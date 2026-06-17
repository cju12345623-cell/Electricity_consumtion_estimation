# Electricity Consumption Estimation

## 1. Project Overview

This project builds an electricity load forecasting workflow using ENTSO-E electricity load data and Open-Meteo weather data.

The main workflow is written for Jupyter Notebook:

- `build_dataset_notebook.ipynb`: collects and prepares the dataset
- `train_baselines_notebook.ipynb`: trains baseline forecasting models and evaluates performance

The forecasting target is:

```text
load_mw
```

This represents actual electricity load in MW.

The default ENTSO-E bidding zone is:

```text
DE_LU
```

This corresponds to Germany/Luxembourg.

---

## 2. Data Used

This project uses three main datasets.

### ENTSO-E Load Data

Generated file:

```text
data/raw/entsoe_load.csv
```

Main columns:

| Column | Description |
| --- | --- |
| timestamp | Timestamp of the load observation |
| load_mw | Actual electricity load in MW |
| load_forecast_mw | ENTSO-E day-ahead load forecast |

The raw ENTSO-E load data is collected at 15-minute intervals.

### Open-Meteo Weather Data

Generated file:

```text
data/raw/open_meteo_weather.csv
```

Main columns:

| Column | Description |
| --- | --- |
| timestamp | Timestamp of the weather observation |
| temperature_2m | Temperature at 2 meters |
| relative_humidity_2m | Relative humidity at 2 meters |
| wind_speed_10m | Wind speed at 10 meters |

### Final Processed Dataset

Tracked dataset:

```text
data/processed/power_load_dataset.csv
```

This is the final machine learning dataset. It combines:

- hourly electricity load
- day-ahead load forecast
- weather features
- calendar features
- lag and rolling load features

The raw 15-minute ENTSO-E values are resampled into hourly averages.

Example:

```text
hourly load = mean of four 15-minute load values
```

---

## 3. How To Run, Jupyter Notebook Workflow

### 1. Clone The Repository

```bash
git clone https://github.com/cju12345623-cell/Electricity_consumtion_estimation.git
cd Electricity_consumtion_estimation
```

### 2. Create Environment

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### 3. Add ENTSO-E API Key

Create a `.env` file in the project root.

```env
ENTSOE_API_KEY=your_entsoe_api_key_here
```

Do not commit `.env` to GitHub.

### 4. Open Jupyter Notebook

```bash
jupyter notebook
```

Run the notebooks in this order:

```text
1. build_dataset_notebook.ipynb
2. train_baselines_notebook.ipynb
```

---

## 4. Dataset Builder Notebook

Notebook:

```text
build_dataset_notebook.ipynb
```

This notebook performs the dataset preparation process.

Main steps:

1. Load Python libraries
2. Read `ENTSOE_API_KEY` from `.env`
3. Set country code, date range, timezone, and weather location
4. Download actual load data from ENTSO-E
5. Download day-ahead load forecast data from ENTSO-E
6. Download weather data from Open-Meteo
7. Save raw datasets under `data/raw/`
8. Resample 15-minute load data into hourly averages
9. Merge electricity load data with weather data
10. Add calendar, holiday, lag, and rolling features
11. Save the final dataset to `data/processed/power_load_dataset.csv`

Important settings inside the notebook:

```python
COUNTRY_CODE = "DE_LU"
START_DATE = "2023-01-01"
END_DATE = "2023-10-31"
TIMEZONE = "Europe/Berlin"
LATITUDE = 52.52
LONGITUDE = 13.41
```

Key output:

```text
data/processed/power_load_dataset.csv
```

---

## 5. Model Training Notebook

Notebook:

```text
train_baselines_notebook.ipynb
```

This notebook trains and evaluates baseline forecasting models.

Main steps:

1. Load `data/processed/power_load_dataset.csv`
2. Parse `timestamp`
3. Set `load_mw` as the prediction target
4. Check missing values
5. Check time interval consistency
6. Add extra time and lag features
7. Split data chronologically into train, validation, and test sets
8. Train baseline models
9. Calculate metrics
10. Save metrics and prediction plot

Main settings inside the notebook:

```python
CSV_PATH = PROJECT_ROOT / "data" / "processed" / "power_load_dataset.csv"
TARGET = "load_mw"
TIME_COL = "timestamp"
```

The dataset is split by time order:

| Split | Ratio |
| --- | --- |
| Train | 70% |
| Validation | 15% |
| Test | 15% |

The data is not randomly shuffled because this is a time-series forecasting problem.

---

## 6. Models Used

The notebook trains four baseline models.

| Model | Library | Description |
| --- | --- | --- |
| RandomForestRegressor | scikit-learn | Tree ensemble baseline model |
| HistGradientBoostingRegressor | scikit-learn | Gradient boosting model from scikit-learn |
| LightGBM | lightgbm | Fast gradient boosting model for tabular data |
| XGBoost | xgboost | Gradient boosting model commonly used for structured data |

The models are trained with median imputation for missing feature values.

Main evaluation metrics:

| Metric | Meaning |
| --- | --- |
| MAE | Average absolute prediction error |
| RMSE | Error metric that penalizes large mistakes more strongly |
| MAPE | Average percentage error |
| R2 | Explained variance score |

---

## 7. Result Summary

The best baseline model on the test set was:

```text
HistGradientBoostingRegressor
```

Test performance:

| Model | MAE | RMSE | MAPE | R2 |
| --- | ---: | ---: | ---: | ---: |
| HistGradientBoosting | 1374.72 | 1809.61 | 2.46% | 0.956 |
| LightGBM | 1399.93 | 1827.64 | 2.50% | 0.955 |
| XGBoost | 1608.03 | 2059.83 | 2.86% | 0.943 |
| RandomForest | 1613.54 | 2000.59 | 2.86% | 0.946 |

Generated report files:

```text
reports/dataset_profile.json
reports/baseline_metrics.json
reports/plots/baseline_predictions.png
```

Note:

```text
reports/
```

is excluded from Git because it is generated output.

---

## 8. Folder Structure

```text
Electricity_consumtion_estimation/
├── build_dataset_notebook.ipynb
├── train_baselines_notebook.ipynb
├── build_dataset.py
├── train_baselines.py
├── requirements.txt
├── README.md
├── .env.example
├── .gitignore
├── data/
│   ├── processed/
│   │   └── power_load_dataset.csv
│   └── raw/
│       ├── entsoe_load.csv
│       └── open_meteo_weather.csv
└── reports/
    ├── dataset_profile.json
    ├── baseline_metrics.json
    └── plots/
        └── baseline_predictions.png
```

Tracked in Git:

```text
build_dataset_notebook.ipynb
train_baselines_notebook.ipynb
build_dataset.py
train_baselines.py
requirements.txt
README.md
.env.example
.gitignore
data/processed/power_load_dataset.csv
```

Excluded from Git:

```text
.env
.venv/
.cache/
data/raw/
reports/
```

---

## 9. Security Notes, `.env` And API Key

The ENTSO-E API key should be stored only in `.env`.

Example:

```env
ENTSOE_API_KEY=your_entsoe_api_key_here
```

The `.env` file is excluded by `.gitignore`.

Only this template file should be committed:

```text
.env.example
```

Do not write the real API key directly inside:

- README files
- notebooks
- Python scripts
- Git commit messages

If the API key is accidentally committed, revoke it from the ENTSO-E Transparency Platform and create a new token.
