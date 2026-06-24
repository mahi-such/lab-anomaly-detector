from typing import Dict, Any

SEVERITY_RANK = {"UNKNOWN": 0, "NORMAL": 1, "MILD": 2, "MODERATE": 3, "SEVERE": 4}


def calculate_biological_severity(value: float, report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculates final biological severity using three independent routes:
    1. Panic threshold override (fully_resolved only)
    2. Reference-range delta deviation
    3. Confidence-gated Z-score (fully_resolved only)
    """
    reg = report.get("registry_config") or {}
    res_status = report.get("resolution_status")
    eff_min = report.get("effective_ref_min")
    eff_max = report.get("effective_ref_max")

    if res_status == "fully_resolved" and reg.get("panic_enabled"):
        pl = reg.get("panic_low")
        ph = reg.get("panic_high")
        if (pl is not None and value <= pl) or (ph is not None and value >= ph):
            return {
                "final_severity": "PANIC",
                "is_panic": True,
                "z_score": None,
                "reason": "Value crossed approved panic threshold."
            }

    delta_sev = "UNKNOWN"
    z_sev = "UNKNOWN"
    z_val = None
    reason = "No valid reference range available."

    if eff_min is not None and eff_max is not None:
        span = eff_max - eff_min
        if span > 0:
            if eff_min <= value <= eff_max:
                delta_sev = "NORMAL"
                reason = "Value inside approved reference range."
            else:
                breach = (eff_min - value) if value < eff_min else (value - eff_max)
                pct = breach / span
                if pct <= 0.15:
                    delta_sev = "MILD"
                elif pct <= 0.35:
                    delta_sev = "MODERATE"
                else:
                    delta_sev = "SEVERE"
                reason = f"Delta route: {pct * 100:.1f}% breach outside reference span."

    if res_status == "fully_resolved" and reg.get("baseline_confidence") in ("moderate", "full"):
        mean = reg.get("baseline_mean")
        std = reg.get("baseline_std")
        if mean is not None and std is not None and std > 0:
            z_val = (value - mean) / std
            abs_z = abs(z_val)
            if abs_z < 1.5:
                z_sev = "NORMAL"
            elif abs_z < 2.5:
                z_sev = "MILD"
            elif abs_z < 3.5:
                z_sev = "MODERATE"
            else:
                z_sev = "SEVERE"

    if SEVERITY_RANK.get(z_sev, 0) > SEVERITY_RANK.get(delta_sev, 0):
        return {
            "final_severity": z_sev,
            "is_panic": False,
            "z_score": z_val,
            "reason": f"Z-score route dominant (Z={z_val:.2f}). {reason}"
        }

    return {
        "final_severity": delta_sev,
        "is_panic": False,
        "z_score": z_val,
        "reason": reason
    }


def evaluate_sms_trigger(report: Dict[str, Any], stat: Dict[str, Any]) -> Dict[str, Any]:
    reg = report.get("registry_config") or {}

    if report.get("resolution_status") != "fully_resolved":
        return {"should_send_sms": False, "sms_reason": "Locked: result is not fully resolved."}

    if not reg.get("sms_enabled"):
        return {"should_send_sms": False, "sms_reason": "Locked: master SMS switch disabled for this biomarker."}

    if stat.get("is_panic"):
        return {"should_send_sms": True, "sms_reason": "Panic threshold breached."}

    if stat.get("final_severity") == "SEVERE" and reg.get("stat_severe_sms_enabled"):
        return {"should_send_sms": True, "sms_reason": "SEVERE classification with stat SMS enabled."}

    return {"should_send_sms": False, "sms_reason": "Severity below SMS trigger threshold."}