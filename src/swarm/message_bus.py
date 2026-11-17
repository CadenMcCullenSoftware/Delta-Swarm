"""In-memory message bus (blackboard) for agent communication."""

from __future__ import annotations

from typing import Any

from .types import Message


class MessageBus:
    """Publish-subscribe message bus shared by swarm agents."""

    def __init__(self) -> None:
        self._messages: list[Message] = []
        self._subscribers: dict[str, list[Any]] = {}
        self._counter = 0

    def publish(self, from_agent: str, content: str, to_agent: str | None = None,
                reply_to: str | None = None) -> Message:
        self._counter += 1
        message = Message(
            message_id=f"msg-{self._counter}",
            from_agent=from_agent,
            to_agent=to_agent,
            content=content,
            reply_to=reply_to,
        )
        self._messages.append(message)
        if to_agent is None:
            for handlers in self._subscribers.values():
                for handler in handlers:
                    handler(message)
        else:
            for handler in self._subscribers.get(to_agent, []):
                handler(message)
        return message

    def subscribe(self, agent_id: str, handler: Any) -> None:
        self._subscribers.setdefault(agent_id, []).append(handler)

    def messages_for(self, agent_id: str) -> list[Message]:
        return [m for m in self._messages if m.to_agent in (None, agent_id)]

    def all_messages(self) -> list[Message]:
        return list(self._messages)
