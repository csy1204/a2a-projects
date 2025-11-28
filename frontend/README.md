# A2A Agent Tester Frontend

A2A(Agent-to-Agent) 프로토콜 에이전트를 테스트하기 위한 Streamlit 웹 인터페이스입니다.

## 실행 방법

```bash
# 프로젝트 루트에서
uv run streamlit run frontend/app.py
```

브라우저에서 http://localhost:8501 자동 오픈

## 사용 방법

1. **Agent 연결**
   - Agent URL 입력 (예: `http://localhost:10000`)
   - "Connect" 버튼 클릭

2. **Agent Card 확인**
   - 연결 시 자동으로 Agent Card 정보 표시
   - Name, Version, Description, Skills 등 확인 가능

3. **채팅**
   - 메시지 입력 후 Send 또는 Enter
   - Skills 태그 클릭 시 예제 메시지 자동 입력

## A2A 프로토콜 엔드포인트

| 경로 | 메서드 | 설명 |
|------|--------|------|
| `/.well-known/agent.json` | GET | Agent Card 조회 |
| `/` | POST | JSON-RPC 메시지 전송 |

### Agent Card 직접 확인

```bash
curl http://localhost:10000/.well-known/agent.json
```

> **참고**: Agent Card는 `/agent-card.json`이 아닌 `/.well-known/agent.json` 경로에서 제공됩니다. 이는 A2A 프로토콜 표준을 따릅니다.

## Weather Agent 실행

```bash
# 프로젝트 루트에서
uv run python -m src.agents.weather_agent --host localhost --port 10000
```

### 필수 환경변수

```bash
# .env 파일에 설정
GOOGLE_API_KEY=your_google_api_key
OPENWEATHER_API_KEY=your_openweather_api_key
```

## 기능

- Agent Card 조회 및 표시
- 실시간 스트리밍 채팅 지원
- Task 상태 추적 (working, input_required, completed, failed)
- Skills 기반 예제 메시지
- 연결 상태 표시

## A2A JSON-RPC 요청 예시

```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "method": "tasks/sendSubscribe",
  "params": {
    "id": "task-id",
    "contextId": "context-id",
    "message": {
      "role": "user",
      "parts": [{ "type": "text", "text": "서울 날씨 알려줘" }]
    }
  }
}
```

## 트러블슈팅

### CORS 오류

Agent 서버와 프론트엔드가 다른 포트에서 실행될 경우 CORS 오류가 발생할 수 있습니다. A2A SDK의 `A2AStarletteApplication`은 기본적으로 CORS를 허용하므로 대부분의 경우 문제없이 동작합니다.

### 연결 실패

1. Agent 서버가 실행 중인지 확인
2. URL이 올바른지 확인 (포트 번호 포함)
3. `/.well-known/agent.json` 엔드포인트 직접 접속 테스트
