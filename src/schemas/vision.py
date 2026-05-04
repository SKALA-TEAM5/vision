from pydantic import BaseModel, Field
from typing import Optional


class Detection(BaseModel):
    class_id: int
    class_code: str
    equipment: Optional[str] = None
    label: Optional[str] = None
    is_wearing: Optional[bool] = None
    needs_review: bool = False
    box_color: str
    confidence: float = Field(ge=0, le=1)
    bbox_xyxy: list[float]


class EquipmentReview(BaseModel):
    equipment: str
    equipment_label: str
    status: str
    is_appropriate: Optional[bool]
    confidence: Optional[float]
    reason: str


class DetectionResponse(BaseModel):
    model_name: str
    image_width: int
    image_height: int
    overall_status: str
    is_appropriate: Optional[bool]
    message: str
    annotated_image_path: Optional[str] = None
    annotated_image_url: Optional[str] = None
    reviews: list[EquipmentReview]
    detections: list[Detection]
