"""api.openapi.yaml 의 /sessions, /sessions/{id}, /sessions/{id}/report

오늘 범위: replay 세션 생성 + 종료 리포트 조회.
나머지 REST 경로(문서 업로드, 팩 발행 등)는 이후 슬라이스.
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.fixtures import load_scenario_events, required_item_codes
from app.fold import fold
from app.store import new_id, store

router = APIRouter(prefix="/sessions", tags=["sessions"])


class CreateSessionRequest(BaseModel):
    """api.openapi.yaml 의 POST /sessions requestBody.

    계약이 required 로 잡은 건 mode 하나뿐이다. 나머지는 오늘 범위(replay)에서
    쓰지 않지만, 프런트가 계약대로 보냈을 때 422 로 튕기지 않도록 받아만 둔다.
    """

    mode: Literal["live", "replay", "trace", "text"]
    preset_id: str | None = None
    product_code: str | None = None
    pack_version: str | None = None
    customer_profile: dict[str, Any] | None = None
    source_session_id: str | None = None
    audio_ref: str | None = None


@router.post("", status_code=status.HTTP_201_CREATED)
def create_session(body: CreateSessionRequest):
    """세션을 만들고 ws_url 을 돌려준다. 클라는 이 url 에 붙어 hello 를 보낸다.

    계약은 201 을 명시한다. 200 으로 돌려주면 프런트가 생성 성공을 조회 성공과
    구분하지 못한다.
    """
    if body.mode != "replay":
        # ws.py 와 같은 판단을 REST 에서도 한다. 세션만 만들어 주고 소켓에서
        # 끊으면 클라가 원인을 두 번 찾게 된다.
        raise HTTPException(
            status_code=422,
            detail=f"오늘 범위는 replay 만 지원합니다: {body.mode}",
        )

    session_id = new_id("SESS")
    return {
        "session_id": session_id,
        "pack_version": load_scenario_events()[0]["pack_version"],
        "ws_url": f"/ws/{session_id}",
    }


@router.get("/{session_id}/report")
def get_report(session_id: str):
    """세션 이벤트를 fold 해서 종료 요약을 돌려준다.

    오늘 범위: WS 로 이미 replay 가 끝난 세션만 조회 가능.
    (세션을 만들기만 하고 WS 를 안 붙였으면 이벤트가 없어 404)
    """
    try:
        events = store.list_events(session_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="unknown session")

    if not events:
        raise HTTPException(
            status_code=409,
            detail="세션에 이벤트가 없습니다. WS 로 replay 를 먼저 진행하세요",
        )

    summary = fold(events, list(required_item_codes()))
    return summary.to_report()
