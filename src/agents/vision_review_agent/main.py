import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from src.core.config import settings
from src.services.vision_detection_service import VisionDetectionService
from src.vision.annotation import save_annotated_image
from src.vision.image_loader import load_rgb_image


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def iter_image_paths(input_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in input_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def review_images(input_dir: Path, output_dir: Path) -> dict:
    service = VisionDetectionService(settings)
    image_paths = iter_image_paths(input_dir)
    results = []

    for image_path in image_paths:
        image = load_rgb_image(image_path.read_bytes())
        response = service.detect(image)
        annotated_path = output_dir / "annotated" / f"{image_path.stem}.annotated.jpg"
        save_annotated_image(
            image,
            response.detections,
            annotated_path,
            response.safety_net_review,
        )
        response.annotated_image_path = str(annotated_path)
        response.annotated_image_url = f"/vision-results/annotated/{annotated_path.name}"
        result = {
            "source_file": str(image_path),
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            **response.model_dump(),
        }
        results.append(result)
        write_json(output_dir / f"{image_path.stem}.vision.json", result)

    summary = {
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "model_name": settings.model_name,
        "model_path": str(settings.model_path),
        "total_images": len(image_paths),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
    }
    write_json(output_dir / "summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run vision review for images and save JSON results.")
    parser.add_argument("--input-dir", type=Path, default=settings.input_dir)
    parser.add_argument("--output-dir", type=Path, default=settings.output_dir)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = review_images(args.input_dir, args.output_dir)
    print(f"reviewed {summary['total_images']} image(s)")
    print(f"results saved to {summary['output_dir']}")


if __name__ == "__main__":
    main()
