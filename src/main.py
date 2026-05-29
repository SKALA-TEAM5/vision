import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles

from src.core.config import settings
from src.schemas.vision import (
    DetectionResponse,
    PpeDetectionResponse,
    SafetyNetDetectionResponse,
    SourceDetectionRequest,
)
from src.services.vision_detection_service import VisionDetectionService
from src.vision.annotation import save_annotated_image
from src.vision.image_loader import load_rgb_image, load_rgb_image_from_uri


app = FastAPI(title="Safety Vision API", version="0.1.0")
vision_service = VisionDetectionService(settings)
settings.output_dir.mkdir(parents=True, exist_ok=True)
app.mount("/vision-results", StaticFiles(directory=str(settings.output_dir)), name="vision-results")
app.mount("/vision-files", StaticFiles(directory=str(settings.input_dir)), name="vision-files")


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "model_name": settings.model_name,
        "model_path": str(settings.model_path),
        "model_exists": settings.model_path.exists(),
        "model_is_file": settings.model_path.is_file(),
        "safety_net_model_name": settings.safety_net_model_name,
        "safety_net_model_path": str(settings.safety_net_model_path),
        "safety_net_model_exists": settings.safety_net_model_path.exists(),
        "safety_net_model_is_file": settings.safety_net_model_path.is_file(),
        "device": settings.model_device,
    }


@app.get("/labels")
def labels() -> dict[int, str]:
    return settings.class_names


@app.post("/detect", response_model=DetectionResponse)
async def detect(file: UploadFile = File(...)) -> DetectionResponse:
    image = await _load_upload_image(file)

    try:
        response = vision_service.detect(image)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    output_path = _upload_annotated_output_path(file.filename, "combined")
    save_annotated_image(
        image,
        response.detections,
        output_path,
        response.safety_net_review,
    )
    response.annotated_image_path = str(output_path)
    response.annotated_image_url = _annotated_image_url(output_path)
    return response


@app.post("/detect/source", response_model=DetectionResponse)
async def detect_source(request: SourceDetectionRequest) -> DetectionResponse:
    image = _load_source_image(request.source_uri)

    try:
        response = vision_service.detect(image)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    response.source_id = request.source_id
    response.source_uri = request.source_uri
    response.source_image_url = _source_image_url(request.source_uri)
    output_path = _annotated_output_path(request, "combined")
    save_annotated_image(
        image,
        response.detections,
        output_path,
        response.safety_net_review,
    )
    response.annotated_image_path = str(output_path)
    response.annotated_image_url = _annotated_image_url(output_path)
    return response


@app.post("/detect/ppe", response_model=PpeDetectionResponse)
async def detect_ppe(file: UploadFile = File(...)) -> PpeDetectionResponse:
    image = await _load_upload_image(file)

    try:
        response = vision_service.detect_ppe(image)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return response


@app.post("/detect/ppe/source", response_model=PpeDetectionResponse)
async def detect_ppe_source(request: SourceDetectionRequest) -> PpeDetectionResponse:
    image = _load_source_image(request.source_uri)

    try:
        response = vision_service.detect_ppe(image)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    response.source_id = request.source_id
    response.source_uri = request.source_uri
    response.source_image_url = _source_image_url(request.source_uri)
    return response


@app.post("/detect/safety-net", response_model=SafetyNetDetectionResponse)
async def detect_safety_net(file: UploadFile = File(...)) -> SafetyNetDetectionResponse:
    image = await _load_upload_image(file)

    try:
        response = vision_service.detect_safety_net(image)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    output_path = _upload_annotated_output_path(file.filename, "safety-net")
    save_annotated_image(image, [], output_path, response.safety_net_review)
    response.annotated_image_path = str(output_path)
    response.annotated_image_url = _annotated_image_url(output_path)
    return response


@app.post("/detect/safety-net/source", response_model=SafetyNetDetectionResponse)
async def detect_safety_net_source(request: SourceDetectionRequest) -> SafetyNetDetectionResponse:
    image = _load_source_image(request.source_uri)

    try:
        response = vision_service.detect_safety_net(image)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    response.source_id = request.source_id
    response.source_uri = request.source_uri
    response.source_image_url = _source_image_url(request.source_uri)
    output_path = _annotated_output_path(request, "safety-net")
    save_annotated_image(image, [], output_path, response.safety_net_review)
    response.annotated_image_path = str(output_path)
    response.annotated_image_url = _annotated_image_url(output_path)
    return response


async def _load_upload_image(file: UploadFile):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="file must be an image")

    try:
        return load_rgb_image(await file.read())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _load_source_image(source_uri: str):
    try:
        return load_rgb_image_from_uri(source_uri, settings.input_dir)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _annotated_output_path(request: SourceDetectionRequest, result_type: str) -> Path:
    base_name = request.source_id or _source_name(request.source_uri)
    return _named_annotated_output_path(base_name, result_type)


def _upload_annotated_output_path(filename: str | None, result_type: str) -> Path:
    return _named_annotated_output_path(Path(filename or "uploaded").stem, result_type)


def _named_annotated_output_path(base_name: str, result_type: str) -> Path:
    safe_name = re.sub(r"[^0-9A-Za-z가-힣_.-]+", "_", base_name).strip("._")
    if not safe_name:
        safe_name = "uploaded"
    return settings.output_dir / "annotated" / result_type / f"{safe_name}.annotated.jpg"


def _source_name(source_uri: str) -> str:
    parsed = urlparse(source_uri)
    if parsed.scheme in ("http", "https"):
        return Path(parsed.path).stem
    return Path(source_uri).stem


def _annotated_image_url(output_path: Path) -> str:
    relative_path = output_path.relative_to(settings.output_dir)
    return f"/vision-results/{relative_path.as_posix()}"


def _source_image_url(source_uri: str) -> str:
    parsed = urlparse(source_uri)
    if parsed.scheme in ("http", "https"):
        return source_uri
    return f"/vision-files/{Path(source_uri).name}"
