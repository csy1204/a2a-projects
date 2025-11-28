"""A2A Agent Tester - Streamlit Frontend."""

import json
import uuid

import httpx
import streamlit as st

st.set_page_config(
    page_title="A2A Agent Tester",
    page_icon="🤖",
    layout="wide",
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "context_id" not in st.session_state:
    st.session_state.context_id = str(uuid.uuid4())
if "task_id" not in st.session_state:
    st.session_state.task_id = None
if "agent_card" not in st.session_state:
    st.session_state.agent_card = None
if "connected" not in st.session_state:
    st.session_state.connected = False
if "task_history" not in st.session_state:
    st.session_state.task_history = []
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "chat_task_id" not in st.session_state:
    st.session_state.chat_task_id = None
if "chat_state" not in st.session_state:
    st.session_state.chat_state = "idle"  # idle, working, input_required, completed


def fetch_agent_card(url: str) -> dict | None:
    """Fetch agent card from the A2A server."""
    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(f"{url}/.well-known/agent-card.json")
            if response.status_code == 404:
                response = client.get(f"{url}/.well-known/agent.json")
            response.raise_for_status()
            return response.json()
    except Exception as e:
        st.error(f"Failed to fetch agent card: {e}")
        return None


def send_message_sync(url: str, message: str, context_id: str) -> dict:
    """Send a message using message/send (synchronous)."""
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/send",
        "params": {
            "message": {
                "messageId": str(uuid.uuid4()),
                "role": "user",
                "parts": [{"kind": "text", "text": message}],
                "contextId": context_id,
            },
            "configuration": {
                "acceptedOutputModes": ["text", "text/plain"],
            },
        },
    }

    try:
        with httpx.Client(timeout=120) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            return {"success": True, "data": response.json(), "raw_request": payload}
    except Exception as e:
        return {"success": False, "error": str(e), "raw_request": payload}


def send_message_stream(url: str, message: str, context_id: str):
    """Send a message using message/stream (SSE streaming)."""
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/stream",
        "params": {
            "message": {
                "messageId": str(uuid.uuid4()),
                "role": "user",
                "parts": [{"kind": "text", "text": message}],
                "contextId": context_id,
            },
            "configuration": {
                "acceptedOutputModes": ["text", "text/plain"],
            },
        },
    }

    events = []
    try:
        with httpx.Client(timeout=120) as client:
            with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line.startswith("data: "):
                        try:
                            event_data = json.loads(line[6:])
                            events.append(event_data)
                            yield {"type": "event", "data": event_data}
                        except json.JSONDecodeError:
                            pass
        yield {"type": "complete", "events": events, "raw_request": payload}
    except Exception as e:
        yield {"type": "error", "error": str(e), "raw_request": payload}


def get_task(url: str, task_id: str) -> dict:
    """Get task status using tasks/get."""
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "tasks/get",
        "params": {
            "id": task_id,
        },
    }

    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            return {"success": True, "data": response.json(), "raw_request": payload}
    except Exception as e:
        return {"success": False, "error": str(e), "raw_request": payload}


def set_push_notification_config(url: str, task_id: str, webhook_url: str) -> dict:
    """Set push notification config for a task."""
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "tasks/pushNotificationConfig/set",
        "params": {
            "id": task_id,
            "pushNotificationConfig": {
                "url": webhook_url,
            },
        },
    }

    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            return {"success": True, "data": response.json(), "raw_request": payload}
    except Exception as e:
        return {"success": False, "error": str(e), "raw_request": payload}


def get_push_notification_config(url: str, task_id: str) -> dict:
    """Get push notification config for a task."""
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "tasks/pushNotificationConfig/get",
        "params": {
            "id": task_id,
        },
    }

    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            return {"success": True, "data": response.json(), "raw_request": payload}
    except Exception as e:
        return {"success": False, "error": str(e), "raw_request": payload}


