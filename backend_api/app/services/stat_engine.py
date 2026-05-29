from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Optional

PANIC_THRESHOLDS: dict[str, dict] = {
    # Haematology
    "HB":          {"low": 5.0,   "high": 20.0,   "unit": "g/dL",    "note": "Critical anaemia / polycythaemia"},
    "HGB":         {"low": 5.0,   "high": 20.0,   "unit": "g/dL",    "note": "Alt code for haemoglobin"},
    "HAEMOGLOBIN": {"low": 5.0,   "high": 20.0,   "unit": "g/dL",    "note": "Alt code for haemoglobin"},
    "WBC":         {"low": 2.0,   "high": 30.0,   "unit": "10³/µL",  "note": "Severe leukopenia / leukocytosis"},
    "PLT":         {"low": 50.0,  "high": 1000.0, "unit": "10³/µL",  "note": "Bleeding risk / thrombocytosis"},
    "PLATELETS":   {"low": 50.0,  "high": 1000.0, "unit": "10³/µL",  "note": "Alt code"},
    # Electrolytes
    "K":           {"low": 2.5,   "high": 6.5,    "unit": "mmol/L",  "note": "Cardiac arrhythmia risk"},
    "POTASSIUM":   {"low": 2.5,   "high": 6.5,    "unit": "mmol/L",  "note": "Alt code"},
    "NA":          {"low": 120.0, "high": 160.0,  "unit": "mmol/L",  "note": "Hypo/hypernatraemia seizure risk"},
    "SODIUM":      {"low": 120.0, "high": 160.0,  "unit": "mmol/L",  "note": "Alt code"},
    "CA":          {"low": 6.0,   "high": 13.0,   "unit": "mg/dL",   "note": "Hypo/hypercalcaemia"},
    "CALCIUM":     {"low": 6.0,   "high": 13.0,   "unit": "mg/dL",   "note": "Alt code"},
    # Glucose
    "GLUCOSE_RND": {"low": 40.0,  "high": 500.0,  "unit": "mg/dL",   "note": "Hypoglycaemia / hyperglycaemic crisis"},
    "GLUCOSE_FBS": {"low": 40.0,  "high": 500.0,  "unit": "mg/dL",   "note": "Fasting glucose panic"},
    "GLUCOSE":     {"low": 40.0,  "high": 500.0,  "unit": "mg/dL",   "note": "Alt code"},
    # Renal
    "CREATININE":  {"low": None,  "high": 10.0,   "unit": "mg/dL",   "note": "Acute renal failure"},
    "CREAT":       {"low": None,  "high": 10.0,   "unit": "mg/dL",   "note": "Alt code"},
    "BUN":         {"low": None,  "high": 100.0,  "unit": "mg/dL",   "note": "Uraemia"},
    "UREA":        {"low": None,  "high": 100.0,  "unit": "mg/dL",   "note": "Alt code"},
    # Lipids
    "CHOL_TOT":    {"low": None,  "high": 400.0,  "unit": "mg/dL",   "note": "Extreme hypercholesterolaemia"},
    "LDL":         {"low": None,  "high": 300.0,  "unit": "mg/dL",   "note": "Extreme LDL"},
    "TRIG":        {"low": None,  "high": 1000.0, "unit": "mg/dL",   "note": "Pancreatitis risk"},
    # Liver
    "ALT":         {"low": None,  "high": 1000.0, "unit": "U/L",     "note": "Acute hepatitis / liver failure"},
    "AST":         {"low": None,  "high": 1000.0, "unit": "U/L",     "note": "Acute hepatitis / liver failure"},
    "BILIRUBIN":   {"low": None,  "high": 20.0,   "unit": "mg/dL",   "note": "Severe jaundice"},
    "TBIL":        {"low": None,  "high": 20.0,   "unit": "mg/dL",   "note": "Alt code"},
    # Thyroid
    "TSH":         {"low": 0.01,  "high": 100.0,  "unit": "mIU/L",   "note": "Thyroid storm / myxoedema"},
    # Cardiac
    "TROPONIN":    {"low": None,  "high": 2.0,    "unit": "ng/mL",   "note": "Myocardial infarction"},
    "TROP_I":      {"low": None,  "high": 2.0,    "unit": "ng/mL",   "note": "Alt code"},
    # Coagulation
    "INR":         {"low": None,  "high": 5.0,    "unit": "ratio",   "note": "Severe anticoagulation"},
    "PT":          {"low": None,  "high": 60.0,   "unit": "sec",     "note": "Coagulopathy"},
}

