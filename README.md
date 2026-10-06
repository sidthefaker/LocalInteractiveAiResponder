# 로컬 LLM 채팅

로컬에서 실행되는 LLM과 대화하고, 대화 내용을 SQLite에 저장하는 웹 앱입니다. FastAPI와 서버 렌더링을 중심으로 구성해 프론트엔드와 백엔드를 한 프로젝트에서 관리합니다.

## 기술 구성

- **FastAPI**: 웹 서버와 요청 처리
- **Jinja2**: HTML 페이지와 화면 조각 렌더링
- **HTMX**: 페이지 전체를 새로고침하지 않고 메시지를 보내고 대화 화면 갱신
- **SQLite**: 대화와 메시지 저장
- **HTTPX**: 통합 테스트용 HTTP 클라이언트 (추후 응답 제공자에서 로컬 LLM 호출에 사용)
- **uv**: Python 패키지 및 가상환경 관리
- **mise**: Python 등 개발 도구 버전 관리
- **Uvicorn**: FastAPI 개발 서버 실행

화면은 Jinja2 서버 렌더링과 HTMX로 구성합니다. `/chat` 경로에서 별도 응답 제공자 함수에 메시지를 전달합니다. 현재 제공자는 입력을 그대로 돌려주는 테스트용 에코이며, 반환된 응답을 SSE로 다섯 번 나누어 전송해 화면 갱신 흐름을 확인합니다. 나중에 이 함수의 구현을 로컬 LLM 호출로 교체합니다.

## 주요 흐름

1. 사용자가 채팅 화면에서 메시지를 전송합니다.
2. HTMX가 메시지를 서버에 비동기 전송합니다.
3. 채팅 경로가 `response_provider.request_response()`를 호출합니다.
4. 테스트 제공자가 입력을 반환하고, FastAPI가 이를 SSE 이벤트 다섯 개로 나누어 전송합니다.
5. HTMX가 각 조각을 대화창에 순차적으로 추가합니다.

## 실행

```sh
uv sync
uv run localinteractiveairesponder
```

브라우저에서 `http://127.0.0.1:8000`을 열어 테스트용 응답 흐름을 확인합니다.

## 테스트와 coverage

통합 테스트는 `uv run pytest tests/integration`으로 실행합니다. Unit test coverage는 `uv run pytest tests/unit --cov=localinteractiveairesponder --cov-report=term-missing --cov-fail-under=80`으로 확인합니다. Coverage는 `tests/unit`만 대상으로 하므로 통합 테스트는 계산에서 제외됩니다. PR에서 unit test coverage가 80% 미만이면 필수 GitHub 체크가 실패합니다.

## 개발 방향

- 로컬 LLM 런타임(Ollama 등)은 교체할 수 있도록 호출 코드를 분리합니다.
- 대화와 메시지는 별도로 저장하고, 생성 시각과 모델 이름을 기록합니다.
- DB 모델링에는 SQLAlchemy 또는 SQLModel을 검토하고, 스키마 변경이 생기면 Alembic을 도입합니다.
- 코드 품질과 검증에는 Ruff, pytest, HTTPX를 사용합니다. 브라우저 흐름 검증이 필요해지면 Playwright를 추가합니다.

## 작업 시 역할과 주의사항

### 사람

- PR에 포함된 코드와 설계 변경을 꼼꼼히 리뷰합니다.
- 변경된 로직을 이해하고 설명할 수 있도록, 필요하면 해당 로직의 unit test를 직접 작성합니다.
