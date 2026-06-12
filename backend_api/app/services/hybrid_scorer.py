from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class HybridResult:
    final_label     : str            
    confidence      : float         
    anomaly_score   : float          

    decision_reason : str            

    ml_prediction   : str
    ml_probabilities: dict          

    stat_severity   : str           
    z_score         : Optional[float]
    delta           : float
    is_panic        : bool

    alert_message   : str

    def to_dict(self) -> dict:
        return asdict(self)

REASON_PANIC          = "panic_threshold_exceeded"
REASON_SOFT_DOWNGRADE = "low_confidence_stat_soft_downgrade"
REASON_HIGH_ML_CONF   = "high_ml_confidence"
REASON_DOWNGRADE      = "downgrade_borderline_critical"
REASON_STAT_ESCALATE  = "stat_escalation"
REASON_DEFAULT        = "ml_prediction"


class HybridScorer:
    SOFT_DOWNGRADE_CONF           : float = 0.50
    SOFT_DOWNGRADE_RELATIVE_DELTA : float = 0.10

    HIGH_CONF_THRESHOLD           : float = 0.85

    DOWNGRADE_RELATIVE_DELTA      : float = 0.30
    DOWNGRADE_Z                   : float = 1.5

    ESCALATE_Z                    : float = 2.5
    ESCALATE_RELATIVE_DELTA       : float = 0.75

    def decide(self, ml_output: dict) -> HybridResult:
        ml_pred    = ml_output["ml_prediction"]
        ml_probs   = ml_output["ml_probabilities"]
        stat_sev   = ml_output["stat_severity"]
        z_score    = ml_output["z_score"]
        delta      = ml_output["delta"]
        is_panic   = ml_output["is_panic"]
        ml_conf    = ml_output["confidence"]
        ml_crit_p  = ml_probs.get("CRITICAL", 0.0)
        ref_min = ml_output.get("ref_min")
        ref_max = ml_output.get("ref_max")

        relative_delta = None
        if ref_min is not None and ref_max is not None and ref_max > ref_min:
            relative_delta = abs(delta) / (ref_max - ref_min)

        #  Rule 1: Panic override 
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
        if ml_pred in ("ALERT", "CRITICAL"):
            d_small = relative_delta is not None and relative_delta < self.SOFT_DOWNGRADE_RELATIVE_DELTA
            if ml_conf < self.SOFT_DOWNGRADE_CONF and stat_sev == "NORMAL" and d_small:
                return self._build(
                    label   = "WATCH",
                    conf    = ml_conf, 
                    reason  = REASON_SOFT_DOWNGRADE,
                    ml_pred = ml_pred,
                    ml_probs= ml_probs,
                    stat_sev= stat_sev,
                    z_score = z_score,
                    delta   = delta,
                    is_panic= False,
                )

        #  Rule 3: High ML confidence 
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
        if ml_pred == "CRITICAL":
            z_small = z_score is None or abs(z_score) < self.DOWNGRADE_Z
            d_small = relative_delta is not None and relative_delta < self.DOWNGRADE_RELATIVE_DELTA
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
        if ml_pred in ("NORMAL", "WATCH"):
            z_large = z_score is not None and abs(z_score) >= self.ESCALATE_Z
            d_large = relative_delta is not None and relative_delta >= self.ESCALATE_RELATIVE_DELTA
            if z_large and d_large:
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

        #  Rule 6: Default- ML prediction
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