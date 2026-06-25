from typing import Dict, Any


def calculate_biological_severity(value: float, report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculates final biological severity using two routes:
    1. Panic threshold override (fully_resolved only)
    2. Z-score route (fully_resolved + n >= 30 only)

    Delta route removed. Provisional and cold-start results return UNKNOWN.
    """
    reg = report.get("registry_config") or {}
    res_status = report.get("resolution_status")

    # Route 1: Panic Override
    # Gated on fully_resolved — prevents unit-mismatched provisional values
    # from being compared against registry panic thresholds in the wrong scale.
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

    # Route 2: Z-Score
    # Active only when fully_resolved AND baseline has at least 30 samples.
    # Provisional results and cold-start biomarkers (n < 30) fall through to UNKNOWN.
    if res_status == "fully_resolved" and reg.get("baseline_confidence") != "none":
        mean = reg.get("baseline_mean")
        std = reg.get("baseline_std")
        if mean is not None and std is not None and std > 0:
            z_val = (value - mean) / std
            abs_z = abs(z_val)
            if abs_z < 1.5:
                z_sev = "NORMAL"
            elif abs_z < 2.0:
                z_sev = "MILD"
            
            #elif abs_z < 3.5:
             #   z_sev = "MODERATE"
            else:
                z_sev = "SEVERE"
            return {
                "final_severity": z_sev,
                "is_panic": False,
                "z_score": z_val,
                "reason": f"Z-score route (Z={z_val:.2f})."
            }

    # Fallback: provisional result or cold-start (n < 30)
    return {
        "final_severity": "UNKNOWN",
        "is_panic": False,
        "z_score": None,
        "reason": "Insufficient baseline data or provisional result. Cannot score."
    }


def evaluate_sms_trigger(report: Dict[str, Any], stat: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates whether an SMS alert should fire.
    Provisional and unresolved results are hard-locked to False regardless of severity.
    """
    reg = report.get("registry_config") or {}

    # Hard lock 1: not fully resolved
    if report.get("resolution_status") != "fully_resolved":
        return {
            "should_send_sms": False,
            "sms_reason": "Locked: result is not fully resolved."
        }

    # Hard lock 2: master SMS switch
    if not reg.get("sms_enabled"):
        return {
            "should_send_sms": False,
            "sms_reason": "Locked: master SMS switch disabled for this biomarker."
        }

    # Gold standard: actual panic event
    if stat.get("is_panic"):
        return {
            "should_send_sms": True,
            "sms_reason": "Panic threshold breached."
        }

    # If panic limits exist, suppress stat SEVERE to prevent alert fatigue
    has_panic_limits = (
        reg.get("panic_enabled")
        and (
            reg.get("panic_low") is not None
            or reg.get("panic_high") is not None
        )
    )

    if has_panic_limits:
        return {
            "should_send_sms": False,
            "sms_reason": "Clinical panic limits exist; statistical SEVERE suppressed to prevent alert fatigue."
        }

    # Fallback: stat SEVERE only when no panic limits defined
    if stat.get("final_severity") == "SEVERE" and reg.get("stat_severe_sms_enabled"):
        return {
            "should_send_sms": True,
            "sms_reason": "No panic limits defined; fallback to stat SEVERE trigger."
        }

    return {
        "should_send_sms": False,
        "sms_reason": "Severity below SMS trigger threshold."
    }