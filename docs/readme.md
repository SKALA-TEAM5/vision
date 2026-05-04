# Vision AI Workspace

사진 입력을 받아 적정성 여부를 판단하고, 결과를 JSON으로 반환하는 Vision AI 전용 작업 공간입니다.

## 범위

이 레포에서 다루는 것:

- Vision AI agent
- 이미지 전처리 및 후처리
- 적정성 판단 로직
- JSON 출력 스키마
- 샘플 이미지 및 실험 예제

## 입력 / 출력

입력:

- 사진 파일 1장 또는 여러 장

출력:

- 적정성 판단 결과 JSON

예시:

```json
{
  "is_appropriate": true,
  "confidence": 0.92,
  "reason": "안전모가 정상 착용 상태로 확인됨"
}
```

## 디렉토리 원칙

모든 구현 코드는 `src/` 아래에 둡니다.
루트에는 프로젝트 설정 파일과 공통 문서만 둡니다.

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
