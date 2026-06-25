from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from contextlib import asynccontextmanager

from app.services.resolution_engine import resolve_incoming_result
from app.services.stat_engine import calculate_biological_severity, evaluate_sms_trigger
from app.db.db_service import insert_audit_log, build_alias_cache, update_baseline, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup sequence:
    1. init_db() ensures tables exist before anything else runs.
    2. build_alias_cache() loads the O(1) lookup dict into memory.
    """
    init_db()
    build_alias_cache()
    yield


app = FastAPI(title="Rely Clinical Engine", lifespan=lifespan)


class LabResult(BaseModel):
    request_id: str
    lab_ref: str
    raw_name: str
    value: float
    unit: str
    ref_min: Optional[float] = None
    ref_max: Optional[float] = None


@app.post("/analyze")
def analyze_result(payload: LabResult):
    # Pydantic v1/v2 compatibility
    data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()

    # Stage 1: Resolve biomarker identity and unit validity
    res_report = resolve_incoming_result(data)

    # Stage 2: Calculate severity using panic boundaries and Z-scores
    stat_report = calculate_biological_severity(data["value"], res_report)

    # Stage 3: Evaluate SMS trigger against resolution and severity
    sms_decision = evaluate_sms_trigger(res_report, stat_report)

    # Stage 4: Build audit record and persist — every request logged regardless of outcome
    audit_data = {
        "request_id": data["request_id"],
        "lab_ref": data["lab_ref"],
        "raw_name": data["raw_name"],
        "canonical_code": res_report["canonical_code"],
        "value_num": data["value"],
        "unit": data["unit"],
        "ref_min": res_report["effective_ref_min"],
        "ref_max": res_report["effective_ref_max"],
        "z_score": stat_report.get("z_score"),
        "baseline_confidence": (res_report.get("registry_config") or {}).get("baseline_confidence", "none"),
        "severity": stat_report["final_severity"],
        "is_panic": stat_report["is_panic"],
        "should_send_sms": sms_decision["should_send_sms"],
        "resolution_status": res_report["resolution_status"],
        "reason": f"{stat_report['reason']} | {sms_decision['sms_reason']}"
    }

    insert_audit_log(audit_data)

    # Stage 5: Update Welford baseline safely.
    # - If established (confidence != none): Only NORMAL or MILD values are added to prevent corruption.
    # - If cold-start (confidence == none): We allow updates for UNKNOWN values ONLY if the raw reading 
    #   falls inside the standard reference range. This resolves the cold-start deadlock.
    if res_report["resolution_status"] == "fully_resolved":
        canonical_code = res_report["canonical_code"]
        val = data["value"]
        
        reg_config = res_report.get("registry_config") or {}
        confidence = reg_config.get("baseline_confidence", "none")
        
        is_normal_or_mild = stat_report["final_severity"] in ("NORMAL", "MILD")
        
        is_cold_start = (confidence == "none")
        ref_min = res_report.get("effective_ref_min")
        ref_max = res_report.get("effective_ref_max")
        
        is_safe_cold_start_value = (
            is_cold_start 
            and ref_min is not None 
            and ref_max is not None 
            and (ref_min <= val <= ref_max)
        )
        
        if is_normal_or_mild or is_safe_cold_start_value:
            update_baseline(canonical_code, val)

    return {
        "raw_name": data["raw_name"],
        "canonical_code": res_report["canonical_code"],
        "resolution_status": res_report["resolution_status"],
        "severity": stat_report["final_severity"],
        "should_send_sms": sms_decision["should_send_sms"],
        "reason": audit_data["reason"]
    }