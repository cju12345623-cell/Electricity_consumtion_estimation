# Electricity Consumption Estimation

Electricity load forecasting project using ENTSO-E electricity load data, Open-Meteo weather data, baseline machine learning models, and a FastAPI + JavaScript dashboard.

The project has two main parts:

- Data and model workflow in Jupyter notebooks
- Web dashboard for uploading raw CSV data, selecting a time period, and comparing actual load with model predictions

The forecasting target is:

```text
load_mw
```

Default ENTSO-E bidding zone:

```text
DE_LU
```

---

## 1. Main Features

- Build an hourly electricity load dataset from ENTSO-E and Open-Meteo data
- Train baseline forecasting models
- Save trained models into a reusable `joblib` bundle
- Run a Python FastAPI backend
- Upload raw CSV data from the web dashboard
- Select a start and end datetime
- Display actual load and model predictions on a chart
- Compare model performance with MAE, RMSE, and MAPE
- Compare ENTSO-E forecast against the trained ML models

---

## 2. Project Structure

```text
Electricity_consumtion_estimation/
|-- app.py
|-- run_backend.ps1
|-- test_backend.py
|-- requirements.txt
|-- README.md
|-- .env.example
|-- .gitignore
|
|-- frontend/
|   |-- index.html
|   |-- styles.css
|   |-- app.js
|
|-- data/
|   |-- raw/
|   |   |-- entsoe_load.csv
|   |   |-- open_meteo_weather.csv
|   |
|   |-- processed/
|       |-- power_load_dataset.csv
|
|-- reports/
|   |-- dataset_profile.json
|   |-- baseline_metrics.json
|   |-- web_model_bundle.joblib
|   |
|   |-- plots/
|       |-- baseline_predictions.png
|
|-- build_dataset.py
|-- train_baselines.py
|-- build_dataset_notebook.ipynb
|-- train_baselines_notebook.ipynb
```

---

## 3. File Descriptions

### Backend And Dashboard Files

| File | Description |
| --- | --- |
| `app.py` | Main FastAPI backend. Serves the dashboard, receives CSV uploads, filters by selected period, loads trained models, runs predictions, and returns JSON results. |
| `run_backend.ps1` | PowerShell helper script for starting the FastAPI server on `http://127.0.0.1:8000/`. |
| `test_backend.py` | Local test script that checks whether the backend prediction logic works without opening the browser. |
| `frontend/index.html` | Dashboard page structure. Contains the upload form, date inputs, metric cards, chart area, summary section, and result table. |
| `frontend/styles.css` | Dashboard styling and responsive layout. Controls cards, chart section, table, colors, spacing, and mobile behavior. |
| `frontend/app.js` | Frontend JavaScript. Sends CSV and date range to `/predict`, receives model predictions, draws the chart, renders the table, and calculates summary metrics. |

### Data And Model Workflow Files

| File | Description |
| --- | --- |
| `build_dataset_notebook.ipynb` | Notebook version of the dataset creation workflow. Downloads ENTSO-E and Open-Meteo data, merges them, and creates the processed dataset. |
| `train_baselines_notebook.ipynb` | Notebook version of the model training workflow. Trains baseline models, evaluates them, and saves `reports/web_model_bundle.joblib` for the backend. |
| `build_dataset.py` | Python script version of the dataset builder. Useful for command-line dataset generation. |
| `train_baselines.py` | Python script version of the baseline model training process. |
| `requirements.txt` | Python dependencies required for dataset building, model training, backend API, and dashboard execution. |
| `.env.example` | Template for environment variables. The real `.env` file should contain the ENTSO-E API key and must not be committed. |
| `.gitignore` | Defines files and folders that should not be committed to GitHub. |

### Generated Files

| File or Folder | Description |
| --- | --- |
| `data/raw/` | Raw downloaded data from ENTSO-E and Open-Meteo. Usually excluded from Git. |
| `data/processed/power_load_dataset.csv` | Final processed dataset used for model training and dashboard testing. |
| `reports/dataset_profile.json` | Dataset summary generated during training. |
| `reports/baseline_metrics.json` | Model evaluation metrics generated during training. |
| `reports/plots/baseline_predictions.png` | Plot comparing actual load and model predictions. |
| `reports/web_model_bundle.joblib` | Saved trained model bundle used by the FastAPI backend. Usually excluded from Git because it is generated and large. |

---

## 4. Dashboard Architecture

The dashboard uses a simple frontend-backend structure.

