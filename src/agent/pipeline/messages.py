from __future__ import annotations

from typing import Any

try:
    from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
except ImportError:  # pragma: no cover — langgraph always pulls langchain-core
    BaseMessage = object  # type: ignore[misc, assignment]
    HumanMessage = object  # type: ignore[misc, assignment]
    AIMessage = object  # type: ignore[misc, assignment]


def coerce_chat_message(item: Any) -> dict[str, str]:
    """Normalize LangGraph/LangChain messages for JSON WebSocket payloads."""
    if isinstance(item, dict):
        role = str(item.get("role") or "assistant")
        content = item.get("content", "")
        return {"role": role, "content": _message_content(content)}

    if isinstance(item, BaseMessage):
        if isinstance(item, HumanMessage):
            role = "user"
        elif isinstance(item, AIMessage):
            role = "assistant"
        else:
            role = getattr(item, "type", "assistant")
            if role == "human":
                role = "user"
            elif role == "ai":
                role = "assistant"
        return {"role": role, "content": _message_content(item.content)}

    return {"role": "assistant", "content": str(item)}


def serialize_messages(messages: list[Any] | None) -> list[dict[str, str]]:
    if not messages:
        return []
    return [coerce_chat_message(item) for item in messages]


def _message_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                text = block.get("text") or block.get("content")
                if text:
                    parts.append(str(text))
            else:
                parts.append(str(block))
        return "\n".join(parts)
    return str(content)
