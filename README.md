diff --git a/C:\Users\jaeug.choi\Documents\전력 사용량 예측\README.md b/C:\Users\jaeug.choi\Documents\전력 사용량 예측\README.md
new file mode 100644
--- /dev/null
+++ b/C:\Users\jaeug.choi\Documents\전력 사용량 예측\README.md
@@ -0,0 +1,36 @@
+# 전력 사용량 예측 데이터셋 준비
+
+ENTSO-E Transparency Platform의 전력 수요 데이터를 내려받아 예측용 CSV로 정리하는 파이프라인입니다.
+
+기본 권역은 `DE_LU`이고, 다른 유럽 국가/권역은 `--country-code`로 바꿀 수 있습니다.
+
+## 준비
+
+1. `.env.example`을 복사해 `.env`를 만들고 보유한 ENTSO-E API 토큰을 넣습니다.
+2. 패키지를 설치합니다.
+
+```powershell
+python -m venv .venv
+.\.venv\Scripts\Activate.ps1
+pip install -r requirements.txt
+```
+
+## 데이터셋 생성
+
+```powershell
+python scripts/build_dataset.py --start 2023-01-01 --end 2025-12-31
+```
+
+결과:
+
+- `data/raw/entsoe_load.csv`
+- `data/raw/open_meteo_weather.csv`
+- `data/processed/power_load_dataset.csv`
+
+## 최종 컬럼
+
+- `load_mw`: 실제 전력 수요, 예측 타깃
+- `load_forecast_mw`: ENTSO-E day-ahead 수요 예측
+- `temperature_2m`, `relative_humidity_2m`, `wind_speed_10m`: 날씨 피처
+- `hour`, `dayofweek`, `month`, `is_weekend`, `is_holiday`: 시간/캘린더 피처
+- `load_lag_24h`, `load_lag_168h`, `load_rolling_24h_mean`: 과거 수요 기반 피처