def extract_text_from_parts(parts: list) -> str:
    """Extract text from A2A message parts."""
    if not parts:
        return ""
    texts = []
    for part in parts:
        if isinstance(part, dict):
            # Handle both "kind" and "type" for compatibility
            if part.get("kind") == "text" or part.get("type") == "text":
                texts.append(part.get("text", ""))
            # Handle nested root structure
            elif "root" in part:
                root = part["root"]
                if isinstance(root, dict) and (root.get("kind") == "text" or root.get("type") == "text"):
                    texts.append(root.get("text", ""))
    return "\n".join(texts)


def extract_text_from_result(obj: dict) -> str:
    """Extract text from various A2A result structures."""
    if not obj:
        return ""

    # Direct text field
    if "text" in obj:
        return obj["text"]

    # Parts array
    if "parts" in obj:
        return extract_text_from_parts(obj["parts"])

    # Nested message structure
    if "message" in obj:
        return extract_text_from_result(obj["message"])

    # Root wrapper (Pydantic model serialization)
    if "root" in obj:
        return extract_text_from_result(obj["root"])

    return ""


def extract_task_info(result: dict) -> dict | None:
    """Extract task information from response."""
    if not result:
        return None

    task_id = result.get("id")
    context_id = result.get("contextId")
    status = result.get("status", {})

    return {
        "id": task_id,
        "contextId": context_id,
        "state": status.get("state"),
        "message": status.get("message"),
        "artifacts": result.get("artifacts", []),
    }


