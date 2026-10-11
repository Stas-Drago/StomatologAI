"""Local-only API: uploaded images live only for the duration of one request."""
from __future__ import annotations

import html
import logging
import os
import tempfile
from functools import lru_cache
from pathlib import Path
from threading import Lock

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

MAX_IMAGE_BYTES = 10 * 1024 * 1024
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}

app = FastAPI(title="DentalHelper Local API", version="1.0.0")
logger = logging.getLogger("DentalHelperAPI")
model_error: str | None = None
model_lock = Lock()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000", "http://127.0.0.1:5173", "http://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@lru_cache(maxsize=1)
def classifier():
    """Load the ML model only when the first image is actually submitted."""
    from agent.agent import DentalYOLOClassifier

    return DentalYOLOClassifier()


@lru_cache(maxsize=1)
def report_agent():
    from agent.agent import DentalGemmaAgent

    return DentalGemmaAgent()


@app.on_event("startup")
def preload_classifier() -> None:
    """Load the small local classifier once; the LLM remains managed by Ollama."""
    global model_error
    with model_lock:
        try:
            classifier()
            model_error = None
        except Exception as exc:
            model_error = str(exc)


def _validate_coordinates(lat: float, lon: float) -> None:
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise HTTPException(status_code=422, detail="Некорректные координаты.")


@app.get("/health")
def health() -> dict[str, str | bool | None]:
    return {"status": "ok", "mode": "local", "classifier_ready": model_error is None, "classifier_error": model_error}


@app.get("/api/status")
def status() -> dict[str, str | bool | None]:
    preload_classifier()
    return {"classifier_ready": model_error is None, "classifier_error": model_error}


@app.post("/api/analyze")
async def analyze(image: UploadFile = File(...)) -> dict:
    from starlette.concurrency import run_in_threadpool
    await run_in_threadpool(preload_classifier)
    if model_error:
        await image.close()
        raise HTTPException(status_code=503, detail=model_error)
    if image.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="Поддерживаются JPG, PNG и WEBP.")

    raw_image = await image.read()
    if not raw_image or len(raw_image) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Размер изображения должен быть не больше 10 МБ.")

    try:
        from PIL import Image, UnidentifiedImageError

        with Image.open(__import__("io").BytesIO(raw_image)) as uploaded:
            uploaded.verify()
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="Не найдена библиотека Pillow. Установите зависимости проекта.") from exc
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=422, detail="Файл не является корректным изображением.")

    suffix = Path(image.filename or "image.jpg").suffix.lower() or ".jpg"
    temp_path = ""
    try:
        with tempfile.NamedTemporaryFile(prefix="dentalhelper-", suffix=suffix, delete=False) as temporary:
            temporary.write(raw_image)
            temp_path = temporary.name

        yolo_result = classifier().predict(temp_path)
        if "error" in yolo_result:
            raise HTTPException(status_code=503, detail="Модель не смогла обработать фотографию.")

        report = html.unescape(report_agent().generate_report(yolo_result))
        return {**yolo_result, "report": report}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Локальные модели сейчас недоступны. Проверьте Ollama и путь к YOLO-модели.") from exc
    finally:
        if temp_path:
            try:
                os.remove(temp_path)
            except FileNotFoundError:
                pass
        await image.close()


@app.get("/api/clinics")
def clinics(lat: float = Query(...), lon: float = Query(...)) -> dict:
    _validate_coordinates(lat, lon)
    from web_api.clinic_search import get_nearby_dentists

    return {"clinics": get_nearby_dentists(lat, lon, radius=5000)}


@app.get("/api/geocode")
def geocode(q: str = Query(..., min_length=3, max_length=180)) -> dict:
    try:
        import requests
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="Не найдена библиотека requests. Установите зависимости проекта.") from exc

    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": q, "format": "jsonv2", "limit": 1, "countrycodes": "ru"},
            headers={"User-Agent": "DentalHelper-local/1.0"},
            timeout=12,
        )
        response.raise_for_status()
        places = response.json()
        if not places:
            raise HTTPException(status_code=404, detail="Адрес не найден. Уточните запрос или выберите точку на карте.")
        return {"lat": float(places[0]["lat"]), "lon": float(places[0]["lon"]), "label": places[0]["display_name"]}
    except HTTPException:
        raise
    except requests.RequestException as exc:
        raise HTTPException(status_code=503, detail="Сервис геокодирования временно недоступен.") from exc
