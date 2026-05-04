from functools import lru_cache
from typing import Any, Optional, Tuple

from PIL import Image

from src.core.config import Settings
from src.schemas.vision import Detection, DetectionResponse, EquipmentReview


class VisionDetectionService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @lru_cache(maxsize=1)
    def load_model(self) -> Any:
        if not self.settings.model_path.is_file():
            raise FileNotFoundError(f"model file not found: {self.settings.model_path}")

        from ultralytics import YOLO

        return YOLO(str(self.settings.model_path))

    def detect(self, image: Image.Image) -> DetectionResponse:
        model = self.load_model()
        predict_kwargs: dict[str, Any] = {
            "conf": self.settings.model_conf,
            "iou": self.settings.model_iou,
            "verbose": False,
        }

        if self.settings.model_device != "auto":
            predict_kwargs["device"] = self.settings.model_device

        results = model.predict(image, **predict_kwargs)
        boxes = results[0].boxes
        detections: list[Detection] = []

        if boxes is not None:
            for box in boxes:
                class_id = int(box.cls.item())
                class_code = self.settings.class_names.get(class_id, str(class_id))
                class_label = self.settings.class_labels.get(class_code, {})
                is_wearing = class_label.get("is_wearing")
                confidence = round(float(box.conf.item()), 4)
                needs_review = bool(
                    is_wearing is True
                    and confidence < self.settings.review_confidence_threshold
                )
                xyxy = [round(float(value), 2) for value in box.xyxy[0].tolist()]
                detections.append(
                    Detection(
                        class_id=class_id,
                        class_code=class_code,
                        equipment=class_label.get("equipment"),
                        label=class_label.get("label"),
                        is_wearing=is_wearing,
                        needs_review=needs_review,
                        box_color=self._box_color(is_wearing, needs_review),
                        confidence=confidence,
                        bbox_xyxy=xyxy,
                    )
                )

        reviews = self._build_reviews(detections)
        overall_status, is_appropriate, message = self._build_overall_result(reviews)
        return DetectionResponse(
            model_name=self.settings.model_name,
            image_width=image.width,
            image_height=image.height,
            overall_status=overall_status,
            is_appropriate=is_appropriate,
            message=message,
            reviews=reviews,
            detections=detections,
        )

    def _build_reviews(self, detections: list[Detection]) -> list[EquipmentReview]:
        reviews: list[EquipmentReview] = []

        for equipment in ("safety_helmet", "safety_shoes", "safety_belt"):
            matches = [detection for detection in detections if detection.equipment == equipment]
            if not matches:
                reviews.append(
                    EquipmentReview(
                        equipment=equipment,
                        equipment_label=self.settings.equipment_labels[equipment],
                        status="unknown",
                        is_appropriate=None,
                        confidence=None,
                        reason="관련 객체가 탐지되지 않았습니다.",
                    )
                )
                continue

            not_wearing_matches = [detection for detection in matches if detection.is_wearing is False]
            if not_wearing_matches:
                best = max(not_wearing_matches, key=lambda detection: detection.confidence)
                reviews.append(
                    EquipmentReview(
                        equipment=equipment,
                        equipment_label=self.settings.equipment_labels[equipment],
                        status="not_wearing",
                        is_appropriate=False,
                        confidence=best.confidence,
                        reason=f"{best.label} 탐지 결과를 기준으로 부적정 판단했습니다.",
                    )
                )
                continue

            valid_wearing_matches = [
                detection
                for detection in matches
                if detection.is_wearing is True and not detection.needs_review
            ]
            if valid_wearing_matches:
                best = max(valid_wearing_matches, key=lambda detection: detection.confidence)
                reviews.append(
                    EquipmentReview(
                        equipment=equipment,
                        equipment_label=self.settings.equipment_labels[equipment],
                        status="wearing",
                        is_appropriate=True,
                        confidence=best.confidence,
                        reason=f"{best.label} 탐지 결과를 기준으로 판단했습니다.",
                    )
                )
                continue

            best = max(matches, key=lambda detection: detection.confidence)
            reviews.append(
                EquipmentReview(
                    equipment=equipment,
                    equipment_label=self.settings.equipment_labels[equipment],
                    status="needs_review",
                    is_appropriate=None,
                    confidence=best.confidence,
                    reason=(
                        f"{best.label} confidence가 "
                        f"{self.settings.review_confidence_threshold:.2f} 미만이라 검토가 필요합니다."
                    ),
                )
            )

        return reviews

    def _build_overall_result(
        self, reviews: list[EquipmentReview]
    ) -> Tuple[str, Optional[bool], str]:
        not_wearing = [review for review in reviews if review.is_appropriate is False]
        unknown = [review for review in reviews if review.is_appropriate is None]

        if not_wearing:
            labels = ", ".join(review.equipment_label for review in not_wearing)
            return "not_appropriate", False, f"{labels} 항목이 부적정으로 판단되었습니다."

        if unknown:
            labels = ", ".join(review.equipment_label for review in unknown)
            return "needs_review", None, f"{labels} 항목은 검토가 필요합니다."

        return "appropriate", True, "안전모, 안전화, 안전벨트가 모두 적정으로 판단되었습니다."

    def _box_color(self, is_wearing: object, needs_review: bool) -> str:
        if needs_review:
            return "yellow"
        if is_wearing is False:
            return "red"
        return "blue"
