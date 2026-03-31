const btnCheckStatus = document.getElementById("btnCheckStatus");
const btnLoadModel = document.getElementById("btnLoadModel");
const btnAnalyze = document.getElementById("btnAnalyze");
const btnClearResult = document.getElementById("btnClearResult");

const videoFile = document.getElementById("videoFile");
const selectedFile = document.getElementById("selectedFile");

const statusBadge = document.getElementById("statusBadge");
const statusText = document.getElementById("statusText");
const pathInfo = document.getElementById("pathInfo");

const modelLoading = document.getElementById("modelLoading");
const predictLoading = document.getElementById("predictLoading");

const resultBox = document.getElementById("resultBox");
const summaryBox = document.getElementById("summaryBox");

function setBadge(type, text) {
  statusBadge.className = `status-badge ${type}`;
  statusBadge.textContent = text;
}

function setResult(data) {
  resultBox.textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
}

function setSummary(text) {
  summaryBox.textContent = text;
}

function buildSummary(data) {
  if (!data || typeof data !== "object") {
    return "Não foi possível gerar resumo.";
  }

  if (data.detail) {
    return `Erro:\n${data.detail}`;
  }

  const lines = [];

  if (data.status) {
    lines.push(`Status: ${data.status}`);
  }

  if (data.filename) {
    lines.push(`Arquivo: ${data.filename}`);
  }

  if (typeof data.events_rows !== "undefined") {
    lines.push(`Linhas de eventos: ${data.events_rows}`);
  }

  if (Array.isArray(data.predictions_shape) && data.predictions_shape.length > 0) {
    lines.push(`Shape das predições: ${data.predictions_shape.join(" x ")}`);
  }

  if (typeof data.segments_count !== "undefined") {
    lines.push(`Quantidade de segmentos: ${data.segments_count}`);
  }

  if (data.predictions_summary && typeof data.predictions_summary === "object") {
    const stats = data.predictions_summary;
    lines.push("");
    lines.push("Resumo estatístico:");
    if (typeof stats.mean !== "undefined") lines.push(`- mean: ${stats.mean}`);
    if (typeof stats.std !== "undefined") lines.push(`- std: ${stats.std}`);
    if (typeof stats.min !== "undefined") lines.push(`- min: ${stats.min}`);
    if (typeof stats.max !== "undefined") lines.push(`- max: ${stats.max}`);
    if (typeof stats.warning !== "undefined") lines.push(`- aviso: ${stats.warning}`);
  }

  if (Array.isArray(data.segments_preview) && data.segments_preview.length > 0) {
    lines.push("");
    lines.push("Prévia de segmentos:");
    lines.push(JSON.stringify(data.segments_preview, null, 2));
  }

  return lines.length > 0 ? lines.join("\n") : "Sem dados suficientes para resumir.";
}

async function parseResponse(res) {
  const contentType = res.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    return await res.json();
  }

  const text = await res.text();
  return { detail: text || "Resposta sem conteúdo." };
}

async function refreshStatus() {
  try {
    btnCheckStatus.disabled = true;
    setBadge("status-warn", "Consultando...");
    statusText.textContent = "Consultando status atual da API.";
    pathInfo.textContent = "";

    const res = await fetch("/api/status");
    const data = await parseResponse(res);

    if (!res.ok) {
      throw new Error(data.detail || "Falha ao consultar status.");
    }

    if (data.model_loaded) {
      setBadge("status-ok", "Modelo carregado");
      statusText.textContent = `Modelo ativo: ${data.model_name}`;
    } else {
      setBadge("status-warn", "Modelo não carregado");
      statusText.textContent = `Modelo disponível para carga: ${data.model_name}`;
    }

    if (data.paths) {
      pathInfo.textContent =
        `templates: ${data.paths.templates_dir} | static: ${data.paths.static_dir} | cache: ${data.paths.cache_dir}`;
    }

    setResult(data);
    setSummary(buildSummary(data));
  } catch (error) {
    setBadge("status-error", "Erro no status");
    statusText.textContent = error.message || String(error);
    setResult({ detail: error.message || String(error) });
    setSummary(`Erro ao consultar status:\n${error.message || String(error)}`);
  } finally {
    btnCheckStatus.disabled = false;
  }
}

async function loadModel() {
  try {
    btnLoadModel.disabled = true;
    modelLoading.classList.add("visible");
    setBadge("status-warn", "Carregando modelo...");
    statusText.textContent = "A API está baixando/carregando o modelo.";

    const res = await fetch("/api/load-model", {
      method: "POST"
    });

    const data = await parseResponse(res);

    if (!res.ok) {
      throw new Error(data.detail || "Falha ao carregar modelo.");
    }

    setBadge("status-ok", "Modelo carregado");
    statusText.textContent = data.message || "Modelo carregado com sucesso.";
    setResult(data);
    setSummary(buildSummary(data));
  } catch (error) {
    setBadge("status-error", "Erro ao carregar modelo");
    statusText.textContent = error.message || String(error);
    setResult({ detail: error.message || String(error) });
    setSummary(`Erro ao carregar modelo:\n${error.message || String(error)}`);
  } finally {
    modelLoading.classList.remove("visible");
    btnLoadModel.disabled = false;
  }
}

async function analyzeVideo() {
  try {
    const file = videoFile.files[0];

    if (!file) {
      alert("Selecione um vídeo antes de analisar.");
      return;
    }

    btnAnalyze.disabled = true;
    predictLoading.classList.add("visible");
    setResult("Enviando vídeo e processando análise...");
    setSummary("Processando vídeo. Aguarde a resposta da API.");

    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch("/api/predict", {
      method: "POST",
      body: formData
    });

    const data = await parseResponse(res);

    if (!res.ok) {
      throw new Error(data.detail || "Erro ao analisar vídeo.");
    }

    setResult(data);
    setSummary(buildSummary(data));
  } catch (error) {
    const message = error.message || String(error);
    setResult({ detail: message });
    setSummary(`Erro durante a análise:\n${message}`);
  } finally {
    predictLoading.classList.remove("visible");
    btnAnalyze.disabled = false;
  }
}

function clearResult() {
  setResult("Nenhuma operação executada ainda.");
  setSummary("Ainda não há resumo disponível.");
}

videoFile.addEventListener("change", () => {
  const file = videoFile.files[0];
  selectedFile.textContent = file
    ? `Arquivo selecionado: ${file.name} (${Math.round(file.size / 1024)} KB)`
    : "Nenhum arquivo selecionado.";
});

btnCheckStatus.addEventListener("click", refreshStatus);
btnLoadModel.addEventListener("click", loadModel);
btnAnalyze.addEventListener("click", analyzeVideo);
btnClearResult.addEventListener("click", clearResult);

refreshStatus();
