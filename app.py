from pathlib import Path
import shutil
import tempfile
import traceback

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from tribev2 import TribeModel

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
UPLOAD_DIR = BASE_DIR / "uploads"
CACHE_DIR = BASE_DIR / "cache"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="TRIBEv2 Analyzer API")

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

model = None
MODEL_NAME = "facebook/tribev2"


def ensure_required_dirs() -> None:
    if not TEMPLATES_DIR.exists():
        raise RuntimeError(f"Diretório de templates não encontrado: {TEMPLATES_DIR}")
    if not (TEMPLATES_DIR / "index.html").exists():
        raise RuntimeError(f"Arquivo index.html não encontrado em: {TEMPLATES_DIR}")
    if not STATIC_DIR.exists():
        raise RuntimeError(f"Diretório static não encontrado: {STATIC_DIR}")


def to_serializable(value):
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool, dict, list)):
        return value

    if hasattr(value, "tolist"):
        return value.tolist()

    if isinstance(value, tuple):
        return [to_serializable(v) for v in value]

    return str(value)


@app.on_event("startup")
def startup_checks():
    ensure_required_dirs()


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/status")
def status():
    return {
        "status": "ok",
        "model_loaded": model is not None,
        "model_name": MODEL_NAME,
        "paths": {
            "base_dir": str(BASE_DIR),
            "templates_dir": str(TEMPLATES_DIR),
            "static_dir": str(STATIC_DIR),
            "uploads_dir": str(UPLOAD_DIR),
            "cache_dir": str(CACHE_DIR),
        },
    }


@app.post("/api/load-model")
def load_model():
    global model

    try:
        model = TribeModel.from_pretrained(
            MODEL_NAME,
            cache_folder=str(CACHE_DIR),
        )
        return {
            "status": "ok",
            "message": "Modelo carregado com sucesso",
            "model_name": MODEL_NAME,
            "cache_dir": str(CACHE_DIR),
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao carregar modelo: {e}",
        )


@app.post("/api/predict")
async def predict_video(file: UploadFile = File(...)):
    global model

    if model is None:
        raise HTTPException(
            status_code=400,
            detail="Modelo não carregado. Clique em 'Carregar Modelo' primeiro.",
        )

    if not file.filename:
        raise HTTPException(status_code=400, detail="Arquivo inválido.")

    suffix = Path(file.filename).suffix.lower()
    allowed = {".mp4", ".mov", ".avi", ".mkv", ".webm"}

    if suffix not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Formato não suportado. Use um destes: {sorted(allowed)}",
        )

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
            dir=str(UPLOAD_DIR),
        ) as tmp:
            temp_path = Path(tmp.name)
            shutil.copyfileobj(file.file, tmp)

        df = model.get_events_dataframe(video_path=str(temp_path))
        preds, segments = model.predict(events=df)

        response = {
            "status": "ok",
            "filename": file.filename,
            "saved_temp_file": str(temp_path),
            "events_rows": int(len(df)),
            "events_columns": list(df.columns) if hasattr(df, "columns") else [],
            "predictions_shape": list(preds.shape) if hasattr(preds, "shape") else [],
            "segments_count": len(segments) if segments is not None else 0,
            "segments_preview": to_serializable(segments[:5]) if segments is not None else [],
        }

        try:
            response["predictions_summary"] = {
                "mean": float(preds.mean()),
                "std": float(preds.std()),
                "min": float(preds.min()),
                "max": float(preds.max()),
            }
        except Exception as summary_error:
            response["predictions_summary"] = {
                "warning": f"Não foi possível calcular resumo estatístico: {summary_error}"
            }

        return JSONResponse(content=jsonable_encoder(response))

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar vídeo: {e}",
        )

    finally:
        try:
            if temp_path and temp_path.exists():
                temp_path.unlink(missing_ok=True)
        except Exception:
            pass
        try:
            await file.close()
        except Exception:
            pass
