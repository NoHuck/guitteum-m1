"""귀띔 M1 게이트웨이. 오늘 범위: replay 모드 전체 흐름.

실행:
    uvicorn app.main:app --reload --port 8000

확인:
    curl -X POST localhost:8000/sessions
    -> ws_url 을 websocat 이나 프런트에서 붙이면 25건이 흘러나온다
    curl localhost:8000/sessions/{id}/report
    -> fold 된 종료 요약 (contracts/validate.py 와 같은 값이 나와야 정상)
"""

from __future__ import annotations

from fastapi import FastAPI, WebSocket

from app.routes import sessions
from app.ws import handle_session

app = FastAPI(title="귀띔 M1 게이트웨이", version="0.1.0-replay")

app.include_router(sessions.router)


@app.get("/health")
def health():
    return {"status": "ok", "mode": "replay-only"}


@app.websocket("/ws/{session_id}")
async def ws_endpoint(websocket: WebSocket, session_id: str):
    await handle_session(websocket, session_id)
