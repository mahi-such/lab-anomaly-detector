import pandas as pd
import numpy as np
import json, os, math, warnings, unittest
from dataclasses import dataclass, asdict
from typing import Optional
warnings.filterwarnings('ignore')

df = pd.read_csv("ml_pipeline/data/rely_lis_model_features_v6.csv")
#  Per biomarker population statistics
def build_population_baselines(df: pd.DataFrame) -> dict:

    clean = df.dropna(subset=['biomarker_code', 'result_value_num']).copy()

    baselines = {}
    for code, grp in clean.groupby('biomarker_code'):
        vals = grp['result_value_num'].dropna()
        if len(vals) < 5:
            continue

        ref_min_typical = grp['ref_min_parsed'].median() if 'ref_min_parsed' in grp else None
        ref_max_typical = grp['ref_max_parsed'].median() if 'ref_max_parsed' in grp else None

        baselines[str(code)] = {
            'mean':             round(float(vals.mean()), 4),
            'std':              round(float(vals.std(ddof=1)), 4),
            'p5':               round(float(vals.quantile(0.05)), 4),
            'p25':              round(float(vals.quantile(0.25)), 4),
            'median':           round(float(vals.quantile(0.50)), 4),
            'p75':              round(float(vals.quantile(0.75)), 4),
            'p95':              round(float(vals.quantile(0.95)), 4),
            'n_samples':        int(len(vals)),
            'ref_min_typical':  round(float(ref_min_typical), 4) if ref_min_typical is not None and not math.isnan(ref_min_typical) else None,
            'ref_max_typical':  round(float(ref_max_typical), 4) if ref_max_typical is not None and not math.isnan(ref_max_typical) else None,
        }

    return baselines

BASELINES = build_population_baselines(df)
BASELINE_JSON_PATH = "backend_api/artifacts/population_baselines.json"

os.makedirs(os.path.dirname(BASELINE_JSON_PATH), exist_ok=True)

with open(BASELINE_JSON_PATH, "w") as f:
    json.dump(BASELINES, f, indent=2)

print(f" Saved → {BASELINE_JSON_PATH}")
# Format: biomarker_code → {'low': float|None, 'high': float|None, 'unit': str, 'note': str}
PANIC_THRESHOLDS = {
    # Haematology
    'HB':           {'low': 5.0,   'high': 20.0,  'unit': 'g/dL',   'note': 'Critical anaemia / polycythaemia'},
    'HGB':          {'low': 5.0,   'high': 20.0,  'unit': 'g/dL',   'note': 'Alt code for haemoglobin'},
    'HAEMOGLOBIN':  {'low': 5.0,   'high': 20.0,  'unit': 'g/dL',   'note': 'Alt code for haemoglobin'},
    'WBC':          {'low': 2.0,   'high': 30.0,  'unit': '10³/µL', 'note': 'Severe leukopenia / leukocytosis'},
    'PLT':          {'low': 50.0,  'high': 1000.0,'unit': '10³/µL', 'note': 'Bleeding risk / thrombocytosis'},
    'PLATELETS':    {'low': 50.0,  'high': 1000.0,'unit': '10³/µL', 'note': 'Alt code'},

    # Electrolytes
    'K':            {'low': 2.5,   'high': 6.5,   'unit': 'mmol/L', 'note': 'Cardiac arrhythmia risk'},
    'POTASSIUM':    {'low': 2.5,   'high': 6.5,   'unit': 'mmol/L', 'note': 'Alt code'},
    'NA':           {'low': 120.0, 'high': 160.0, 'unit': 'mmol/L', 'note': 'Hypo/hypernatraemia seizure risk'},
    'SODIUM':       {'low': 120.0, 'high': 160.0, 'unit': 'mmol/L', 'note': 'Alt code'},
    'CA':           {'low': 6.0,   'high': 13.0,  'unit': 'mg/dL',  'note': 'Hypo/hypercalcaemia'},
    'CALCIUM':      {'low': 6.0,   'high': 13.0,  'unit': 'mg/dL',  'note': 'Alt code'},

    # Glucose
    'GLUCOSE_RND':  {'low': 40.0,  'high': 500.0, 'unit': 'mg/dL',  'note': 'Hypoglycaemia / hyperglycaemic crisis'},
    'GLUCOSE_FBS':  {'low': 40.0,  'high': 500.0, 'unit': 'mg/dL',  'note': 'Fasting glucose panic'},
    'GLUCOSE':      {'low': 40.0,  'high': 500.0, 'unit': 'mg/dL',  'note': 'Alt code'},

    # Renal
    'CREATININE':   {'low': None,  'high': 10.0,  'unit': 'mg/dL',  'note': 'Acute renal failure'},
    'CREAT':        {'low': None,  'high': 10.0,  'unit': 'mg/dL',  'note': 'Alt code'},
    'BUN':          {'low': None,  'high': 100.0, 'unit': 'mg/dL',  'note': 'Uraemia'},
    'UREA':         {'low': None,  'high': 100.0, 'unit': 'mg/dL',  'note': 'Alt code'},

    # Lipids
    'CHOL_TOT':     {'low': None,  'high': 400.0, 'unit': 'mg/dL',  'note': 'Extreme hypercholesterolaemia'},
    'LDL':          {'low': None,  'high': 300.0, 'unit': 'mg/dL',  'note': 'Extreme LDL'},
    'TRIG':         {'low': None,  'high': 1000.0,'unit': 'mg/dL',  'note': 'Pancreatitis risk'},

    # Liver
    'ALT':          {'low': None,  'high': 1000.0,'unit': 'U/L',    'note': 'Acute hepatitis / liver failure'},
    'AST':          {'low': None,  'high': 1000.0,'unit': 'U/L',    'note': 'Acute hepatitis / liver failure'},
    'BILIRUBIN':    {'low': None,  'high': 20.0,  'unit': 'mg/dL',  'note': 'Severe jaundice'},
    'TBIL':         {'low': None,  'high': 20.0,  'unit': 'mg/dL',  'note': 'Alt code'},

    # Thyroid
    'TSH':          {'low': 0.01,  'high': 100.0, 'unit': 'mIU/L',  'note': 'Thyroid storm / myxoedema'},

    # Cardiac
    'TROPONIN':     {'low': None,  'high': 2.0,   'unit': 'ng/mL',  'note': 'Myocardial infarction'},
    'TROP_I':       {'low': None,  'high': 2.0,   'unit': 'ng/mL',  'note': 'Alt code'},

    # Coagulation
    'INR':          {'low': None,  'high': 5.0,   'unit': 'ratio',  'note': 'Severe anticoagulation'},
    'PT':           {'low': None,  'high': 60.0,  'unit': 'sec',    'note': 'Coagulopathy'},
}
# zscore
def compute_zscore(
    biomarker_code: str,
    value: float,
    baselines: dict = None,
) -> Optional[float]:
    
    if baselines is None:
        baselines = BASELINES

    code = str(biomarker_code).strip().upper()
    bl = baselines.get(code)

    if bl is None:
        return None

    std = bl.get('std')
    if std is None or std == 0:
        return None

    return round((value - bl['mean']) / std, 4)
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
# panic lookup
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

    low  = thresh.get('low')
    high = thresh.get('high')

    if low  is not None and value < low:
        return True
    if high is not None and value > high:
        return True
    return False
