const modelStatus = document.getElementById("modelStatus");
const modelInfo = document.getElementById("modelInfo");
const resultBox = document.getElementById("resultBox");

const checkStatusBtn = document.getElementById("checkStatusBtn");
const loadModelBtn = document.getElementById("loadModelBtn");
const analyzeBtn = document.getElementById("analyzeBtn");
const videoFile = document.getElementById("videoFile");

function setStatus(type, text) {
  modelStatus.className = `status ${type}`;
  modelStatus.textContent = text;
}

async function refreshStatus() {
  try {
    setStatus("warn", "Consultando...");
    const res = await fetch("/api/status");
    const data = await res.json();

    if (data.model_loaded) {
      setStatus("ok", "Modelo carregado");
    } else {
      setStatus("warn", "Modelo ainda não carregado");
    }

    modelInfo.textContent = `Modelo: ${data.model_name}`;
  } catch (err) {
    setStatus("error", "Erro ao consultar status");
    modelInfo.textContent = String(err);
  }
}

async function loadModel() {
  try {
    loadModelBtn.disabled = true;
    setStatus("warn", "Carregando modelo... isso pode levar um tempo");
    resultBox.textContent = "Carregando modelo...";

    const res = await fetch("/api/load-model", {
      method: "POST"
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || "Falha ao carregar modelo");
    }

    setStatus("ok", "Modelo carregado com sucesso");
    modelInfo.textContent = `Modelo: ${data.model_name}`;
    resultBox.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    setStatus("error", "Erro ao carregar modelo");
    resultBox.textContent = String(err);
  } finally {
    loadModelBtn.disabled = false;
  }
}

async function analyzeVideo() {
  try {
    const file = videoFile.files[0];
    if (!file) {
      alert("Selecione um vídeo primeiro.");
      return;
    }

    analyzeBtn.disabled = true;
    resultBox.textContent = "Enviando vídeo e processando análise... isso pode demorar.";

    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch("/api/predict", {
      method: "POST",
      body: formData
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || "Erro ao analisar vídeo");
    }

    resultBox.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    resultBox.textContent = String(err);
  } finally {
    analyzeBtn.disabled = false;
  }
}

checkStatusBtn.addEventListener("click", refreshStatus);
loadModelBtn.addEventListener("click", loadModel);
analyzeBtn.addEventListener("click", analyzeVideo);

refreshStatus();
