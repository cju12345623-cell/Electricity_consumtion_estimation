from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, mean_squared_error, r2_score
from sklearn.pipeline import make_pipeline


PROJECT_ROOT = Path(__file__).resolve().parent
REPORT_DIR = PROJECT_ROOT / "reports"
PLOT_DIR = REPORT_DIR / "plots"

TARGET_CANDIDATES = [
    "load_mw",
    "load",
    "total_load",
    "actual_load",
    "demand",
    "power",
    "consumption",
    "electricity_consumption",
]
TIME_CANDIDATES = ["timestamp", "time", "datetime", "date", "dt"]


def find_csv() -> Path:
    candidates = sorted(
        path
        for path in PROJECT_ROOT.rglob("*.csv")
        if ".venv" not in path.parts and "reports" not in path.parts
    )
    if not candidates:
        raise FileNotFoundError("No CSV file found under the project folder.")
    if len(candidates) > 1:
        print("Multiple CSV files found. Using the largest one:")
        for path in candidates:
            print(f"- {path.relative_to(PROJECT_ROOT)} ({path.stat().st_size:,} bytes)")
    return max(candidates, key=lambda path: path.stat().st_size)


def infer_column(columns: list[str], candidates: list[str]) -> str | None:
    lowered = {column.lower(): column for column in columns}
    for candidate in candidates:
        if candidate in lowered:
            return lowered[candidate]
    for column in columns:
        normalized = column.lower().replace(" ", "_").replace("-", "_")
        if any(candidate in normalized for candidate in candidates):
            return column
    return None


def load_dataset(csv_path: Path, target: str | None, time_col: str | None) -> tuple[pd.DataFrame, str, str | None]:
    frame = pd.read_csv(csv_path)
    if frame.empty:
        raise ValueError(f"{csv_path} is empty.")

    time_col = time_col or infer_column(list(frame.columns), TIME_CANDIDATES)
    if time_col is None:
        for column in frame.columns:
            parsed = pd.to_datetime(frame[column], errors="coerce")
            if parsed.notna().mean() > 0.9:
                time_col = column
                break

    if time_col:
        frame[time_col] = pd.to_datetime(frame[time_col], errors="coerce")
        frame = frame.dropna(subset=[time_col]).sort_values(time_col).reset_index(drop=True)

    target = target or infer_column(list(frame.columns), TARGET_CANDIDATES)
    if target is None:
        numeric_columns = frame.select_dtypes(include=[np.number]).columns.tolist()
        if not numeric_columns:
            raise ValueError("No numeric target column found. Pass --target.")
        target = numeric_columns[0]
        print(f"Target column inferred as: {target}")

    if target not in frame.columns:
        raise ValueError(f"Target column not found: {target}")

    frame[target] = pd.to_numeric(frame[target], errors="coerce")
    frame = frame.dropna(subset=[target]).reset_index(drop=True)
    return frame, target, time_col


def add_time_features(frame: pd.DataFrame, time_col: str | None, target: str) -> pd.DataFrame:
    dataset = frame.copy()
    if time_col:
        dataset["hour"] = dataset[time_col].dt.hour
        dataset["dayofweek"] = dataset[time_col].dt.dayofweek
        dataset["month"] = dataset[time_col].dt.month
        dataset["is_weekend"] = dataset["dayofweek"].isin([5, 6]).astype(int)

    dataset["target_lag_24"] = dataset[target].shift(24)
    dataset["target_lag_168"] = dataset[target].shift(168)
    dataset["target_roll_24_mean"] = dataset[target].shift(1).rolling(24).mean()
    return dataset