@dataclass
class LabResultPayload:
    
    biomarker_code:   str
    result_value_num: float
    ref_min:          float
    ref_max:          float
    dataset_zscore:   Optional[float] = None
    dataset_is_panic: Optional[int]   = None


@dataclass
class StatisticalScore:
    
    biomarker_code:          str
    value:                   float
    z_score:                 Optional[float]
    delta:                   float
    is_panic:                bool
    severity_from_stats:     str
    baseline_available:      bool
    panic_threshold_defined: bool

    def to_dict(self) -> dict:
        return asdict(self)

def compute_zscore(
    biomarker_code: str,
    value: float,
    baselines: dict,
) -> Optional[float]:
    """
    Return the population Z-score for *value* using pre-built *baselines*.

    Returns None if the biomarker is not in baselines or std is 0.

    Parameters
    ----------
    biomarker_code  Code string (will be upper-stripped internally)
    value           Numeric lab result
    baselines       Dict loaded from population_baselines.json
    """
    code = str(biomarker_code).strip().upper()
    bl = baselines.get(code)
    if bl is None:
        return None
    std = bl.get("std")
    if not std:
        return None
    return round((value - bl["mean"]) / std, 4)


def compute_delta(
    value: float,
    ref_min: float,
    ref_max: float,
) -> float:
    
    if value < ref_min:
        return round(value - ref_min, 4)
    if value > ref_max:
        return round(value - ref_max, 4)
    return 0.0


def is_panic_value(
    biomarker_code: str,
    value: float,
    panic_thresholds: dict = None,
) -> bool:
   
    if panic_thresholds is None:
        panic_thresholds = PANIC_THRESHOLDS
    code = str(biomarker_code).strip().upper()
    thresh = panic_thresholds.get(code)
    if thresh is None:
        return False
    low  = thresh.get("low")
    high = thresh.get("high")
    if low  is not None and value < low:
        return True
    if high is not None and value > high:
        return True
    return False

class StatisticalScorer:
 
    _SEVERITY_BANDS = [
        (0.0, 1.0,          "NORMAL"),
        (1.0, 2.0,          "MILD"),
        (2.0, 3.0,          "MODERATE"),
        (3.0, float("inf"), "SEVERE"),
    ]

    def __init__(
        self,
        baselines: dict,
        panics: dict = None,
    ) -> None:
  
        self.baselines: dict = baselines
        self.panics: dict    = panics if panics is not None else PANIC_THRESHOLDS

    @classmethod
    def from_json(
        cls,
        json_path: str,
        panics: dict = None,
    ) -> "StatisticalScorer":
    
        with open(json_path) as f:
            baselines = json.load(f)
        return cls(baselines=baselines, panics=panics)

    def score(self, payload: LabResultPayload) -> StatisticalScore:
        """
        Score a single lab result.

        Parameters
        ----------
        payload  LabResultPayload with biomarker_code, result_value_num,
                 ref_min, ref_max

        Returns
        -------
        StatisticalScore
        """
        code  = str(payload.biomarker_code).strip().upper()
        value = float(payload.result_value_num)

        z        = compute_zscore(code, value, self.baselines)
        delta    = compute_delta(value, payload.ref_min, payload.ref_max)
        panic    = is_panic_value(code, value, self.panics)
        severity = self._severity(z, panic)

        return StatisticalScore(
            biomarker_code          = code,
            value                   = value,
            z_score                 = z,
            delta                   = delta,
            is_panic                = panic,
            severity_from_stats     = severity,
            baseline_available      = code in self.baselines,
            panic_threshold_defined = code in self.panics,
        )

    def score_batch(self, payloads: list[LabResultPayload]) -> list[StatisticalScore]:
        """
        Score multiple lab results.

        Parameters
        ----------
        payloads  List of LabResultPayload

        Returns
        -------
        List of StatisticalScore in the same order as input
        """
        return [self.score(p) for p in payloads]

    def _severity(self, z_score: Optional[float], panic: bool) -> str:
        if panic:
            return "PANIC"
        if z_score is None:
            return "UNKNOWN"
        abs_z = abs(z_score)
        for lo, hi, label in self._SEVERITY_BANDS:
            if lo <= abs_z < hi:
                return label
        return "SEVERE"