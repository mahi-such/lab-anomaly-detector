from app.db.db_service import find_registry_by_alias

def resolve_incoming_result(payload: dict) -> dict:
    raw_name = payload.get("raw_name", "")
    incoming_unit = payload.get("unit", "").strip()
    
    req_min = payload.get("ref_min")
    req_max = payload.get("ref_max")
    
    resolution_report = {
        "canonical_code": None,
        "resolution_status": "unresolved",
        "registry_config": None,
        "effective_ref_min": None,  
        "effective_ref_max": None,  
        "reason": "Unknown biomarker variation with no provided reference boundaries."
    }
    
    registry_entry = find_registry_by_alias(raw_name)
    
    if registry_entry:
        standard_unit = registry_entry.get("standard_unit", "")
        
        if incoming_unit.lower() == standard_unit.lower():
            # Scenario A: Known & Unit Matches
            resolution_report["canonical_code"] = registry_entry["canonical_code"]
            resolution_report["resolution_status"] = "fully_resolved"
            resolution_report["registry_config"] = registry_entry
            resolution_report["effective_ref_min"] = registry_entry.get("ref_min")
            resolution_report["effective_ref_max"] = registry_entry.get("ref_max")
            resolution_report["reason"] = "Biomarker identity verified and unit scale matched."
        else:
            # Scenario B: Known but Unit Mismatches 
            resolution_report["canonical_code"] = registry_entry["canonical_code"]
            resolution_report["resolution_status"] = "provisional"
            resolution_report["registry_config"] = registry_entry
            resolution_report["effective_ref_min"] = req_min
            resolution_report["effective_ref_max"] = req_max
            resolution_report["reason"] = (
                f"Unit mismatch guardrail triggered. Expected: {standard_unit}, Got: {incoming_unit}. "
                "Scored using request-provided range, not registry range. Baseline tracks frozen."
            )
            
    else:
        # Scenario C: Unknown Biomarker
        if req_min is not None and req_max is not None:
            resolution_report["resolution_status"] = "provisional"
            resolution_report["effective_ref_min"] = req_min
            resolution_report["effective_ref_max"] = req_max
            resolution_report["reason"] = "New dynamic test registered. Scored provisionally on LIS provided limits."
        else:
            # Scenario D: Garbage Input
            resolution_report["resolution_status"] = "unresolved"
            resolution_report["reason"] = "Unknown test anomaly. Missing critical baseline reference parameters."
            
    return resolution_report