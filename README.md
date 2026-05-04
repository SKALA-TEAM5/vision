# Vision AI Workspace

사진 입력을 받아 현재 학습된 YOLO 체크포인트로 객체를 탐지하고 JSON으로 반환하는 FastAPI 서비스입니다.

구현 코드는 모두 `src/` 아래에 둡니다.

```text
src/
  agents/
    vision_review_agent/
      main.py
  core/
    config.py
  schemas/
    vision.py
  services/
    vision_detection_service.py
  vision/
    image_loader.py
  main.py
```

## Run

기본 모델 경로는 `vision/models/best.pt`입니다.

```env
HOST_VISION_MODEL_PATH=./vision/models/best.pt
VISION_MODEL_NAME=yolo11s-0504
VISION_MODEL_CONF=0.35
VISION_MODEL_IOU=0.45
VISION_MODEL_DEVICE=auto
```

```bash
make vision-venv
make vision-review
```

`make vision-review`는 `volumes/files` 아래 이미지를 읽고 `volumes/vision_results`에 파일별 JSON과 `summary.json`을 저장합니다.
박스가 그려진 이미지는 `volumes/vision_results/annotated` 아래에 저장됩니다.

결과 JSON은 프론트에서 그대로 상태 표시와 메시지, 박스 렌더링에 사용할 수 있습니다.

```json
{
  "overall_status": "not_appropriate",
  "is_appropriate": false,
  "message": "안전모 항목이 부적정으로 판단되었습니다.",
  "annotated_image_path": "volumes/vision_results/annotated/sample.annotated.jpg",
  "annotated_image_url": "/vision-results/annotated/sample.annotated.jpg",
  "reviews": [
    {
      "equipment": "safety_helmet",
      "equipment_label": "안전모",
      "status": "not_wearing",
      "is_appropriate": false,
      "confidence": 0.91,
      "reason": "안전모 미착용 탐지 결과를 기준으로 판단했습니다."
    }
  ],
  "detections": [
    {
      "class_code": "08",
      "equipment": "safety_helmet",
      "label": "안전모 미착용",
      "is_wearing": false,
      "box_color": "red",
      "confidence": 0.91,
      "bbox_xyxy": [10.0, 20.0, 120.0, 220.0]
    }
  ]
}
```

컨테이너로 API를 띄울 때는 아래 명령을 사용합니다.

```bash
make vision-up
```

## API

- `GET /health`: 서버와 모델 파일 존재 여부 확인
- `GET /labels`: 현재 클래스 코드 확인
- `POST /detect`: 이미지 파일 multipart 업로드 후 bbox 결과 반환

```bash
curl -F "file=@sample.jpg" http://localhost:8002/detect
```

GPU 서버에서 컨테이너를 띄울 때는 `VISION_MODEL_DEVICE=0`으로 지정하고 compose 서비스에 GPU 옵션을 추가합니다.

```yaml
services:
  vision:
    gpus: all
```
