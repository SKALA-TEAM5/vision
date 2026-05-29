# Vision AI Workspace

사진 입력을 받아 적정성 여부를 판단하고, 결과를 JSON으로 반환하는 Vision AI 전용 작업 공간입니다.

## 범위

이 레포에서 다루는 것:

- Vision AI agent
- 이미지 전처리 및 후처리
- 적정성 판단 로직
- JSON 출력 스키마
- 샘플 이미지 및 실험 예제
- BentoML 기반 모델 서빙 설정
- uv 기반 Python 의존성 관리

현재 모델:

- `models/ppe-detector.pt`: 안전모, 안전화, 안전벨트 착용/미착용 bbox detector
- `models/safety-net-classifier.pt`: 안전망 설치 여부 classifier

## 입력 / 출력

입력:

- 보호구 점검 사진 파일 또는 파일 주소
- 안전망 점검 사진 파일 또는 파일 주소

출력:

- 적정성 판단 결과 JSON
- bbox 또는 상태 배너가 그려진 결과 이미지 경로/URL

예시:

```json
{
  "overall_status": "needs_review",
  "is_appropriate": null,
  "message": "안전화 항목은 검토가 필요합니다.",
  "ppe_status": "needs_review",
  "safety_net_review": {
    "status": "unclear",
    "is_appropriate": null,
    "confidence": 0.54,
    "reason": "이 사진에서는 안전망 설치 여부를 판단하기 어렵습니다."
  }
}
```

운영 API에서는 사진 업로드 시 선택된 점검 항목에 따라 모델을 따로 실행합니다.

- 보호구 점검: `POST /detect/ppe/source`
- 안전망 점검: `POST /detect/safety-net/source`

컨테이너 실행 기준으로 입력 이미지 디렉토리는 `/data/files`, 결과 이미지 디렉토리는 `/data/vision_results`입니다.
보호구 결과 이미지는 `/data/vision_results/annotated/ppe`, 안전망 결과 이미지는 `/data/vision_results/annotated/safety-net` 아래에 따로 저장됩니다.
백엔드는 DB에서 가져온 파일 위치를 `source_uri`로 전달합니다.

```json
{
  "source_id": "image_12345",
  "source_uri": "/data/files/raw_image_022__0009.jpg"
}
```

백엔드는 Vision API 응답의 `annotated_image_path` 또는 `annotated_image_url`을 로그 테이블에 저장합니다.
프론트는 DB에 저장된 결과 이미지 URL을 그대로 표시할 수 있습니다.

안전망 classifier는 현재 `installed`, `missing`만 학습되어 있으므로 confidence가 낮은 경우 코드에서 `unclear`로 처리합니다.

## 디렉토리 원칙

모든 구현 코드는 `src/` 아래에 둡니다.
루트에는 프로젝트 설정 파일, BentoML entrypoint(`service.py`), 공통 문서만 둡니다.

권장 구조:

```text
src/
  agents/
    vision_review_agent/
  vision/
  prompts/
  schemas/
  services/
  repositories/
  core/
examples/
tests/
docs/
service.py
bentofile.yaml
pyproject.toml
uv.lock
```

## 폴더 설명

- `src/agents/`: 에이전트별 실행 로직
- `src/vision/`: 이미지 전처리, crop, 후처리
- `src/prompts/`: 비전 모델 프롬프트 (있으면)
- `src/schemas/`: 입력/출력 JSON 스키마
- `src/services/`: 모델 호출, 검증, 후처리
- `src/repositories/`: DB/스토리지 접근
- `src/core/`: 공통 설정, 상수, 유틸
- `examples/`: 샘플 이미지와 기대 결과
- `tests/`: 자동화 테스트
- `docs/`: 설계 및 작업 문서

## 파일 규칙

- 에이전트 실행 파일은 `main.py`로 통일합니다.
- Python 파일과 디렉토리는 소문자 + 스네이크 케이스를 사용합니다.
- 서비스 파일은 `*_service.py`
- 저장소 파일은 `*_repository.py`
- 테스트 파일은 `test_*.py`
- 예제 JSON은 `sample_*.json`, `expected_*.json`

예시:

```text
src/agents/vision_review_agent/
  __init__.py
  main.py
  config.py
```

## 작업 규칙

- 새 기능 디렉토리를 루트에 직접 만들지 않습니다.
- 새 에이전트는 `src/agents/<agent_name>/` 아래에 추가합니다.
- 이미지 처리 코드는 `src/vision/` 아래에 둡니다.
- 프롬프트 파일은 `src/prompts/` 또는 에이전트 내부에 둡니다.
- 샘플 데이터는 `examples/` 아래에 둡니다.
- 개인 실험 파일, 임시 파일, 로컬 산출물은 커밋하지 않습니다.

## 브랜치 규칙

- 기능 개발: `feature/<name>`
- 버그 수정: `fix/<name>`
- 긴급 수정: `hotfix/<name>`

PR 대상은 기본적으로 `main`입니다.

## 개발 환경

- Python: 3.11.9
- 패키지 관리: `uv`

설치:

```bash
uv python install 3.11.9
uv sync
```