# Sidebar - Connection
with st.sidebar:
    st.title("🤖 A2A Agent Tester")
    st.divider()

    agent_url = st.text_input(
        "Agent URL",
        value="http://localhost:10000",
        placeholder="http://localhost:10000",
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Connect", use_container_width=True):
            card = fetch_agent_card(agent_url)
            if card:
                st.session_state.agent_card = card
                st.session_state.connected = True
                st.session_state.messages = []
                st.session_state.context_id = str(uuid.uuid4())
                st.session_state.task_id = None
                st.session_state.task_history = []
                st.rerun()

    with col2:
        if st.button("Disconnect", use_container_width=True):
            st.session_state.agent_card = None
            st.session_state.connected = False
            st.session_state.messages = []
            st.session_state.task_id = None
            st.session_state.task_history = []
            st.rerun()

    if st.session_state.connected:
        st.success("✅ Connected")
    else:
        st.warning("⚠️ Disconnected")

    st.divider()

    if st.session_state.agent_card:
        card = st.session_state.agent_card
        st.subheader("Agent Info")
        st.write(f"**Name:** {card.get('name', '-')}")
        st.write(f"**Version:** {card.get('version', '-')}")

        capabilities = card.get("capabilities", {})
        st.write(f"**Streaming:** {'✅' if capabilities.get('streaming') else '❌'}")
        st.write(f"**Push:** {'✅' if capabilities.get('pushNotifications') else '❌'}")

        with st.expander("📄 Full Agent Card"):
            st.json(card)

    if st.session_state.task_history:
        st.divider()
        st.subheader("Task History")
        for i, task in enumerate(reversed(st.session_state.task_history[-5:])):
            with st.expander(f"📋 Task {i+1} ({task['state']})"):
                st.code(task['id'], language=None)
                st.caption(f"State: {task['state']}")


# Main content
st.title("A2A Protocol Tester")

if not st.session_state.connected:
    st.info("👈 Connect to an agent using the sidebar to start testing.")
else:
    tab_chat, tab1, tab2, tab3, tab4 = st.tabs([
        "💬 Chat Mode",
        "1️⃣ message/send (Sync)",
        "2️⃣ message/stream (SSE)",
        "3️⃣ tasks/get (Query)",
        "4️⃣ Push Notifications",
    ])

    # Tab Chat: Interactive Chat Mode
    with tab_chat:
        st.header("💬 Interactive Chat Mode")
        st.markdown("""
        스트리밍으로 대화하며 중간 상태를 실시간으로 확인합니다.
        - `working`: 처리 중 상태 표시
        - `input_required`: 추가 입력 요청 시 대화 계속
        - `completed`: 최종 결과 표시
        """)

        # Chat controls
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("🔄 New Chat", key="new_chat"):
                st.session_state.chat_messages = []
                st.session_state.chat_task_id = None
                st.session_state.chat_state = "idle"
                st.session_state.context_id = str(uuid.uuid4())
                st.rerun()
        with col2:
            state_colors = {
                "idle": "🔵",
                "working": "🟡",
                "input_required": "🟠",
                "completed": "🟢",
                "failed": "🔴",
            }
            st.markdown(f"**State:** {state_colors.get(st.session_state.chat_state, '⚪')} `{st.session_state.chat_state}`")

        st.divider()

        # Chat messages container
        chat_container = st.container(height=400)
        with chat_container:
            for msg in st.session_state.chat_messages:
                with st.chat_message(msg["role"]):
                    if msg.get("type") == "status":
                        st.info(f"⏳ {msg['content']}")
                    elif msg.get("type") == "error":
                        st.error(msg["content"])
                    else:
                        st.markdown(msg["content"])

        # Chat input
        chat_disabled = st.session_state.chat_state == "working"

        if prompt := st.chat_input(
            "메시지를 입력하세요..." if st.session_state.chat_state != "input_required" else "추가 정보를 입력하세요...",
            key="chat_input",
            disabled=chat_disabled,
        ):
            # Add user message
            st.session_state.chat_messages.append({
                "role": "user",
                "content": prompt,
            })
            st.session_state.chat_state = "working"

            # Process with streaming
            status_messages = []
            final_response = None
            final_state = "completed"
            debug_events = []

            for item in send_message_stream(agent_url, prompt, st.session_state.context_id):
                if item["type"] == "event":
                    data = item["data"]
                    debug_events.append(data)

                    if "result" in data:
                        result = data["result"]

                        # Update task ID
                        if result.get("id"):
                            st.session_state.chat_task_id = result["id"]
                            st.session_state.task_id = result["id"]

                        # Handle status
                        if "status" in result:
                            status = result["status"]
                            state = status.get("state", "")

                            # Extract text from message
                            msg = status.get("message", {})
                            text = extract_text_from_result(msg)

                            if state == "working":
                                if text:
                                    status_messages.append(text)

                            elif state == "input_required":
                                final_state = "input_required"
                                if text:
                                    final_response = text

                            elif state == "completed":
                                final_state = "completed"
                                if text:
                                    final_response = text

                            elif state == "failed":
                                final_state = "failed"
                                if text:
                                    final_response = text

                        # Handle artifacts
                        if "artifact" in result:
                            artifact = result["artifact"]
                            text = extract_text_from_result(artifact)
                            if text:
                                final_response = text
                            final_state = "completed"

                elif item["type"] == "error":
                    final_response = f"Error: {item['error']}"
                    final_state = "failed"

            # Add status messages as assistant messages
            if status_messages:
                for status_msg in status_messages:
                    st.session_state.chat_messages.append({
                        "role": "assistant",
                        "type": "status",
                        "content": status_msg,
                    })

            # Add final response
            if final_response:
                msg_type = "error" if final_state == "failed" else None
                st.session_state.chat_messages.append({
                    "role": "assistant",
                    "content": final_response,
                    "type": msg_type,
                })

            # If no response was extracted, show debug info
            if not final_response and not status_messages and debug_events:
                st.session_state.chat_messages.append({
                    "role": "assistant",
                    "type": "error",
                    "content": f"No text extracted. Raw events: {json.dumps(debug_events, indent=2, default=str)[:1000]}",
                })

            # Update state
            st.session_state.chat_state = final_state

            # Save to task history
            if st.session_state.chat_task_id:
                task_info = {
                    "id": st.session_state.chat_task_id,
                    "state": final_state,
                    "contextId": st.session_state.context_id,
                }
                if task_info not in st.session_state.task_history:
                    st.session_state.task_history.append(task_info)

            st.rerun()

        # Show current task info
        if st.session_state.chat_task_id:
            with st.expander("📋 Current Task Info"):
                st.markdown("**Task ID:**")
                st.code(st.session_state.chat_task_id, language=None)
                st.markdown("**Context ID:**")
                st.code(st.session_state.context_id, language=None)

    # Tab 1: message/send (Synchronous)
    with tab1:
        st.header("message/send - Synchronous Request")
        st.markdown("""
        동기 요청으로 메시지를 보내고 완료된 응답을 받습니다.
        - 요청 후 전체 처리가 끝날 때까지 대기
        - Task 또는 Message 객체 반환
        """)

        sync_message = st.text_input("Message", key="sync_msg", placeholder="What is the weather in Seoul?")

        if st.button("Send (Sync)", key="sync_send", type="primary"):
            if sync_message:
                with st.spinner("Waiting for response..."):
                    result = send_message_sync(agent_url, sync_message, st.session_state.context_id)

                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("📤 Request")
                    st.json(result["raw_request"])

                with col2:
                    st.subheader("📥 Response")
                    if result["success"]:
                        st.json(result["data"])

                        # Extract task info
                        if "result" in result["data"]:
                            task_info = extract_task_info(result["data"]["result"])
                            if task_info and task_info["id"]:
                                st.session_state.task_id = task_info["id"]
                                st.session_state.task_history.append(task_info)
                                st.success(f"State: `{task_info['state']}`")
                                st.markdown("**Task ID (click to copy):**")
                                st.code(task_info['id'], language=None)
                    else:
                        st.error(f"Error: {result['error']}")

    # Tab 2: message/stream (SSE Streaming)
    with tab2:
        st.header("message/stream - SSE Streaming")
        st.markdown("""
        Server-Sent Events (SSE) 스트리밍으로 실시간 응답을 받습니다.
        - 중간 상태 업데이트 (working, input_required 등)
        - Artifact 생성 이벤트
        - 실시간 진행 상황 확인
        """)

        stream_message = st.text_input("Message", key="stream_msg", placeholder="Give me a 5-day forecast for Tokyo")

        if st.button("Send (Stream)", key="stream_send", type="primary"):
            if stream_message:
                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("📤 Request")
                    request_placeholder = st.empty()

                with col2:
                    st.subheader("📥 SSE Events")
                    events_container = st.container()

                all_events = []
                raw_request = None

                for item in send_message_stream(agent_url, stream_message, st.session_state.context_id):
                    if item["type"] == "event":
                        all_events.append(item["data"])
                        with events_container:
                            st.markdown(f"**Event {len(all_events)}:**")
                            st.json(item["data"])

                            # Extract task info from events
                            if "result" in item["data"]:
                                task_info = extract_task_info(item["data"]["result"])
                                if task_info and task_info["id"]:
                                    st.session_state.task_id = task_info["id"]
                                    if task_info not in st.session_state.task_history:
                                        st.session_state.task_history.append(task_info)
                            st.divider()

                    elif item["type"] == "complete":
                        raw_request = item["raw_request"]
                        with col1:
                            request_placeholder.json(raw_request)
                        st.success(f"✅ Streaming complete! Received {len(all_events)} events.")

                    elif item["type"] == "error":
                        raw_request = item.get("raw_request")
                        if raw_request:
                            with col1:
                                request_placeholder.json(raw_request)
                        st.error(f"Error: {item['error']}")

    # Tab 3: tasks/get (Query Task)
    with tab3:
        st.header("tasks/get - Query Task Status")
        st.markdown("""
        TaskStore에서 태스크 상태를 조회합니다.
        - 이전에 생성된 태스크 ID로 조회
        - 태스크 상태, 아티팩트, 메시지 확인
        """)

        # Task ID input with last task ID as default
        default_task_id = st.session_state.task_id or ""
        task_id_input = st.text_input(
            "Task ID",
            value=default_task_id,
            key="task_id_input",
            placeholder="Enter task ID or use the last created task",
        )

        if st.session_state.task_history:
            st.markdown("**Recent Tasks (click to select):**")
            for i, task in enumerate(reversed(st.session_state.task_history[-5:])):
                col_btn, col_id = st.columns([1, 4])
                with col_btn:
                    if st.button(f"Select", key=f"task_select_{i}"):
                        st.session_state.selected_task_id = task["id"]
                        st.rerun()
                with col_id:
                    st.code(task['id'], language=None)
                    st.caption(f"State: {task['state']}")

        # Use selected task if available
        if "selected_task_id" in st.session_state:
            task_id_input = st.session_state.pop("selected_task_id")

        if st.button("Get Task", key="get_task", type="primary"):
            if task_id_input:
                with st.spinner("Fetching task..."):
                    result = get_task(agent_url, task_id_input)

                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("📤 Request")
                    st.json(result["raw_request"])

                with col2:
                    st.subheader("📥 Response")
                    if result["success"]:
                        st.json(result["data"])

                        if "result" in result["data"]:
                            task_data = result["data"]["result"]
                            st.success(f"State: `{task_data.get('status', {}).get('state', 'unknown')}`")
                        elif "error" in result["data"]:
                            st.warning(f"Task not found or error: {result['data']['error']}")
                    else:
                        st.error(f"Error: {result['error']}")
            else:
                st.warning("Please enter a Task ID")

    # Tab 4: Push Notifications
    with tab4:
        st.header("Push Notifications - Webhook Configuration")
        st.markdown("""
        태스크 완료 시 webhook으로 알림을 받습니다.
        - Webhook URL 설정
        - 태스크 상태 변경 시 자동 호출
        - 비동기 처리에 유용
        """)

        st.subheader("1. Set Push Notification Config")

        push_task_id = st.text_input(
            "Task ID for Push Config",
            value=st.session_state.task_id or "",
            key="push_task_id",
        )

        webhook_url = st.text_input(
            "Webhook URL",
            placeholder="https://your-webhook.example.com/callback",
            key="webhook_url",
            help="URL that will receive POST requests when task status changes",
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Set Config", key="set_push", type="primary"):
                if push_task_id and webhook_url:
                    with st.spinner("Setting push notification config..."):
                        result = set_push_notification_config(agent_url, push_task_id, webhook_url)

                    st.subheader("📤 Request")
                    st.json(result["raw_request"])

                    st.subheader("📥 Response")
                    if result["success"]:
                        st.json(result["data"])
                        st.success("Push notification config set!")
                    else:
                        st.error(f"Error: {result['error']}")
                else:
                    st.warning("Please enter both Task ID and Webhook URL")

        with col2:
            if st.button("Get Config", key="get_push"):
                if push_task_id:
                    with st.spinner("Getting push notification config..."):
                        result = get_push_notification_config(agent_url, push_task_id)

                    st.subheader("📤 Request")
                    st.json(result["raw_request"])

                    st.subheader("📥 Response")
                    if result["success"]:
                        st.json(result["data"])
                    else:
                        st.error(f"Error: {result['error']}")
                else:
                    st.warning("Please enter Task ID")

        st.divider()

        st.subheader("2. Test Webhook (Local)")
        st.markdown("""
        로컬에서 webhook을 테스트하려면 별도의 서버가 필요합니다.

        **예시: 간단한 webhook 수신 서버**
        ```python
        # webhook_receiver.py
        from fastapi import FastAPI, Request
        import uvicorn

        app = FastAPI()

        @app.post("/callback")
        async def receive_webhook(request: Request):
            data = await request.json()
            print(f"Received webhook: {data}")
            return {"status": "received"}

        if __name__ == "__main__":
            uvicorn.run(app, host="0.0.0.0", port=8888)
        ```

        실행 후 Webhook URL에 `http://localhost:8888/callback` 입력
        """)

    # Footer with context info
    st.divider()
    col1, col2 = st.columns([4, 1])
    with col1:
        with st.expander("📋 Session Info (click to copy IDs)"):
            st.markdown("**Context ID:**")
            st.code(st.session_state.context_id, language=None)
            st.markdown("**Last Task ID:**")
            st.code(st.session_state.task_id or "None", language=None)
    with col2:
        if st.button("🔄 New Context", key="new_context"):
            st.session_state.context_id = str(uuid.uuid4())
            st.session_state.task_id = None
            st.session_state.messages = []
            st.rerun()
