# Electricity Consumption Forecasting Dataset Preparation

This project builds a machine learning-ready electricity consumption forecasting dataset using electricity load data from the ENTSO-E Transparency Platform and weather data from Open-Meteo.

The default bidding zone is `DE_LU`, but other European countries and regions can be specified using the `--country-code` parameter.

---

## Setup

### 1. Configure API Access

Copy `.env.example` to `.env` and insert your ENTSO-E API token.

```env
ENTSOE_API_KEY=your_api_token_here
```

### 2. Install Dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## Build the Dataset

Run the dataset generation script:

```powershell
python scripts/build_dataset.py --start 2023-01-01 --end 2025-12-31
```

### Generated Files

```text
data/raw/entsoe_load.csv
data/raw/open_meteo_weather.csv
data/processed/power_load_dataset.csv
```

---

## Dataset Features

| Column                | Description                                 |
| --------------------- | ------------------------------------------- |
| load_mw               | Actual electricity load (prediction target) |
| load_forecast_mw      | ENTSO-E day-ahead load forecast             |
| temperature_2m        | Temperature                                 |
| relative_humidity_2m  | Relative humidity                           |
| wind_speed_10m        | Wind speed                                  |
| hour                  | Hour of day                                 |
| dayofweek             | Day of week                                 |
| month                 | Month                                       |
| is_weekend            | Weekend indicator                           |
| is_holiday            | Public holiday indicator                    |
| load_lag_24h          | Load value 24 hours earlier                 |
| load_lag_168h         | Load value 168 hours (1 week) earlier       |
| load_rolling_24h_mean | Rolling 24-hour average load                |

---

## Train Baseline Models

Place the CSV file in the project directory and run:

```powershell
python scripts/train_baselines.py
```

If multiple CSV files are available, the script automatically selects the largest one.

To specify a dataset manually:

```powershell
python scripts/train_baselines.py --csv data/processed/power_load_dataset.csv --target load_mw --time-col timestamp
```

---

## Generated Reports

### Dataset Profile

```text
reports/dataset_profile.json
```

Contains:

* Column overview
* Missing value analysis
* Time interval validation

### Model Performance Metrics

```text
reports/baseline_metrics.json
```

Contains:

* Train / Validation / Test evaluation results
* Baseline model performance metrics

### Prediction Visualization

```text
reports/plots/baseline_predictions.png
```

Contains:

* Comparison of actual versus predicted electricity load values

---

## Notes

* The `.env` file is excluded from version control through `.gitignore`.
* Only `.env.example` should be committed to the repository.
* Generated datasets and cached files should not be uploaded to GitHub unless explicitly required.
