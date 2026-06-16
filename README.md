# 전력 사용량 예측 데이터셋 준비

ENTSO-E Transparency Platform의 전력 수요 데이터를 수집하고, 전력 사용량 예측을 위한 머신러닝 데이터셋(CSV)으로 변환하는 파이프라인입니다.

기본 권역은 `DE_LU`이며, 다른 유럽 국가/권역은 `--country-code` 옵션으로 변경할 수 있습니다.

---

## 준비

### 1. API 토큰 설정

`.env.example` 파일을 복사하여 `.env` 파일을 생성한 뒤, 보유한 ENTSO-E API 토큰을 입력합니다.

```env
ENTSOE_API_KEY=your_api_token_here
```

### 2. 패키지 설치

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## 데이터셋 생성

```powershell
python scripts/build_dataset.py --start 2023-01-01 --end 2025-12-31
```

### 생성 결과

```text
data/raw/entsoe_load.csv
data/raw/open_meteo_weather.csv
data/processed/power_load_dataset.csv
```

---

## 최종 데이터셋 컬럼

| 컬럼명                   | 설명                      |
| --------------------- | ----------------------- |
| load_mw               | 실제 전력 수요 (예측 타깃)        |
| load_forecast_mw      | ENTSO-E Day-Ahead 수요 예측 |
| temperature_2m        | 기온                      |
| relative_humidity_2m  | 상대 습도                   |
| wind_speed_10m        | 풍속                      |
| hour                  | 시간                      |
| dayofweek             | 요일                      |
| month                 | 월                       |
| is_weekend            | 주말 여부                   |
| is_holiday            | 공휴일 여부                  |
| load_lag_24h          | 24시간 전 전력 수요            |
| load_lag_168h         | 168시간(1주일) 전 전력 수요      |
| load_rolling_24h_mean | 최근 24시간 평균 전력 수요        |

---

## 베이스라인 모델 실행

CSV 파일을 프로젝트 폴더에 넣은 뒤 실행합니다.

```powershell
python scripts/train_baselines.py
```

CSV 파일이 여러 개 존재할 경우 가장 큰 파일을 자동으로 선택합니다.

특정 파일을 직접 지정하려면:

```powershell
python scripts/train_baselines.py --csv data/processed/power_load_dataset.csv --target load_mw --time-col timestamp
```

---

## 생성 리포트

### 데이터 품질 리포트

```text
reports/dataset_profile.json
```

* 컬럼 정보
* 결측치 점검
* 시간 간격 검증

### 모델 성능 리포트

```text
reports/baseline_metrics.json
```

* Train / Validation / Test 분리
* 베이스라인 모델 성능 평가

### 예측 결과 시각화

```text
reports/plots/baseline_predictions.png
```

* 실제값과 예측값 비교 그래프
