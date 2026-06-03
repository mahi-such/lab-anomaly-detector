from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware

from app.services.ml_inference import predict_anomaly, is_model_ready, population_baselines
from app.data.biomarker_metadata import BIOMARKER_METADATA

class LabRequest(BaseModel):
    biomarker_code: str
    result_value_num: float
    test_panel: str
    ref_min_parsed: Optional[float] = Field(default=None)
    ref_max_parsed: Optional[float] = Field(default=None)

app = FastAPI(title="RelyTech LIS Backend Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # React dev server URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "model_ready": is_model_ready()
    }

@app.post("/analyze")
async def analyze(request: LabRequest):
    if not is_model_ready():
        raise HTTPException(
            status_code=503,
            detail="ML model artifacts not loaded. Check /artifacts folder."
        )

    try:
        print("\nDEBUG PAYLOAD:")
        print(request.model_dump())

        result = predict_anomaly(request.model_dump())

        return {"data": result}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Inference error: {str(e)}"
        )

@app.get("/baselines")
def get_baselines():
    combined_baselines = {}
    for code, baseline_data in population_baselines.items():
        lookup_code = code.strip().upper()
        ui_metadata = BIOMARKER_METADATA.get(lookup_code, {"unit": "—", "panel": "UNKNOWN"})
        
        combined_baselines[lookup_code] = {
            **baseline_data,
            "unit": ui_metadata.get("unit", "—"),
            # Change "GENERAL" to "UNKNOWN" to match the encoder's explicit token
            "panel": ui_metadata.get("panel") or "UNKNOWN" 
        }
    return combined_baselines