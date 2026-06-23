from __future__ import annotations

from io import StringIO
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

PROJECT_ROOT = Path(__file__).resolve().parent
MODEL_PATH = PROJECT_ROOT / "reports" / "web_model_bundle.joblib"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

app = FastAPI(title="Electricity Forecast Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


def load_bundle() -> dict[str, Any]:
    if not MODEL_PATH.exists():
        raise RuntimeError(
            f"Model bundle not found: {MODEL_PATH}. "
            "Run train_baselines_notebook.ipynb first to create reports/web_model_bundle.joblib."
        )
    return joblib.load(MODEL_PATH)


bundle = load_bundle()
models = bundle["models"]
feature_columns = bundle["feature_columns"]
target_col = bundle.get("target", "load_mw")
time_col = bundle.get("time_col", "timestamp")


def parse_local_timestamps(values: pd.Series) -> pd.Series:
    cleaned = (
        values.astype(str)
        .str.strip()
        .str.replace(r"Z$", "", regex=True)
        .str.replace(r"[+-]\d{2}:?\d{2}$", "", regex=True)
    )
    return pd.to_datetime(cleaned, errors="coerce")


def read_csv_upload(file_text: str) -> pd.DataFrame:
    frame = pd.read_csv(StringIO(file_text))
    if frame.empty:
        raise HTTPException(status_code=400, detail="CSV file is empty.")
    if time_col not in frame.columns:
        raise HTTPException(status_code=400, detail=f"Missing time column: {time_col}")
    if target_col not in frame.columns:
        raise HTTPException(status_code=400, detail=f"Missing target column: {target_col}")

    frame[time_col] = parse_local_timestamps(frame[time_col])
    frame[target_col] = pd.to_numeric(frame[target_col], errors="coerce")
    frame = frame.dropna(subset=[time_col, target_col]).sort_values(time_col).reset_index(drop=True)

    if frame.empty:
        raise HTTPException(status_code=400, detail="No valid rows after parsing timestamp and target columns.")
    return frame


def parse_user_datetime(value: str, name: str) -> pd.Timestamp:
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        raise HTTPException(status_code=400, detail=f"Invalid {name} datetime: {value}")
    if parsed.tzinfo is not None:
        parsed = parsed.tz_localize(None)
    return parsed


def filter_period(frame: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    start_dt = parse_user_datetime(start, "start")
    end_dt = parse_user_datetime(end, "end")
    if start_dt > end_dt:
        raise HTTPException(status_code=400, detail="Start datetime must be before end datetime.")

    filtered = frame[(frame[time_col] >= start_dt) & (frame[time_col] <= end_dt)].copy()
    if filtered.empty:
        raise HTTPException(status_code=404, detail="No data found for the selected period.")
    return filtered


def make_features(frame: pd.DataFrame) -> pd.DataFrame:
    features = frame.drop(columns=[column for column in [target_col, time_col] if column in frame.columns])
    features = pd.get_dummies(features, drop_first=False)
    return features.reindex(columns=feature_columns, fill_value=0)


@app.get("/")
def dashboard() -> FileResponse:
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Dashboard frontend is missing.")
    return FileResponse(index_path)


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "model_path": str(MODEL_PATH),
        "models": list(models.keys()),
        "target": target_col,
        "time_col": time_col,
        "feature_count": len(feature_columns),
    }


@app.post("/predict")
async def predict(
    file: UploadFile = File(...),
    start: str = Form(...),
    end: str = Form(...),
) -> dict[str, Any]:
    raw_bytes = await file.read()
    try:
        file_text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        file_text = raw_bytes.decode("cp949")

    frame = read_csv_upload(file_text)
    filtered = filter_period(frame, start, end)
    features = make_features(filtered)

    result = pd.DataFrame(
        {
            "timestamp": filtered[time_col].dt.strftime("%Y-%m-%d %H:%M:%S"),
            "actual": filtered[target_col].astype(float),
        }
    )

    if "load_forecast_mw" in filtered.columns:
        result["entsoe_forecast"] = pd.to_numeric(filtered["load_forecast_mw"], errors="coerce")

    for name, model in models.items():
        result[name] = model.predict(features).astype(float)

    return {
        "rows": result.where(pd.notna(result), None).to_dict(orient="records"),
        "models": list(models.keys()),
        "row_count": int(len(result)),
        "start": str(filtered[time_col].iloc[0]),
        "end": str(filtered[time_col].iloc[-1]),
    }
