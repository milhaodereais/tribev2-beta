from fastapi import FastAPI
from tribev2 import TribeModel

app = FastAPI()

model = None

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/load-model")
def load_model():
    global model
    model = TribeModel.from_pretrained("facebook/tribev2", cache_folder="./cache")
    return {"status": "model loaded"}

@app.get("/status")
def status():
    return {"model_loaded": model is not None}
