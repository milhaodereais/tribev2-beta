from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import shutil
import tempfile
import traceback

from tribev2 import TribeModel

app = FastAPI()

model = None
MODEL_NAME = "facebook/tribev2"
CACHE_DIR = "./cache"
UPLOAD_DIR = Path("./uploads")

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
Path("./templates").mkdir(parents=True, exist_ok=True)
Path("./static").mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/status")
def status():
    return {
        "status": "ok",
        "model_loaded": model is not None,
        "model_name": MODEL_NAME,
    }


@app.post("/api/load-model")
def load_model():
    global model
    try:
        model = TribeModel.from_pretrained(MODEL_NAME, cache_folder=CACHE_DIR)
        return {
            "status": "ok",
            "message": "Modelo carregado com sucesso",
            "model_name": MODEL_NAME,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao carregar modelo: {e}")


@app.post("/api/predict")
async def predict_video(file: UploadFile = File(...)):
    global model

    if model is None:
        raise HTTPException(
            status_code=400,
            detail="Modelo não carregado. Clique em 'Carregar Modelo' primeiro."
        )

    if not file.filename:
        raise HTTPException(status_code=400, detail="Arquivo inválido.")

    suffix = Path(file.filename).suffix.lower()
    allowed = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
    if suffix not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Formato não suportado. Use um destes: {sorted(allowed)}"
        )

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=UPLOAD_DIR) as tmp:
            temp_path = Path(tmp.name)
            shutil.copyfileobj(file.file, tmp)

        df = model.get_events_dataframe(video_path=str(temp_path))
        preds, segments = model.predict(events=df)

        response = {
            "status": "ok",
            "filename": file.filename,
            "events_rows": int(len(df)),
            "predictions_shape": list(preds.shape),
            "segments_count": len(segments) if segments is not None else 0,
            "segments_preview": segments[:5] if segments is not None else [],
        }

        try:
            response["predictions_summary"] = {
                "mean": float(preds.mean()),
                "std": float(preds.std()),
                "min": float(preds.min()),
                "max": float(preds.max()),
            }
        except Exception:
            response["predictions_summary"] = "Não foi possível calcular resumo estatístico."

        return JSONResponse(content=response)

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro ao processar vídeo: {e}")

    finally:
        try:
            if temp_path and temp_path.exists():
                temp_path.unlink(missing_ok=True)
        except Exception:
            pass
