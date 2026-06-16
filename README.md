전력 사용량 예측 데이터셋 준비
ENTSO-E Transparency Platform의 전력 수요 데이터를 내려받아 예측용 CSV로 정리하는 파이프라인입니다.
기본 권역은 DE_LU이고, 다른 유럽 국가/권역은 --country-code로 바꿀 수 있습니다.
준비
.env.example을 복사해 .env를 만들고 보유한 ENTSO-E API 토큰을 넣습니다.
패키지를 설치합니다.
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
데이터셋 생성
python scripts/build_dataset.py --start 2023-01-01 --end 2025-12-31
결과:
data/raw/entsoe_load.csv
data/raw/open_meteo_weather.csv
data/processed/power_load_dataset.csv
최종 컬럼
load_mw: 실제 전력 수요, 예측 타깃
load_forecast_mw: ENTSO-E day-ahead 수요 예측
temperature_2m, relative_humidity_2m, wind_speed_10m: 날씨 피처
hour, dayofweek, month, is_weekend, is_holiday: 시간/캘린더 피처
load_lag_24h, load_lag_168h, load_rolling_24h_mean: 과거 수요 기반 피처
베이스라인 모델 실행
CSV 파일을 프로젝트 폴더 안에 넣은 뒤 실행합니다.
python scripts/train_baselines.py
CSV가 여러 개 있으면 가장 큰 파일을 자동으로 사용합니다. 직접 지정하려면:
python scripts/train_baselines.py --csv data/processed/power_load_dataset.csv --target load_mw --time-col timestamp
생성 결과:
reports/dataset_profile.json: 컬럼, 결측치, 시간 간격 점검
reports/baseline_metrics.json: train/validation/test 분리 후 모델 성능
reports/plots/baseline_predictions.png: 실제값과 예측값 비교 그래프