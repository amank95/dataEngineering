from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
import os

from data_pipeline import main
from config_loader import get_output_file

app = FastAPI(
    title="Stock Data Pipeline API",
    description="API for ML team to generate and fetch stock market data",
    version="1.0"
)

# ---------------------------
# Health check
# ---------------------------
@app.get("/")
def health_check():
    return {
        "status": "API is running",
        "message": "Use /run-pipeline to generate data"
    }

# ---------------------------
# Run data pipeline
# ---------------------------
@app.post("/run-pipeline")
def run_pipeline_api():
    try:
        main()
        return {
            "status": "success",
            "message": "Data pipeline executed successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------
# Fetch processed data
# ---------------------------
@app.get("/fetch-data")
def fetch_processed_data():
    output_file = get_output_file()

    if not os.path.exists(output_file):
        raise HTTPException(
            status_code=404,
            detail="Processed data not found. Run /run-pipeline first."
        )

    return FileResponse(
        path=output_file,
        filename=os.path.basename(output_file),
        media_type="application/octet-stream"
    )
       # Start API
# python -m uvicorn api:app --reload
         #Go to
#http://127.0.0.1:8000/docs


