"""이벤트 스토어. append-only.

계약 규칙(README.md):
- M1(여기)만 봉투를 찍는다: event_id, seq_in_session, occurred_at, session_id, pack_version
- 이벤트는 절대 수정하지 않는다. 정정은 새 이벤트 + supersedes.
- seq_in_session 은 세션 내 단조 증가.

이 파일에 UPDATE 메서드가 없는 건 실수가 아니라 설계다.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def new_id(prefix: str) -> str:
    """운영 id 생성. fixtures 는 FIXT- 접두어라 실물과 눈으로 구분된다."""
    from ulid import ULID  # python-ulid

    return f"{prefix}-{ULID()}"


@dataclass
class EventStore:
    """세션별 append-only 이벤트 로그. 프로세스 메모리 구현.

    실제 배포에서는 이 클래스의 append/list_events 를 DB 테이블로
    바꾸면 된다. 인터페이스만 유지하면 나머지 코드는 안 바뀐다.
    """

    _events: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    _seq_counter: dict[str, itertools.count] = field(default_factory=dict)

    def start_session(self, session_id: str) -> None:
        if session_id in self._events:
            raise ValueError(f"session already exists: {session_id}")
        self._events[session_id] = []
        self._seq_counter[session_id] = itertools.count(0)

    def append(
        self,
        session_id: str,
        pack_version: str,
        kind: str,
        payload: dict[str, Any],
        supersedes: str | None = None,
    ) -> dict[str, Any]:
        """봉투를 찍어서 이벤트 하나를 append 한다. 반환값이 저장된 실물이다."""
        if session_id not in self._events:
            raise ValueError(f"unknown session: {session_id}")

        seq = next(self._seq_counter[session_id])
        event = {
            "schema_version": "1",
            "event_id": new_id("EV"),
            "session_id": session_id,
            "seq_in_session": seq,
            "occurred_at": datetime.now(timezone.utc).isoformat(
                timespec="milliseconds"
            ).replace("+00:00", "Z"),
            "pack_version": pack_version,
            "kind": kind,
            kind: payload,
        }
        if supersedes:
            event["supersedes"] = supersedes

        self._events[session_id].append(event)
        return event

    def list_events(self, session_id: str) -> list[dict[str, Any]]:
        """seq_in_session 순서 그대로. append 순서가 곧 seq 순서이므로 정렬 불필요."""
        if session_id not in self._events:
            raise ValueError(f"unknown session: {session_id}")
        return list(self._events[session_id])


# 프로세스 전역 싱글턴. 여러 워커로 스케일할 때는 DB 백엔드로 교체.
store = EventStore()
