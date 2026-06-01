from fastapi import FastAPI, HTTPException
from pydantic import BaseModel,Field
from typing import Optional
# Ensure this import matches the function name in ml_inference.py
from app.services.ml_inference import predict_anomaly, is_model_ready

# 1. Frontend Data Contract: Matches your React Dashboard structure
class LabRequest(BaseModel):
    biomarker_code: str
    result_value_num: float
    test_panel: str
    ref_min_parsed: Optional[float] = Field(default=None)
    ref_max_parsed: Optional[float] = Field(default=None)

app = FastAPI()

# 2. Health Check: Used by the browser to ensure the backend is alive
@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "model_ready": is_model_ready()
    }

# 3. Main Analysis Endpoint: Processes clinical data through your pipeline
@app.post("/analyze")
async def analyze(request: LabRequest):
    # Verify model is loaded before accepting requests
    if not is_model_ready():
        raise HTTPException(
            status_code=503,
            detail="ML model artifacts not loaded. Check /artifacts folder."
        )

    try:
        # Run the full pipeline (Stat + ML + Hybrid)
        # Using model_dump() for Pydantic v2 compatibility
        result = predict_anomaly(request.model_dump())

        return {"data": result}

    except Exception as e:
        # Catch unexpected inference errors and report back to frontend
        raise HTTPException(
            status_code=500,
            detail=f"Inference error: {str(e)}"
        )