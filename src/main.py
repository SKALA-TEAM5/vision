from typing import Any

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

    output_path = settings.output_dir / "annotated" / f"{file.filename or 'uploaded'}.annotated.jpg"
    save_annotated_image(
        image,
        response.detections,
        output_path,
        response.safety_net_review,
    )
    response.annotated_image_path = str(output_path)
    response.annotated_image_url = f"/vision-results/annotated/{output_path.name}"
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
    return response


@app.post("/detect/ppe", response_model=PpeDetectionResponse)
async def detect_ppe(file: UploadFile = File(...)) -> PpeDetectionResponse:
    image = await _load_upload_image(file)

    try:
        response = vision_service.detect_ppe(image)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    output_path = settings.output_dir / "annotated" / f"{file.filename or 'uploaded'}.ppe.annotated.jpg"
    save_annotated_image(image, response.detections, output_path)
    response.annotated_image_path = str(output_path)
    response.annotated_image_url = f"/vision-results/annotated/{output_path.name}"
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
    return response


@app.post("/detect/safety-net", response_model=SafetyNetDetectionResponse)
async def detect_safety_net(file: UploadFile = File(...)) -> SafetyNetDetectionResponse:
    image = await _load_upload_image(file)

    try:
        return vision_service.detect_safety_net(image)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/detect/safety-net/source", response_model=SafetyNetDetectionResponse)
async def detect_safety_net_source(request: SourceDetectionRequest) -> SafetyNetDetectionResponse:
    image = _load_source_image(request.source_uri)

    try:
        response = vision_service.detect_safety_net(image)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    response.source_id = request.source_id
    response.source_uri = request.source_uri
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
        return load_rgb_image_from_uri(source_uri)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
