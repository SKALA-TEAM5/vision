# Vision AI Workspace

사진 입력을 받아 보호구 착용 상태와 안전망 설치 상태를 판단하고 JSON으로 반환하는 BentoML 기반 Vision API 서비스입니다.
기존 FastAPI 앱은 BentoML Service에 ASGI 앱으로 mount되어 있어 API 경로와 Swagger 문서는 그대로 유지됩니다.

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
service.py
bentofile.yaml
pyproject.toml
uv.lock
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

의존성은 `pyproject.toml`과 `uv.lock` 기준으로 설치합니다.

```bash
make vision-venv
make vision-review
```

`make vision-review`는 `volumes/files` 아래 이미지를 읽고 `volumes/vision_results`에 파일별 JSON과 `summary.json`을 저장합니다.
박스가 그려진 이미지는 `volumes/vision_results/annotated` 아래에 저장됩니다.

결과 JSON에는 판정 상태, 메시지, 결과 이미지 경로가 포함됩니다.
운영 API는 점검 항목에 따라 보호구 모델과 안전망 모델을 따로 실행하고, 각각 결과 이미지를 생성합니다.

- PPE detector: 안전모, 안전화, 안전벨트 착용/미착용 bbox
- Safety-net classifier: `installed`, `missing`, 또는 confidence 낮을 때 코드에서 합성한 `unclear`
- 보호구 결과 이미지: bbox와 라벨이 그려진 이미지
- 안전망 결과 이미지: 설치/미설치/판단 어려움 배너가 그려진 이미지

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
  "annotated_image_path": "volumes/vision_results/annotated/ppe/sample.annotated.jpg",
  "annotated_image_url": "/vision-results/annotated/ppe/sample.annotated.jpg",
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

`make vision-up`은 Dockerfile을 사용해 BentoML 서버를 실행합니다.
Dockerfile도 `uv sync --frozen`으로 `uv.lock`에 고정된 의존성을 설치합니다.
FastAPI 문서는 그대로 아래 URL에서 확인할 수 있습니다.

```text
http://localhost:8002/docs
```

BentoML 표준 패키징이 필요하면 아래 명령을 사용합니다.

```bash
make vision-bento-build
make vision-bento-containerize
```

컨테이너 실행 시 입력 이미지는 host의 `volumes/files`가 컨테이너의 `/data/files`로 mount됩니다.
백엔드가 DB에서 파일 위치를 가져와 Vision API에 전달할 때는 컨테이너에서 접근 가능한 경로를 사용합니다.

```json
{
  "source_id": "image_12345",
  "source_uri": "/data/files/raw_image_022__0009.jpg"
}
```

`source_uri`가 `raw_image_022__0009.jpg`처럼 파일명만 들어오거나 `volumes/files/raw_image_022__0009.jpg`처럼 상대 경로로 들어오는 경우에도, Vision API는 `VISION_INPUT_DIR` 아래에서 같은 파일명을 한 번 더 찾아봅니다.

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

백엔드는 응답의 `annotated_image_path` 또는 `annotated_image_url`을 DB 로그 테이블에 저장하고, 프론트는 해당 결과 이미지를 그대로 표시할 수 있습니다.

GPU 서버에서 컨테이너를 띄울 때는 `VISION_MODEL_DEVICE=0`으로 지정하고 compose 서비스에 GPU 옵션을 추가합니다.

```yaml
services:
  vision:
    gpus: all
```