def split_chronologically(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train_end = int(len(frame) * 0.7)
    valid_end = int(len(frame) * 0.85)
    return frame.iloc[:train_end], frame.iloc[train_end:valid_end], frame.iloc[valid_end:]


def make_xy(frame: pd.DataFrame, target: str, time_col: str | None) -> tuple[pd.DataFrame, pd.Series]:
    ignore = {target}
    if time_col:
        ignore.add(time_col)
    features = frame.drop(columns=[column for column in ignore if column in frame.columns])
    features = pd.get_dummies(features, drop_first=False)
    return features, frame[target]


def align_features(*frames: pd.DataFrame) -> list[pd.DataFrame]:
    columns = sorted(set().union(*(set(frame.columns) for frame in frames)))
    return [frame.reindex(columns=columns, fill_value=0) for frame in frames]


def metrics(y_true: pd.Series, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(mean_squared_error(y_true, y_pred) ** 0.5),
        "mape": float(mean_absolute_percentage_error(y_true, y_pred)),
        "r2": float(r2_score(y_true, y_pred)),
    }


def optional_models() -> dict[str, object]:
    models: dict[str, object] = {}
    try:
        from lightgbm import LGBMRegressor

        models["LightGBM"] = LGBMRegressor(
            n_estimators=500,
            learning_rate=0.04,
            num_leaves=31,
            random_state=42,
            verbose=-1,
        )
    except ImportError:
        pass

    try:
        from xgboost import XGBRegressor

        models["XGBoost"] = XGBRegressor(
            n_estimators=500,
            learning_rate=0.04,
            max_depth=6,
            objective="reg:squarederror",
            random_state=42,
        )
    except ImportError:
        pass

    return models


def plot_predictions(y_true: pd.Series, predictions: dict[str, np.ndarray], output_path: Path) -> None:
    tail_size = min(300, len(y_true))
    x = np.arange(tail_size)
    plt.figure(figsize=(14, 6))
    plt.plot(x, y_true.iloc[-tail_size:].to_numpy(), label="actual", linewidth=2)
    for name, pred in predictions.items():
        plt.plot(x, pred[-tail_size:], label=name, alpha=0.8)
    plt.title("Power Load Forecast Baseline")
    plt.xlabel("Test sample")
    plt.ylabel("Target")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def write_profile(frame: pd.DataFrame, target: str, time_col: str | None, output_path: Path) -> None:
    profile = {
        "rows": int(len(frame)),
        "columns": list(frame.columns),
        "target": target,
        "time_column": time_col,
        "missing_values": frame.isna().sum().astype(int).to_dict(),
    }
    if time_col:
        deltas = frame[time_col].sort_values().diff().dropna()
        profile["time_start"] = str(frame[time_col].min())
        profile["time_end"] = str(frame[time_col].max())
        profile["most_common_time_interval"] = str(deltas.mode().iloc[0]) if not deltas.empty else None
        profile["irregular_time_steps"] = int((deltas != deltas.mode().iloc[0]).sum()) if not deltas.empty else 0
    output_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")


def train(args: argparse.Namespace) -> None:
    REPORT_DIR.mkdir(exist_ok=True)
    PLOT_DIR.mkdir(parents=True, exist_ok=True)

    csv_path = Path(args.csv) if args.csv else find_csv()
    if not csv_path.is_absolute():
        csv_path = PROJECT_ROOT / csv_path

    frame, target, time_col = load_dataset(csv_path, args.target, args.time_col)
    frame = add_time_features(frame, time_col, target).dropna(subset=[target]).reset_index(drop=True)
    write_profile(frame, target, time_col, REPORT_DIR / "dataset_profile.json")

    train_frame, valid_frame, test_frame = split_chronologically(frame)
    if min(len(train_frame), len(valid_frame), len(test_frame)) == 0:
        raise ValueError("Not enough data for train/validation/test split.")

    x_train, y_train = make_xy(train_frame, target, time_col)
    x_valid, y_valid = make_xy(valid_frame, target, time_col)
    x_test, y_test = make_xy(test_frame, target, time_col)
    x_train, x_valid, x_test = align_features(x_train, x_valid, x_test)

    models = {
        "RandomForest": RandomForestRegressor(n_estimators=300, min_samples_leaf=2, n_jobs=-1, random_state=42),
        "HistGradientBoosting": HistGradientBoostingRegressor(max_iter=500, learning_rate=0.04, random_state=42),
        **optional_models(),
    }

    results: dict[str, dict[str, dict[str, float]]] = {}
    test_predictions: dict[str, np.ndarray] = {}

    for name, model in models.items():
        pipeline = make_pipeline(SimpleImputer(strategy="median"), model)
        pipeline.fit(x_train, y_train)
        valid_pred = pipeline.predict(x_valid)
        test_pred = pipeline.predict(x_test)
        results[name] = {
            "valid": metrics(y_valid, valid_pred),
            "test": metrics(y_test, test_pred),
        }
        test_predictions[name] = test_pred

    (REPORT_DIR / "baseline_metrics.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    plot_predictions(y_test, test_predictions, PLOT_DIR / "baseline_predictions.png")

    print(f"CSV: {csv_path}")
    print(f"Target: {target}")
    print(f"Time column: {time_col}")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"Saved: {REPORT_DIR / 'dataset_profile.json'}")
    print(f"Saved: {REPORT_DIR / 'baseline_metrics.json'}")
    print(f"Saved: {PLOT_DIR / 'baseline_predictions.png'}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect a power-load CSV and train baseline forecasting models.")
    parser.add_argument("--csv", default=None, help="CSV path. If omitted, the largest CSV under the project is used.")
    parser.add_argument("--target", default=None, help="Target column. If omitted, the script tries to infer it.")
    parser.add_argument("--time-col", default=None, help="Timestamp column. If omitted, the script tries to infer it.")
    return parser.parse_args()


if __name__ == "__main__":
    train(parse_args())
