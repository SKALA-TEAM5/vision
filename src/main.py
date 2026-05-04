from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles

from src.core.config import settings
from src.schemas.vision import DetectionResponse
from src.services.vision_detection_service import VisionDetectionService
from src.vision.annotation import save_annotated_image
from src.vision.image_loader import load_rgb_image


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
        "device": settings.model_device,
    }


@app.get("/labels")
def labels() -> dict[int, str]:
    return settings.class_names


@app.post("/detect", response_model=DetectionResponse)
async def detect(file: UploadFile = File(...)) -> DetectionResponse:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="file must be an image")

    try:
        image = load_rgb_image(await file.read())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        response = vision_service.detect(image)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    output_path = settings.output_dir / "annotated" / f"{file.filename or 'uploaded'}.annotated.jpg"
    save_annotated_image(image, response.detections, output_path)
    response.annotated_image_path = str(output_path)
    response.annotated_image_url = f"/vision-results/annotated/{output_path.name}"
    return response
