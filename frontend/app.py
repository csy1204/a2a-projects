"""A2A Agent Tester - Streamlit Frontend."""

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


def fetch_agent_card(url: str) -> dict | None:
    """Fetch agent card from the A2A server."""
    try:
        with httpx.Client(timeout=10) as client:
            # Try new endpoint first, fallback to deprecated
            response = client.get(f"{url}/.well-known/agent-card.json")
            if response.status_code == 404:
                response = client.get(f"{url}/.well-known/agent.json")
            response.raise_for_status()
            return response.json()
    except Exception as e:
        st.error(f"Failed to fetch agent card: {e}")
        return None


def send_message(url: str, message: str, context_id: str) -> dict:
    """Send a message to the A2A agent."""
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
        with httpx.Client(timeout=60) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        return {"error": {"message": str(e)}}


def send_message_streaming(url: str, message: str, context_id: str):
    """Send a message with streaming response."""
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

    try:
        with httpx.Client(timeout=60) as client:
            with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line.startswith("data: "):
                        yield line[6:]
    except Exception as e:
        yield f'{{"error": {{"message": "{e}"}}}}'


def extract_text_from_message(message: dict) -> str:
    """Extract text from A2A message parts."""
    if not message or "parts" not in message:
        return ""
    texts = []
    for part in message["parts"]:
        if part.get("kind") == "text":
            texts.append(part.get("text", ""))
    return "\n".join(texts)


def extract_text_from_artifact(artifact: dict) -> str:
    """Extract text from A2A artifact."""
    if not artifact or "parts" not in artifact:
        return ""
    texts = []
    for part in artifact["parts"]:
        if part.get("kind") == "text":
            texts.append(part.get("text", ""))
    return "\n".join(texts)


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
                st.rerun()

    with col2:
        if st.button("Disconnect", use_container_width=True):
            st.session_state.agent_card = None
            st.session_state.connected = False
            st.session_state.messages = []
            st.session_state.task_id = None
            st.rerun()

    # Connection status
    if st.session_state.connected:
        st.success("✅ Connected")
    else:
        st.warning("⚠️ Disconnected")

    st.divider()

    # Agent Card Info
    if st.session_state.agent_card:
        card = st.session_state.agent_card
        st.subheader("Agent Info")
        st.write(f"**Name:** {card.get('name', '-')}")
        st.write(f"**Version:** {card.get('version', '-')}")
        st.write(f"**Description:** {card.get('description', '-')}")

        capabilities = card.get("capabilities", {})
        st.write(f"**Streaming:** {'✅' if capabilities.get('streaming') else '❌'}")
        st.write(f"**Push Notifications:** {'✅' if capabilities.get('pushNotifications') else '❌'}")

        st.divider()

        # Skills
        skills = card.get("skills", [])
        if skills:
            st.subheader("Skills")
            for skill in skills:
                with st.expander(f"🔧 {skill.get('name', 'Unknown')}"):
                    st.write(skill.get("description", ""))
                    examples = skill.get("examples", [])
                    if examples:
                        st.write("**Examples:**")
                        for example in examples:
                            if st.button(f"📝 {example}", key=f"ex_{example[:20]}"):
                                st.session_state.example_input = example
                                st.rerun()

        st.divider()

        # Raw Agent Card
        with st.expander("📄 Raw Agent Card"):
            st.json(card)

    # New conversation button
    if st.session_state.connected:
        st.divider()
        if st.button("🔄 New Conversation", use_container_width=True):
            st.session_state.messages = []
            st.session_state.context_id = str(uuid.uuid4())
            st.session_state.task_id = None
            st.rerun()

# Main content - Chat
st.title("💬 Chat")

if not st.session_state.connected:
    st.info("👈 Connect to an agent using the sidebar to start chatting.")
else:
    # Display chat messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Check for example input from sidebar
    if "example_input" in st.session_state:
        example = st.session_state.pop("example_input")
        st.session_state.pending_input = example

    # Chat input
    default_value = st.session_state.pop("pending_input", "")

    if prompt := st.chat_input("Type your message...", key="chat_input"):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Send to agent and get response
        with st.chat_message("assistant"):
            card = st.session_state.agent_card
            use_streaming = card.get("capabilities", {}).get("streaming", False)

            if use_streaming:
                # Streaming response
                status_placeholder = st.empty()
                response_placeholder = st.empty()
                final_response = ""
                current_status = ""

                for data_str in send_message_streaming(
                    agent_url,
                    prompt,
                    st.session_state.context_id,
                ):
                    try:
                        import json
                        data = json.loads(data_str)

                        if "error" in data:
                            st.error(f"Error: {data['error'].get('message', 'Unknown error')}")
                            break

                        if "result" in data:
                            result = data["result"]

                            # Update task ID
                            if result.get("id"):
                                st.session_state.task_id = result["id"]

                            # Handle status updates
                            if "status" in result:
                                status = result["status"]
                                state = status.get("state", "")
                                current_status = state

                                if state == "working":
                                    msg = status.get("message", {})
                                    text = extract_text_from_message(msg)
                                    if text:
                                        status_placeholder.info(f"⏳ {text}")
                                elif state in ("input_required", "completed", "failed"):
                                    status_placeholder.empty()
                                    msg = status.get("message", {})
                                    text = extract_text_from_message(msg)
                                    if text:
                                        final_response = text

                            # Handle artifacts
                            if "artifact" in result:
                                text = extract_text_from_artifact(result["artifact"])
                                if text:
                                    final_response = text

                            # Display final response
                            if final_response:
                                response_placeholder.markdown(final_response)

                            # Reset task ID on completion
                            if current_status in ("completed", "failed"):
                                st.session_state.task_id = None

                    except json.JSONDecodeError:
                        continue

                if final_response:
                    st.session_state.messages.append({"role": "assistant", "content": final_response})

            else:
                # Non-streaming response
                with st.spinner("Thinking..."):
                    response = send_message(
                        agent_url,
                        prompt,
                        st.session_state.context_id,
                    )

                if "error" in response:
                    st.error(f"Error: {response['error'].get('message', 'Unknown error')}")
                elif "result" in response:
                    result = response["result"]
                    st.session_state.task_id = result.get("id")

                    # Get response text
                    response_text = ""
                    if "status" in result and "message" in result["status"]:
                        response_text = extract_text_from_message(result["status"]["message"])

                    if "artifacts" in result:
                        for artifact in result["artifacts"]:
                            text = extract_text_from_artifact(artifact)
                            if text:
                                response_text = text

                    if response_text:
                        st.markdown(response_text)
                        st.session_state.messages.append({"role": "assistant", "content": response_text})

                    # Reset task ID on completion
                    status_state = result.get("status", {}).get("state", "")
                    if status_state in ("completed", "failed"):
                        st.session_state.task_id = None
