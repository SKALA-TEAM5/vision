from pathlib import Path
from typing import Union

from PIL import Image, ImageDraw, ImageFont

from src.schemas.vision import Detection


BOX_COLORS = {
    "blue": (37, 99, 235),
    "red": (220, 38, 38),
    "yellow": (202, 138, 4),
}

FONT_CANDIDATES = (
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
)


def load_label_font(image: Image.Image) -> Union[ImageFont.FreeTypeFont, ImageFont.ImageFont]:
    font_size = max(26, min(image.width, image.height) // 38)

    for font_path in FONT_CANDIDATES:
        if Path(font_path).is_file():
            return ImageFont.truetype(font_path, font_size)

    return ImageFont.load_default()


def save_annotated_image(
    image: Image.Image,
    detections: list[Detection],
    output_path: Path,
) -> None:
    annotated = image.copy()
    draw = ImageDraw.Draw(annotated)
    font = load_label_font(image)
    line_width = max(5, min(image.width, image.height) // 150)
    padding_x = max(10, line_width * 2)
    padding_y = max(8, line_width)
    placed_labels: list[tuple[float, float, float, float]] = []

    for detection in detections:
        color = BOX_COLORS.get(detection.box_color, (107, 114, 128))
        x1, y1, x2, y2 = detection.bbox_xyxy
        label = detection.label or detection.class_code
        suffix = " 검토" if detection.needs_review else ""
        text = f"{label} {detection.confidence:.2f}{suffix}"

        draw.rectangle((x1, y1, x2, y2), outline=color, width=line_width)
        left, top, right, bottom = draw.textbbox((x1, y1), text, font=font)
        text_height = bottom - top
        text_width = right - left
        text_box_width = text_width + padding_x * 2
        text_box_height = text_height + padding_y * 2
        text_x = max(0, min(x1, image.width - text_box_width))
        text_y = y1 - text_box_height - line_width

        if text_y < 0:
            text_y = min(image.height - text_box_height, y1 + line_width)

        label_box = (
            text_x,
            text_y,
            text_x + text_box_width,
            text_y + text_box_height,
        )
        while any(_overlaps(label_box, placed) for placed in placed_labels):
            next_y = label_box[3] + line_width
            if next_y + text_box_height > image.height:
                break
            label_box = (
                label_box[0],
                next_y,
                label_box[2],
                next_y + text_box_height,
            )

        draw.rounded_rectangle(
            label_box,
            radius=max(6, line_width),
            fill=color,
        )
        draw.text(
            (label_box[0] + padding_x, label_box[1] + padding_y),
            text,
            fill=(255, 255, 255),
            font=font,
        )
        placed_labels.append(label_box)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    annotated.save(output_path)


def _overlaps(
    first: tuple[float, float, float, float],
    second: tuple[float, float, float, float],
) -> bool:
    return not (
        first[2] < second[0]
        or first[0] > second[2]
        or first[3] < second[1]
        or first[1] > second[3]
    )