```text
Browser Dashboard
    |
    | upload CSV + start/end datetime
    v
FastAPI Backend /predict
    |
    | load web_model_bundle.joblib
    | run RandomForest, HistGradientBoosting, XGBoost predictions
    v
JSON response
    |
    v
Dashboard chart + summary + table
```

Frontend:

```text
HTML + CSS + JavaScript
```

Backend:

```text
Python + FastAPI + scikit-learn/XGBoost/LightGBM
```

---

## 5. How To Run The Dashboard

### 1. Move To The Project Folder

```powershell
cd C:\Users\jaeug.choi\Downloads\Personal\vibecoding\estimate_Electricity
```

### 2. Install Dependencies

If the virtual environment already exists:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If starting from a fresh clone:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 3. Make Sure The Model Bundle Exists

The dashboard backend needs this file:

```text
reports/web_model_bundle.joblib
```

If it does not exist, run `train_baselines_notebook.ipynb` from top to bottom.

### 4. Start The Backend Server

Recommended direct command:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Or use the helper script if PowerShell script execution is enabled:

```powershell
.\run_backend.ps1
```

### 5. Open The Dashboard

```text
http://127.0.0.1:8000/
```

Health check endpoint:

```text
http://127.0.0.1:8000/health
```

Prediction endpoint used by the frontend:

```text
http://127.0.0.1:8000/predict
```

---

## 6. Dashboard Usage

1. Open `http://127.0.0.1:8000/`
2. Upload the raw/processed CSV file
3. Select a start datetime
4. Select an end datetime
5. Click the prediction button
6. Review:
   - actual load
   - ENTSO-E forecast, if available
   - RandomForest prediction
   - HistGradientBoosting prediction
   - XGBoost prediction
   - model summary metrics
   - prediction result table

The dashboard calculates summary metrics for the selected period:

| Metric | Meaning |
| --- | --- |
| Average Prediction | Average predicted load for the selected period |
| MAE | Mean absolute error against actual load |
| RMSE | Root mean squared error against actual load |
| MAPE | Mean absolute percentage error against actual load |

The dashboard also highlights the model with the best MAE and compares it with the ENTSO-E forecast when `load_forecast_mw` exists in the uploaded CSV.

---

## 7. Data Used

### ENTSO-E Load Data

Generated file:

```text
data/raw/entsoe_load.csv
```

Main columns:

| Column | Description |
| --- | --- |
| `timestamp` | Timestamp of the load observation |
| `load_mw` | Actual electricity load in MW |
| `load_forecast_mw` | ENTSO-E day-ahead load forecast |

### Open-Meteo Weather Data

Generated file:

```text
data/raw/open_meteo_weather.csv
```

Main columns:

| Column | Description |
| --- | --- |
| `timestamp` | Timestamp of the weather observation |
| `temperature_2m` | Temperature at 2 meters |
| `relative_humidity_2m` | Relative humidity at 2 meters |
| `wind_speed_10m` | Wind speed at 10 meters |

### Final Processed Dataset

```text
data/processed/power_load_dataset.csv
```

This dataset combines:

- hourly electricity load
- day-ahead load forecast
- weather features
- calendar features
- holiday feature
- lag features
- rolling mean features

---

## 8. Models Used

| Model | Library | Description |
| --- | --- | --- |
| RandomForestRegressor | scikit-learn | Tree ensemble baseline model |
| HistGradientBoostingRegressor | scikit-learn | Gradient boosting model from scikit-learn |
| LightGBM | lightgbm | Optional fast gradient boosting model for tabular data |
| XGBoost | xgboost | Gradient boosting model commonly used for structured data |

The saved dashboard model bundle currently exposes the models that were successfully trained and saved in the notebook.

---

## 9. GitHub Upload Notes

Do not commit private or generated files such as:

```text
.env
.venv/
.cache/
__pycache__/
data/raw/
reports/
*.joblib
```

The `.env` file may contain the ENTSO-E API key and must stay private.

The model bundle `reports/web_model_bundle.joblib` is generated by the notebook and can be recreated, so it is usually better to exclude it from GitHub.

---

## 10. Security Notes

The ENTSO-E API key should be stored only in `.env`.

Example:

```env
ENTSOE_API_KEY=your_entsoe_api_key_here
```

Only `.env.example` should be committed.

Do not write the real API key directly inside:

- README files
- notebooks
- Python scripts
- Git commit messages

If the API key is accidentally committed, revoke it from the ENTSO-E Transparency Platform and create a new token.
