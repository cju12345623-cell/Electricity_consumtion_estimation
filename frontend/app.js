const form = document.querySelector("#predictForm");
const csvInput = document.querySelector("#csvInput");
const startInput = document.querySelector("#startInput");
const endInput = document.querySelector("#endInput");
const statusText = document.querySelector("#statusText");
const rowCount = document.querySelector("#rowCount");
const periodText = document.querySelector("#periodText");
const actualAvg = document.querySelector("#actualAvg");
const peakActual = document.querySelector("#peakActual");
const winnerText = document.querySelector("#winnerText");
const modelSummary = document.querySelector("#modelSummary");
const tableHead = document.querySelector("#tableHead");
const tableBody = document.querySelector("#tableBody");
const legend = document.querySelector("#legend");
const canvas = document.querySelector("#forecastChart");
const ctx = canvas.getContext("2d");

const colors = {
  actual: "#17211d",
  entsoe_forecast: "#d89b26",
  RandomForest: "#12633f",
  HistGradientBoosting: "#1d638f",
  LightGBM: "#c85a45",
  XGBoost: "#7657b8",
};

let rows = [];
let seriesKeys = [];

function formatNumber(value) {
  if (!Number.isFinite(Number(value))) return "-";
  return new Intl.NumberFormat("ko-KR", { maximumFractionDigits: 1 }).format(Number(value));
}

function updateStatus(message, isError = false) {
  statusText.textContent = message;
  statusText.style.color = isError ? "#c85a45" : "#63716b";
}

function resizeCanvas() {
  const ratio = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = Math.max(1, Math.floor(rect.width * ratio));
  canvas.height = Math.max(1, Math.floor(rect.height * ratio));
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  return rect;
}

function drawLine(points, color, width = 2.5) {
  ctx.beginPath();
  points.forEach((point, index) => {
    if (index === 0) ctx.moveTo(point.x, point.y);
    else ctx.lineTo(point.x, point.y);
  });
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.lineJoin = "round";
  ctx.lineCap = "round";
  ctx.stroke();
}

function drawChart() {
  const rect = resizeCanvas();
  const width = rect.width;
  const height = rect.height;
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#fff";
  ctx.fillRect(0, 0, width, height);

  if (!rows.length) return;

  const pad = { top: 24, right: 24, bottom: 48, left: 76 };
  const plotWidth = width - pad.left - pad.right;
  const plotHeight = height - pad.top - pad.bottom;
  const values = rows.flatMap((row) => seriesKeys.map((key) => Number(row[key]))).filter(Number.isFinite);
  const min = Math.min(...values) * 0.96;
  const max = Math.max(...values) * 1.04;

  ctx.strokeStyle = "#d8ded6";
  ctx.fillStyle = "#63716b";
  ctx.font = "12px Segoe UI, Arial, sans-serif";
  for (let i = 0; i <= 4; i += 1) {
    const y = pad.top + (plotHeight / 4) * i;
    const value = max - ((max - min) / 4) * i;
    ctx.beginPath();
    ctx.moveTo(pad.left, y);
    ctx.lineTo(width - pad.right, y);
    ctx.stroke();
    ctx.fillText(`${formatNumber(value)} MW`, 10, y + 4);
  }

  const toPoint = (value, index) => ({
    x: pad.left + (plotWidth * index) / Math.max(rows.length - 1, 1),
    y: pad.top + plotHeight - ((Number(value) - min) / (max - min || 1)) * plotHeight,
  });

  seriesKeys.forEach((key) => {
    const points = rows.map((row, index) => toPoint(row[key], index)).filter((point) => Number.isFinite(point.y));
    drawLine(points, colors[key] || "#555");
  });

  const tickCount = Math.min(6, rows.length);
  ctx.fillStyle = "#17211d";
  for (let i = 0; i < tickCount; i += 1) {
    const rowIndex = Math.floor((i * (rows.length - 1)) / Math.max(tickCount - 1, 1));
    const x = pad.left + (plotWidth * rowIndex) / Math.max(rows.length - 1, 1);
    const label = rows[rowIndex].timestamp.slice(5, 16);
    ctx.fillText(label, Math.min(x, width - 96), height - 18);
  }
}

function renderLegend() {
  legend.innerHTML = seriesKeys.map((key) => `
    <span><i style="background:${colors[key] || "#555"}"></i>${key}</span>
  `).join("");
}

function renderMetrics(response) {
  const actualValues = rows.map((row) => Number(row.actual)).filter(Number.isFinite);
  const avg = actualValues.reduce((sum, value) => sum + value, 0) / actualValues.length;
  const peak = Math.max(...actualValues);
  rowCount.textContent = response.row_count ?? rows.length;
  periodText.textContent = `${response.start} ~ ${response.end}`;
  actualAvg.textContent = `${formatNumber(avg)} MW`;
  peakActual.textContent = `${formatNumber(peak)} MW`;
}

