import os
import json
import logging
from pathlib import Path
import joblib
from app.services.hybrid_scorer import hybrid_scorer
from app.services.stat_engine import StatisticalScorer, LabResultPayload

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LOCAL_FALLBACK_DIR = Path(__file__).resolve().parent.parent.parent / "artifacts"
ARTIFACT_DIR = Path(os.getenv("RELY_ARTIFACT_DIR", LOCAL_FALLBACK_DIR))

try:
    model          = joblib.load(ARTIFACT_DIR / "xgboost_model.joblib")
    bio_encoder    = joblib.load(ARTIFACT_DIR / "bio_encoder.joblib")
    panel_encoder  = joblib.load(ARTIFACT_DIR / "panel_encoder.joblib")
    target_encoder = joblib.load(ARTIFACT_DIR / "target_encoder.joblib")

    with open(ARTIFACT_DIR / "population_baselines.json") as f:
        population_baselines = json.load(f)

    scorer = StatisticalScorer(baselines=population_baselines, panics=None)
    logger.info("ML Engine initialized successfully.")
except Exception as e:
    logger.error(f"Artifact load failure: {e}")
    raise e

def _encode_biomarker(code: str) -> int:
    try:
        cleaned = str(code).strip().upper()
        if cleaned in bio_encoder.classes_:
            return int(bio_encoder.transform([cleaned])[0])
        raise ValueError
    except (ValueError, KeyError):
        logger.warning(f"Unseen biomarker '{code}'; using UNKNOWN fallback.")
        return int(bio_encoder.transform(["UNKNOWN"])[0]) if "UNKNOWN" in bio_encoder.classes_ else 0

def _encode_panel(panel: str) -> int:
    try:
        cleaned = str(panel).strip().upper()
        if cleaned in panel_encoder.classes_:
            return int(panel_encoder.transform([cleaned])[0])
        raise ValueError
    except (ValueError, KeyError):
        logger.warning(f"Unseen panel '{panel}'; using UNKNOWN fallback.")
        return int(panel_encoder.transform(["UNKNOWN"])[0]) if "UNKNOWN" in panel_encoder.classes_ else 0

def predict_anomaly(data: dict) -> dict:
    val = float(data.get("result_value_num", 0.0))
    ref_min = data.get("ref_min_parsed")
    ref_max = data.get("ref_max_parsed")

    if ref_min is None or ref_max is None:
        baseline = population_baselines.get(data["biomarker_code"].upper(), {})
        
        ref_min = baseline.get("ref_min_typical", 0.0)
        ref_max = baseline.get("ref_max_typical", 100.0)

        logger.info(
            f"Using clinical baselines for {data['biomarker_code']}: "
            f"{ref_min}-{ref_max}"
        )

    ref_min = float(ref_min)
    ref_max = float(ref_max)

    # Statistical scoring
    stat_result = scorer.score(
        LabResultPayload(
            biomarker_code=data["biomarker_code"],
            result_value_num=val,
            ref_min=ref_min,
            ref_max=ref_max,
        )
    )

    # XGBoost inference
    feature_matrix = [[
        val,
        ref_min,
        ref_max,
        _encode_biomarker(data["biomarker_code"]),
        _encode_panel(data.get("test_panel", "UNKNOWN")),
        int(data.get("result_month", 1)),
    ]]

    pred_idx = int(model.predict(feature_matrix)[0])
    probabilities = model.predict_proba(feature_matrix)[0]

    ml_prediction = str(target_encoder.inverse_transform([pred_idx])[0])

    prob_dict = {
        str(cls): round(float(prob), 4)
        for cls, prob in zip(target_encoder.classes_, probabilities)
    }

    confidence = round(float(prob_dict[ml_prediction]), 4)

    # Hybrid decision
    ml_output = {
        "ml_prediction": ml_prediction,
        "ml_probabilities": prob_dict,
        "stat_severity": stat_result.severity_from_stats,
        "z_score": stat_result.z_score,
        "delta": stat_result.delta,
        "is_panic": stat_result.is_panic,
        "confidence": confidence,
        "ref_min": ref_min,
        "ref_max": ref_max
    }

    return hybrid_scorer.decide(ml_output).to_dict()

def is_model_ready() -> bool:
    return all([model, bio_encoder, panel_encoder, target_encoder, scorer])