#Data classes
@dataclass
class LabResultPayload:
    #Input to StatisticalScorer
    biomarker_code: str
    result_value_num: float
    ref_min: float
    ref_max: float
    # optional — already-computed dataset column (used for cross-checking)
    dataset_zscore: Optional[float] = None
    dataset_is_panic: Optional[int] = None


@dataclass
class StatisticalScore:
    #Output of StatisticalScorer.score()
    biomarker_code:     str
    value:              float
    z_score:            Optional[float]    # None if biomarker unknown
    delta:              float              
    is_panic:           bool
    severity_from_stats: str              
    baseline_available: bool
    panic_threshold_defined: bool

    def to_dict(self):
        return asdict(self)
    
# StatisticalScorer
class StatisticalScorer:
    """
    Standalone statistical scorer
    Loads population baselines + panic thresholds at construction.

    Usage:
        scorer = StatisticalScorer(baselines=BASELINES, panics=PANIC_THRESHOLDS)
        result = scorer.score(LabResultPayload(...))
    """

    # Severity bands by |Z-score|
    # PANIC overrides Z-score severity if is_panic=True
    _SEVERITY_BANDS = [
        (0.0, 1.0,  'NORMAL'),
        (1.0, 2.0,  'MILD'),
        (2.0, 3.0,  'MODERATE'),
        (3.0, float('inf'), 'SEVERE'),
    ]

    def __init__(
        self,
        baselines: dict = None,
        panics: dict = None,
    ):
        self.baselines = baselines if baselines is not None else BASELINES
        self.panics    = panics    if panics    is not None else PANIC_THRESHOLDS

    # public API

    def score(self, payload: LabResultPayload) -> StatisticalScore:
        """
        Main entry point — returns StatisticalScore for one lab result.
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

    def score_batch(self, payloads: list) -> list:
        """Score multiple lab results. Returns list of StatisticalScore."""
        return [self.score(p) for p in payloads]

    @classmethod
    def from_json(cls, json_path: str, panics: dict = None) -> 'StatisticalScorer':
        """Load baselines from a JSON file (what the API does at startup)."""
        with open(json_path) as f:
            baselines = json.load(f)
        return cls(baselines=baselines, panics=panics)

    def _severity(self, z_score: Optional[float], panic: bool) -> str:
        if panic:
            return 'PANIC'
        if z_score is None:
            return 'UNKNOWN'
        abs_z = abs(z_score)
        for lo, hi, label in self._SEVERITY_BANDS:
            if lo <= abs_z < hi:
                return label
        return 'SEVERE'


scorer = StatisticalScorer()
print(' StatisticalScorer ready')
if __name__ == "__main__":

    scorer = StatisticalScorer.from_json(
        "backend_api/artifacts/population_baselines.json"
    )

    sample = LabResultPayload(
        biomarker_code="GLUCOSE_RND",
        result_value_num=350,
        ref_min=70,
        ref_max=110
    )

    result = scorer.score(sample)

    print(result.to_dict())