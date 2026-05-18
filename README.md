# Vision AI Workspace

사진 입력을 받아 보호구 착용 상태와 안전망 설치 상태를 판단하고 JSON으로 반환하는 FastAPI 서비스입니다.

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

기본 모델 경로는 아래와 같습니다.

- `vision/models/ppe-detector.pt`: 안전모, 안전화, 안전벨트 bbox detector
- `vision/models/safety-net-classifier.pt`: 안전망 설치 여부 classifier

```env
HOST_VISION_MODEL_PATH=./vision/models/ppe-detector.pt
HOST_SAFETY_NET_MODEL_PATH=./vision/models/safety-net-classifier.pt
VISION_MODEL_NAME=ppe-detector
SAFETY_NET_MODEL_NAME=safety-net-classifier
VISION_MODEL_CONF=0.35
VISION_MODEL_IOU=0.45
VISION_MODEL_DEVICE=auto
VISION_REVIEW_CONF=0.50
SAFETY_NET_REVIEW_CONF=0.70
```

```bash
make vision-venv
make vision-review
```

`make vision-review`는 `volumes/files` 아래 이미지를 읽고 `volumes/vision_results`에 파일별 JSON과 `summary.json`을 저장합니다.
박스가 그려진 이미지는 `volumes/vision_results/annotated` 아래에 저장됩니다.

결과 JSON은 프론트에서 그대로 상태 표시와 메시지, 박스 렌더링에 사용할 수 있습니다.
운영 API는 점검 항목에 따라 보호구 모델과 안전망 모델을 따로 실행합니다.

- PPE detector: 안전모, 안전화, 안전벨트 착용/미착용 bbox
- Safety-net classifier: `installed`, `missing`, 또는 confidence 낮을 때 코드에서 합성한 `unclear`

```json
{
  "overall_status": "not_appropriate",
  "is_appropriate": false,
  "message": "안전모 항목이 부적정으로 판단되었습니다.",
  "ppe_status": "not_appropriate",
  "ppe_is_appropriate": false,
  "ppe_message": "안전모 항목이 부적정으로 판단되었습니다.",
  "safety_net_review": {
    "model_name": "safety-net-classifier",
    "status": "unclear",
    "is_appropriate": null,
    "confidence": 0.54,
    "raw_label": "installed",
    "reason": "이 사진에서는 안전망 설치 여부를 판단하기 어렵습니다."
  },
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

주의: `safety-net-classifier.pt` 자체 클래스는 `installed`, `missing`만 있고 `unclear` 클래스는 없습니다. 지금은 `SAFETY_NET_REVIEW_CONF`보다 confidence가 낮으면 `unclear`로 처리합니다. 운영 품질을 높이려면 안전망 classifier에 `unclear` 또는 `not_applicable` 데이터를 추가해 재학습하는 편이 좋습니다.

컨테이너로 API를 띄울 때는 아래 명령을 사용합니다.

```bash
make vision-up
```

## API

- `GET /health`: 서버와 모델 파일 존재 여부 확인
- `GET /labels`: 현재 클래스 코드 확인
- `POST /detect/ppe/source`: 원본 이미지 주소로 보호구 모델만 실행
- `POST /detect/safety-net/source`: 원본 이미지 주소로 안전망 모델만 실행
- `POST /detect/ppe`: 이미지 파일 multipart 업로드 후 보호구 모델만 실행
- `POST /detect/safety-net`: 이미지 파일 multipart 업로드 후 안전망 모델만 실행
- `POST /detect/source`: 보호구와 안전망 모델을 모두 실행하는 호환용 API
- `POST /detect`: 보호구와 안전망 모델을 모두 실행하는 개발 확인용 업로드 API

```bash
curl -X POST http://localhost:8002/detect/ppe/source \
  -H "Content-Type: application/json" \
  -d '{"source_id":"image_12345","source_uri":"/data/files/ppe-photo-001.jpg"}'

curl -X POST http://localhost:8002/detect/safety-net/source \
  -H "Content-Type: application/json" \
  -d '{"source_id":"image_67890","source_uri":"/data/files/safety-net-photo-001.jpg"}'
```

GPU 서버에서 컨테이너를 띄울 때는 `VISION_MODEL_DEVICE=0`으로 지정하고 compose 서비스에 GPU 옵션을 추가합니다.

```yaml
services:
  vision:
    gpus: all
```
