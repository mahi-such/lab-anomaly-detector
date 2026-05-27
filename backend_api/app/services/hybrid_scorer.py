"""
hybrid_scorer.py
backend_api/app/services/hybrid_scorer.py

Combines StatisticalScorer + XGBoost outputs into a final
clinical decision. Called by the FastAPI /analyze endpoint
after ml_inference.predict_anomaly() returns.

Architecture:
    Raw Lab Input
          │
          ├── StatisticalScorer  → stat_severity, z_score, delta, is_panic
          └── XGBoost            → ml_prediction, ml_probabilities, confidence
                    │
              HybridScorer  ← you are here
                    │
              Final response to API

Decision priority (top wins, others skipped):
    1. Panic override          → always CRITICAL, no rules checked
    2. Soft downgrade to WATCH → AI uncertain, stats normal, borderline delta
    3. High ML confidence      → ml_proba[CRITICAL] >= 0.85 → trust model
    4. Downgrade borderline    → ML=CRITICAL but delta+z say barely abnormal
    5. Stat escalation         → ML=NORMAL/WATCH but stat signals large deviation
    6. Default                 → use ML prediction as-is

Thresholds are class constants — tune them here without touching
any other file.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class HybridResult:
    """
    Final unified output returned by the /analyze endpoint.
    Every field the React AlertPanel needs is here.
    """
    # ── Core decision ──────────────────────────────────────────
    final_label     : str            # NORMAL / WATCH / ALERT / CRITICAL
    confidence      : float          # 0.0 – 1.0  (ML probability of final_label)
    anomaly_score   : float          # 0.0 – 1.0  display-only severity bar

    # ── Rule that fired ───────────────────────────────────────
    decision_reason : str            # see REASON_* constants below

    # ── ML layer ──────────────────────────────────────────────
    ml_prediction   : str
    ml_probabilities: dict           # {'ALERT':0.04, 'CRITICAL':0.83, ...}

    # ── Statistical layer ─────────────────────────────────────
    stat_severity   : str            # PANIC/SEVERE/MODERATE/MILD/NORMAL/UNKNOWN
    z_score         : Optional[float]
    delta           : float
    is_panic        : bool

    # ── Alert text for React panel ────────────────────────────
    alert_message   : str

    def to_dict(self) -> dict:
        return asdict(self)


# ── Decision reason constants ─────────────────────────────────
# Used in logs and API response so frontend can explain the decision
REASON_PANIC          = "panic_threshold_exceeded"
REASON_SOFT_DOWNGRADE = "low_confidence_stat_soft_downgrade"
REASON_HIGH_ML_CONF   = "high_ml_confidence"
REASON_DOWNGRADE      = "downgrade_borderline_critical"
REASON_STAT_ESCALATE  = "stat_escalation"
REASON_DEFAULT        = "ml_prediction"


class HybridScorer:
    """
    Combines StatisticalScorer and XGBoost outputs into one
    final clinical label. Stateless — safe to call concurrently.

    Usage:
        hybrid = HybridScorer()
        result = hybrid.decide(ml_inference_output)
    """

    # ── Tunable thresholds ────────────────────────────────────

    # Rule 2: Soft downgrade to WATCH when ALL conditions are true
    #   ml_conf < SOFT_DOWNGRADE_CONF
    #   stat_sev == "NORMAL"
    #   |delta| < SOFT_DOWNGRADE_DELTA
    SOFT_DOWNGRADE_CONF  : float = 0.50
    SOFT_DOWNGRADE_DELTA : float = 1.0

    # Rule 3: trust model when CRITICAL probability is this high
    HIGH_CONF_THRESHOLD : float = 0.85

    # Rule 4: downgrade CRITICAL when BOTH conditions are true
    #   delta < DOWNGRADE_DELTA  (barely outside ref range)
    #   |z| < DOWNGRADE_Z        (statistically near-normal)
    DOWNGRADE_DELTA     : float = 2.0
    DOWNGRADE_Z         : float = 1.5

    # Rule 5: escalate NORMAL/WATCH when EITHER condition is true
    #   |z| >= ESCALATE_Z        (statistically very unusual)
    #   |delta| >= ESCALATE_DELTA (far outside ref range)
    ESCALATE_Z          : float = 2.5
    ESCALATE_DELTA      : float = 3.0

    def decide(self, ml_output: dict) -> HybridResult:
        """
        Takes the dict returned by predict_anomaly() and
        applies the rule chain to produce a final HybridResult.
        """
        ml_pred    = ml_output["ml_prediction"]
        ml_probs   = ml_output["ml_probabilities"]
        stat_sev   = ml_output["stat_severity"]
        z_score    = ml_output["z_score"]
        delta      = ml_output["delta"]
        is_panic   = ml_output["is_panic"]
        ml_conf    = ml_output["confidence"]
        ml_crit_p  = ml_probs.get("CRITICAL", 0.0)

        #  Rule 1: Panic override 
        # ml_inference already returned early for panic, but
        # guard here too so HybridScorer is safe to call standalone
        if is_panic or stat_sev == "PANIC":
            return self._build(
                label   = "CRITICAL",
                conf    = 1.0,
                reason  = REASON_PANIC,
                ml_pred = ml_pred,
                ml_probs= ml_probs,
                stat_sev= stat_sev,
                z_score = z_score,
                delta   = delta,
                is_panic= True,
            )

        #  Rule 2: Soft downgrade to WATCH 
        # AI is uncertain, stats are normal, and value is barely 
        # outside the reference range. Downgrade to preserve visibility
        # without triggering a false alarm.
        if ml_pred in ("ALERT", "CRITICAL"):
            if (ml_conf < self.SOFT_DOWNGRADE_CONF and 
                stat_sev == "NORMAL" and 
                abs(delta) < self.SOFT_DOWNGRADE_DELTA):
                return self._build(
                    label   = "WATCH",
                    conf    = ml_conf, # Preserve original ML confidence
                    reason  = REASON_SOFT_DOWNGRADE,
                    ml_pred = ml_pred,
                    ml_probs= ml_probs,
                    stat_sev= stat_sev,
                    z_score = z_score,
                    delta   = delta,
                    is_panic= False,
                )

        #  Rule 3: High ML confidence 
        # Model is very sure — trust it regardless of stat engine
        # Threshold: CRITICAL probability >= 0.85
        if ml_crit_p >= self.HIGH_CONF_THRESHOLD:
            return self._build(
                label   = "CRITICAL",
                conf    = ml_crit_p,
                reason  = REASON_HIGH_ML_CONF,
                ml_pred = ml_pred,
                ml_probs= ml_probs,
                stat_sev= stat_sev,
                z_score = z_score,
                delta   = delta,
                is_panic= False,
            )

        #  Rule 4: Downgrade borderline CRITICAL 
        # ML says CRITICAL but both signals say barely abnormal.
        # Both conditions must be true to downgrade.
        if ml_pred == "CRITICAL":
            z_small = z_score is None or abs(z_score) < self.DOWNGRADE_Z
            d_small = abs(delta) < self.DOWNGRADE_DELTA
            if z_small and d_small:
                return self._build(
                    label   = "ALERT",
                    conf    = ml_probs.get("ALERT", 0.0),
                    reason  = REASON_DOWNGRADE,
                    ml_pred = ml_pred,
                    ml_probs= ml_probs,
                    stat_sev= stat_sev,
                    z_score = z_score,
                    delta   = delta,
                    is_panic= False,
                )
            return self._build(
                label   = "CRITICAL",
                conf    = ml_crit_p,
                reason  = REASON_DEFAULT,
                ml_pred = ml_pred,
                ml_probs= ml_probs,
                stat_sev= stat_sev,
                z_score = z_score,
                delta   = delta,
                is_panic= False,
            )

        #  Rule 5: Stat escalation 
        # ML says NORMAL or WATCH but stat engine sees a large
        # deviation. Either signal alone is enough to escalate.
        if ml_pred in ("NORMAL", "WATCH"):
            z_large = z_score is not None and abs(z_score) >= self.ESCALATE_Z
            d_large = abs(delta) >= self.ESCALATE_DELTA
            if z_large or d_large:
                return self._build(
                    label   = "ALERT",
                    conf    = ml_probs.get("ALERT", 0.0),
                    reason  = REASON_STAT_ESCALATE,
                    ml_pred = ml_pred,
                    ml_probs= ml_probs,
                    stat_sev= stat_sev,
                    z_score = z_score,
                    delta   = delta,
                    is_panic= False,
                )

        #  Rule 6: Default 
        # No rule fired — use ML prediction as-is
        return self._build(
            label   = ml_pred,
            conf    = ml_conf,
            reason  = REASON_DEFAULT,
            ml_pred = ml_pred,
            ml_probs= ml_probs,
            stat_sev= stat_sev,
            z_score = z_score,
            delta   = delta,
            is_panic= False,
        )


    def _build(
        self,
        label   : str,
        conf    : float,
        reason  : str,
        ml_pred : str,
        ml_probs: dict,
        stat_sev: str,
        z_score : Optional[float],
        delta   : float,
        is_panic: bool,
    ) -> HybridResult:
        """Build the final HybridResult and generate alert message."""
        anomaly_score = self._anomaly_score(ml_probs)
        alert_message = self._alert_message(
            label, stat_sev, z_score, delta, is_panic, reason
        )
        logger.info(
            f"HybridScorer → {label} "
            f"(reason={reason}, ml={ml_pred}, stat={stat_sev}, "
            f"score={anomaly_score:.3f})"
        )
        return HybridResult(
            final_label     = label,
            confidence      = round(float(conf), 4),
            anomaly_score   = anomaly_score,
            decision_reason = reason,
            ml_prediction   = ml_pred,
            ml_probabilities= ml_probs,
            stat_severity   = stat_sev,
            z_score         = z_score,
            delta           = round(float(delta), 4),
            is_panic        = is_panic,
            alert_message   = alert_message,
        )

    @staticmethod
    def _anomaly_score(ml_probs: dict) -> float:
        """
        Continuous 0–1 severity score for the React panel display bar.
        Not used for the label decision — display only.
        CRITICAL contributes fully, ALERT contributes half.
        """
        crit  = ml_probs.get("CRITICAL", 0.0)
        alert = ml_probs.get("ALERT",    0.0)
        return round(min(crit + alert * 0.5, 1.0), 4)

    @staticmethod
    def _alert_message(
        label   : str,
        stat_sev: str,
        z_score : Optional[float],
        delta   : float,
        is_panic: bool,
        reason  : str,
    ) -> str:
        """
        Human-readable alert message for the React AlertPanel.
        Shown to pathologists alongside the severity badge.
        """
        if is_panic or reason == REASON_PANIC:
            return (
                "PANIC VALUE — result crosses clinical emergency threshold. "
                "Immediate review required."
            )

        z_str = f"{z_score:+.2f} SD from population mean" if z_score is not None \
                else "population baseline unavailable"

        delta_str = (
            f"{abs(delta):.1f} units above reference maximum"
            if delta > 0
            else f"{abs(delta):.1f} units below reference minimum"
            if delta < 0
            else "within reference range"
        )

        severity_phrases = {
            "SEVERE":   "severely abnormal",
            "MODERATE": "moderately abnormal",
            "MILD":     "mildly abnormal",
            "NORMAL":   "within population norms",
            "UNKNOWN":  "no population baseline available",
        }
        stat_phrase = severity_phrases.get(stat_sev, stat_sev.lower())

        if label == "CRITICAL":
            return (
                f"Result is {delta_str} ({z_str}). "
                f"Statistically {stat_phrase}. "
                f"ML model predicts CRITICAL with high confidence. "
                f"Urgent clinical review recommended."
            )
        elif label == "ALERT":
            if reason == REASON_DOWNGRADE:
                return (
                    f"Result is {delta_str} ({z_str}). "
                    f"ML model initially predicted CRITICAL but deviation is borderline. "
                    f"Downgraded to ALERT — clinical review recommended."
                )
            elif reason == REASON_STAT_ESCALATE:
                return (
                    f"Result is {delta_str} ({z_str}). "
                    f"Statistical engine flagged significant deviation. "
                    f"Escalated to ALERT — clinical review recommended."
                )
            return (
                f"Result is {delta_str} ({z_str}). "
                f"Statistically {stat_phrase}. Clinical review recommended."
            )
        elif label == "WATCH":
            if reason == REASON_SOFT_DOWNGRADE:
                return (
                    f"Result is {delta_str} ({z_str}). "
                    f"ML model predicted anomaly with low confidence. "
                    f"Downgraded to WATCH due to near-normal statistics."
                )
            return (
                f"Result is {delta_str} ({z_str}). "
                f"Statistically {stat_phrase}. Monitor on next visit."
            )
        else:  
            return (
                f"Result is {delta_str} ({z_str}). "
                f"No clinical action required."
            )

hybrid_scorer = HybridScorer()