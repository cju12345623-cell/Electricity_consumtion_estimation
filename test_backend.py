from pathlib import Path

import pandas as pd

import app

csv_path = Path("data/processed/power_load_dataset.csv")
text = csv_path.read_text(encoding="utf-8-sig")
frame = app.read_csv_upload(text)
filtered = app.filter_period(frame, "2023-01-10T00:00", "2023-01-10T12:00")
features = app.make_features(filtered)

result = pd.DataFrame(
    {
        "timestamp": filtered[app.time_col].dt.strftime("%Y-%m-%d %H:%M:%S"),
        "actual": filtered[app.target_col].astype(float),
    }
)

for name, model in app.models.items():
    result[name] = model.predict(features).astype(float)

print("rows:", len(result))
print("columns:", list(result.columns))
print(result.head().to_string(index=False))
