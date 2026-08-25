"""WS /ws/{session_id}

ws_protocol.schema.json 의 c2s/s2c 메시지를 다룬다.

오늘 범위(replay 전용):
  1. 클라가 붙으면 hello(mode=replay) 를 기다린다.
  2. hello 를 받으면 fixtures/ws_messages.json 중 **s2c 메시지만**
     원본 seq 순서 그대로 흘려보낸다. (오디오 프레임은 여기 없음 — JSON만)
     fixture 는 c2s·s2c 를 한 파일에 담은 양방향 예시라 그대로 흘리면 안 된다.
  3. 동시에 이 세션의 이벤트 스토어에도 봉투를 찍어 append.
     ws 메시지 자체를 그대로 저장하지 않는다 (README 원칙).
     replay 이므로 저장 원본은 fixtures/events_scenario_a.json 을 그대로 씀.

계약 규칙: 서버 메시지의 seq 는 단조 증가. fixture 가 이미 그렇게
정렬돼 있으므로 여기서는 그 순서를 지키기만 하면 된다.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import WebSocket, WebSocketDisconnect

from app.fixtures import load_scenario_events, load_ws_messages, s2c_message_types
from app.store import store

logger = logging.getLogger("guitteum.ws")

# partial 메시지는 짧게, verdict/alert 처럼 의미 있는 이벤트는 조금 더
# 끌어서 사람이 눈으로 따라올 수 있게 한다. 정교한 타이밍 재현은
# 오늘 범위 밖 — 데모가 자연스럽게 보이는 정도만 맞춘다.
_DELAY_BY_TYPE = {
    "partial": 0.15,
    "ready": 0.1,
}
_DEFAULT_DELAY = 0.35


async def handle_session(ws: WebSocket, session_id: str) -> None:
    await ws.accept()

    try:
        first = await ws.receive_json()
    except WebSocketDisconnect:
        return

    if first.get("t") != "hello":
        await ws.send_json({"t": "error", "code": "protocol_violation",
                              "message": "첫 메시지는 hello 여야 합니다"})
        await ws.close()
        return

    mode = first.get("mode", "replay")
    if mode != "replay":
        await ws.send_json({"t": "error", "code": "unsupported_mode",
                              "message": f"오늘 범위는 replay 만 지원합니다: {mode}"})
        await ws.close()
        return

    store.start_session(session_id)
    messages = load_ws_messages()
    s2c_types = s2c_message_types()
    events = load_scenario_events()
    pack_version = events[0]["pack_version"]

    # events_scenario_a.json 을 그대로 이벤트 스토어에 적재한다.
    # (오늘 replay 범위에서는 이게 "저장된 원본"이다. 실제 라이브
    # 모드에서는 M2 판정 결과가 여기 대신 들어온다.)
    for e in events:
        store.append(
            session_id=session_id,
            pack_version=pack_version,
            kind=e["kind"],
            payload=e[e["kind"]],
            supersedes=e.get("supersedes"),
        )

    try:
        for msg in messages:
            if msg["t"] not in s2c_types:
                # c2s 메시지(hello·ask·mark_waived·pong 등). 계약상 서버는
                # s2c 만 보낸다. 그대로 흘리면 seq 없는 메시지가 끼어들어
                # 프런트의 "seq 는 단조 증가" 가정이 깨진다.
                continue
            delay = _DELAY_BY_TYPE.get(msg["t"], _DEFAULT_DELAY)
            if delay:
                await asyncio.sleep(delay)
            await ws.send_json(msg)

            if msg["t"] == "ping":
                # 계약상 pong 은 클라가 보내는 응답이지만 replay 단독
                # 시연에서는 서버가 자문자답해도 무방
                pass

        await ws.close()
    except WebSocketDisconnect:
        logger.info("client disconnected mid-replay: %s", session_id)
