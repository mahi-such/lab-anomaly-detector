import os
import json
import logging
from pathlib import Path
import joblib

from app.services.stat_engine import StatisticalScorer, LabResultPayload

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LOCAL_FALLBACK_DIR = Path(__file__).resolve().parent.parent.parent / "artifacts"
ARTIFACT_DIR       = Path(os.getenv("RELY_ARTIFACT_DIR", LOCAL_FALLBACK_DIR))
logger.info(f"Artifact directory: {ARTIFACT_DIR.resolve()}")

try:
    model          = joblib.load(ARTIFACT_DIR / "xgboost_model.joblib")
    bio_encoder    = joblib.load(ARTIFACT_DIR / "bio_encoder.joblib")
    panel_encoder  = joblib.load(ARTIFACT_DIR / "panel_encoder.joblib")
    target_encoder = joblib.load(ARTIFACT_DIR / "target_encoder.joblib")

    with open(ARTIFACT_DIR / "population_baselines.json") as f:
        population_baselines = json.load(f)

    scorer = StatisticalScorer(
        baselines        = population_baselines,
        panics = None,
    )

    logger.info(
        f"All artifacts loaded — "
        f"model classes: {list(target_encoder.classes_)}, "
        f"baselines: {len(population_baselines)} biomarkers"
    )

except FileNotFoundError as e:
    logger.error(
        f"Startup failure: artifact not found in {ARTIFACT_DIR}. "
        f"Expected: xgboost_model.joblib, bio_encoder.joblib, "
        f"panel_encoder.joblib, target_encoder.joblib, "
        f"population_baselines.json"
    )
    raise e


def _encode_biomarker(code: str) -> int:
    try:
        cleaned = str(code).strip().upper()
        if cleaned in bio_encoder.classes_:
            return int(bio_encoder.transform([cleaned])[0])
        raise ValueError  # Manually triggers the fallback path if token is unseen
    except (ValueError, KeyError):
        logger.warning(f"Unseen biomarker: '{code}' → mapped to UNKNOWN fallback.")
        if "UNKNOWN" in bio_encoder.classes_:
            return int(bio_encoder.transform(["UNKNOWN"])[0])
        return 0

def _encode_panel(panel: str) -> int:
    try:
        cleaned = str(panel).strip().upper()
        if cleaned in panel_encoder.classes_:
            return int(panel_encoder.transform([cleaned])[0])
        raise ValueError  # Manually triggers the fallback path if token is unseen
    except (ValueError, KeyError):
        logger.warning(f"Unseen panel: '{panel}' → mapped to UNKNOWN fallback.")
        if "UNKNOWN" in panel_encoder.classes_:
            return int(panel_encoder.transform(["UNKNOWN"])[0])
        return 0


# Main inference function 
def predict_anomaly(data: dict) -> dict:
    """
    Takes one lab result payload, runs it through both the
    statistical engine and XGBoost, returns a unified response.
    """

    # statistical engine (parallel to XGBoost) 
    stat_result = scorer.score(LabResultPayload(
        biomarker_code   = data["biomarker_code"],
        result_value_num = float(data["result_value_num"]),
        ref_min          = float(data["ref_min_parsed"]),
        ref_max          = float(data["ref_max_parsed"]),
    ))

    # panic overrides
    if stat_result.is_panic:
        logger.info(f"Panic override: {data['biomarker_code']} = {data['result_value_num']} → CRITICAL")
        return {
            "ml_prediction"   : "CRITICAL",
            "ml_probabilities": {"ALERT": 0.0, "CRITICAL": 1.0, "NORMAL": 0.0, "WATCH": 0.0},
            "stat_severity"   : "PANIC",
            "z_score"         : stat_result.z_score,
            "delta"           : stat_result.delta,
            "is_panic"        : True,
            "final_label"     : "CRITICAL",
            "confidence"      : 1.0,
            "override_reason" : "panic_threshold_exceeded",
        }

    bio_enc   = _encode_biomarker(data["biomarker_code"])
    panel_enc = _encode_panel(data.get("test_panel", "UNKNOWN"))

    feature_matrix = [[
        float(data["result_value_num"]),
        float(data["ref_min_parsed"]),
        float(data["ref_max_parsed"]),
        bio_enc,
        panel_enc,
        int(data.get("result_month", 1)),
    ]]

    #XGBoost inference 
    pred_idx      = int(model.predict(feature_matrix)[0])
    probabilities = model.predict_proba(feature_matrix)[0]
    ml_prediction = str(target_encoder.inverse_transform([pred_idx])[0])

    prob_dict = {
        str(cls): round(float(prob), 4)
        for cls, prob in zip(target_encoder.classes_, probabilities)
    }
    confidence = round(float(prob_dict[ml_prediction]), 4)

    final_label = ml_prediction

    return {
        "ml_prediction"   : ml_prediction,
        "ml_probabilities": prob_dict,
        "stat_severity"   : stat_result.severity_from_stats,
        "z_score"         : stat_result.z_score,
        "delta"           : stat_result.delta,
        "is_panic"        : stat_result.is_panic,
        "final_label"     : final_label,
        "confidence"      : confidence,
        "override_reason" : None,
    }