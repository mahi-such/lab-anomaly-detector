from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from contextlib import asynccontextmanager

from app.services.resolution_engine import resolve_incoming_result
from app.services.stat_engine import calculate_biological_severity, evaluate_sms_trigger
from app.db.db_service import insert_audit_log, build_alias_cache, update_baseline, init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
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
    data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
    res_report = resolve_incoming_result(data)

    stat_report = calculate_biological_severity(data["value"], res_report)

    sms_decision = evaluate_sms_trigger(res_report, stat_report)

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

    if (
        res_report["resolution_status"] == "fully_resolved"
        and stat_report["final_severity"] in ("NORMAL", "MILD")
    ):
        update_baseline(res_report["canonical_code"], data["value"])

    return {
        "raw_name": data["raw_name"],
        "canonical_code": res_report["canonical_code"],
        "resolution_status": res_report["resolution_status"],
        "severity": stat_report["final_severity"],
        "should_send_sms": sms_decision["should_send_sms"],
        "reason": audit_data["reason"]
    }