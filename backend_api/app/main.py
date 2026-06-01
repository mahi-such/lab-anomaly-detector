from fastapi import FastAPI, HTTPException
from pydantic import BaseModel,Field
from typing import Optional
from app.services.ml_inference import predict_anomaly, is_model_ready, population_baselines
from fastapi.middleware.cors import CORSMiddleware
class LabRequest(BaseModel):
    biomarker_code: str
    result_value_num: float
    test_panel: str
    ref_min_parsed: Optional[float] = Field(default=None)
    ref_max_parsed: Optional[float] = Field(default=None)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Your React dev server URL
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
        result = predict_anomaly(request.model_dump())

        return {"data": result}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Inference error: {str(e)}"
        )
@app.get("/baselines")
def get_baselines():
    return population_baselines