function mean(values) {
  const valid = values.filter(Number.isFinite);
  return valid.length ? valid.reduce((sum, value) => sum + value, 0) / valid.length : NaN;
}

function modelMetrics(key) {
  const pairs = rows
    .map((row) => ({ actual: Number(row.actual), pred: Number(row[key]) }))
    .filter((row) => Number.isFinite(row.actual) && Number.isFinite(row.pred));
  const errors = pairs.map((row) => row.pred - row.actual);
  const absErrors = errors.map(Math.abs);
  const squaredErrors = errors.map((value) => value ** 2);
  const ape = pairs
    .filter((row) => row.actual !== 0)
    .map((row) => Math.abs((row.pred - row.actual) / row.actual) * 100);
  return {
    key,
    count: pairs.length,
    averagePrediction: mean(pairs.map((row) => row.pred)),
    mae: mean(absErrors),
    rmse: Math.sqrt(mean(squaredErrors)),
    mape: mean(ape),
  };
}

function renderSummary() {
  if (!rows.length) {
    modelSummary.innerHTML = "";
    winnerText.textContent = "예측 실행 후 모델별 평가가 표시됩니다.";
    return;
  }

  const predictionKeys = seriesKeys.filter((key) => key !== "actual");
  const summaries = predictionKeys.map(modelMetrics).filter((item) => item.count > 0);
  const best = summaries.reduce((winner, item) => (!winner || item.mae < winner.mae ? item : winner), null);
  const entsoe = summaries.find((item) => item.key === "entsoe_forecast");
  const bestModel = summaries
    .filter((item) => item.key !== "entsoe_forecast")
    .reduce((winner, item) => (!winner || item.mae < winner.mae ? item : winner), null);

  if (entsoe && bestModel) {
    const diff = entsoe.mae - bestModel.mae;
    winnerText.textContent = diff > 0
      ? `${bestModel.key}가 ENTSO-E보다 MAE ${formatNumber(diff)} MW 낮아 우위입니다.`
      : `ENTSO-E가 모델 예측보다 MAE ${formatNumber(Math.abs(diff))} MW 낮아 우위입니다.`;
  } else if (best) {
    winnerText.textContent = `${best.key}가 이 기간에서 가장 낮은 MAE를 보입니다.`;
  }

  modelSummary.innerHTML = summaries.map((item) => `
    <article class="summary-card ${best && item.key === best.key ? "best" : ""}">
      <h3>${item.key}</h3>
      ${best && item.key === best.key ? '<span class="badge">Best MAE</span>' : ''}
      <dl>
        <div><dt>평균 예측</dt><dd>${formatNumber(item.averagePrediction)} MW</dd></div>
        <div><dt>MAE</dt><dd>${formatNumber(item.mae)} MW</dd></div>
        <div><dt>RMSE</dt><dd>${formatNumber(item.rmse)} MW</dd></div>
        <div><dt>MAPE</dt><dd>${formatNumber(item.mape)}%</dd></div>
      </dl>
    </article>
  `).join("");
}

function renderTable() {
  if (!rows.length) {
    tableHead.innerHTML = "";
    tableBody.innerHTML = "";
    return;
  }
  const columns = ["timestamp", ...seriesKeys];
  tableHead.innerHTML = `<tr>${columns.map((column) => `<th>${column}</th>`).join("")}</tr>`;
  tableBody.innerHTML = rows.slice(0, 300).map((row) => `
    <tr>${columns.map((column) => `<td>${column === "timestamp" ? row[column] : formatNumber(row[column])}</td>`).join("")}</tr>
  `).join("");
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = csvInput.files[0];
  if (!file) {
    updateStatus("CSV 파일을 선택하세요.", true);
    return;
  }

  const formData = new FormData();
  formData.append("file", file);
  formData.append("start", startInput.value);
  formData.append("end", endInput.value);

  updateStatus("모델 예측 중...");
  try {
    const response = await fetch("/predict", { method: "POST", body: formData });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "예측 요청에 실패했습니다.");

    rows = payload.rows;
    seriesKeys = ["actual"];
    if (rows[0]?.entsoe_forecast !== undefined) seriesKeys.push("entsoe_forecast");
    seriesKeys.push(...payload.models);

    renderMetrics(payload);
    renderLegend();
    renderSummary();
    renderTable();
    drawChart();
    updateStatus(`완료: ${payload.row_count}개 행을 예측했습니다.`);
  } catch (error) {
    updateStatus(error.message, true);
  }
});

window.addEventListener("resize", drawChart);
drawChart();

