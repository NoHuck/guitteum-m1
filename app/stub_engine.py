"""M2 가 나오기 전까지 자리를 지키는 가짜 엔진.

engine_contract.py 의 Engine Protocol 을 그대로 만족한다.
judge()/refine() 은 항상 빈 JudgeResult 를 돌려준다 — "판정이 갈리지 않으면
빈 JudgeResult" 라는 계약 문구 그대로. live 모드에서 실제로 뭘 감지하진
못하지만, M1 의 배관(WS 수신 → judge 호출 → 이벤트 생성)이 깨지지 않고
도는지는 이걸로 확인할 수 있다.

현주 님 엔진이 나오면 이 파일의 StubEngine 대신 진짜 Engine 구현체를
build_engine() 에 넣기만 하면 된다. M1의 나머지 코드(ws.py, routes/)는
Engine 타입에만 의존하므로 안 바뀐다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "contracts"))
from engine_contract import (  # noqa: E402  (contracts 폴더 직접 import, sys.path 조작 이후)
    Engine,
    Evidence,
    JudgeResult,
    PackItem,
    RulePack,
    SessionState,
    Utterance,
)

from app.fixtures import FIXTURES_DIR


def _load_rulepack_from_fixture(pack_version: str) -> RulePack:
    """fixtures/rulepack_<version>.json 을 읽어 RulePack dataclass 로 바꾼다.

    오늘 범위는 fixture 팩 하나뿐이라 pack_version 인자는 검증만 하고
    실제로는 고정 파일을 읽는다. 실 서비스에서는 M3 가 발행한 팩을
    DB/파일에서 읽어오는 코드로 이 함수를 교체한다.
    """
    path = FIXTURES_DIR / f"rulepack_{pack_version}.json"
    if not path.exists():
        raise ValueError(f"알 수 없는 pack_version: {pack_version}")

    raw = json.loads(path.read_text())
    items = tuple(
        PackItem(
            code=it["code"],
            name=it["name"],
            type=it["type"],
            requirement_elements=tuple(it.get("requirement_elements", [])),
            evidence=Evidence(
                doc_id=it["evidence"]["doc_id"],
                page=it["evidence"]["page"],
                span=it["evidence"]["span"],
                bbox=tuple(it["evidence"]["bbox"]) if it["evidence"].get("bbox") else None,
                legal_basis=it.get("legal_basis"),
            ),
            axis=it.get("axis"),
            plain_language=tuple(it.get("plain_language", [])),
            forbidden_examples=tuple(it.get("forbidden_examples", [])),
            documents_required=tuple(it.get("documents_required", [])),
        )
        for it in raw["items"]
    )

    return RulePack(
        pack_version=raw["pack_version"],
        product_code=raw["product"]["code"],
        product_name=raw["product"]["name"],
        embedding_model=raw["embedding"]["model"],
        embedding_dim=raw["embedding"]["dim"],
        items=items,
    )


class StubEngine:
    """Engine Protocol 최소 구현. 아무것도 판정하지 않는다."""

    def __init__(self) -> None:
        self._pack_cache: dict[str, RulePack] = {}

    def load_pack(self, pack_version: str) -> RulePack:
        if pack_version not in self._pack_cache:
            self._pack_cache[pack_version] = _load_rulepack_from_fixture(pack_version)
        return self._pack_cache[pack_version]

    def initial_state(
        self,
        session_id: str,
        pack: RulePack,
        mode: str,
        customer_type: str = "general",
    ) -> SessionState:
        # 필수 항목 전부 unmet, 금지 항목 전부 clean 인 출발점.
        # ItemState 는 engine_contract 에 정의돼 있지만 initial 값 조립은
        # 여기(M2 stub)의 몫 — 실제 엔진도 이 지점에서 같은 일을 한다.
        from engine_contract import ItemState

        items = []
        for it in pack.items:
            if it.type == "required":
                items.append(
                    ItemState(item_code=it.code, axis="omission", state="unmet",
                               decided_by="L1", ver=0)
                )
            elif it.type == "forbidden":
                items.append(
                    ItemState(item_code=it.code, axis="commission", state="clean",
                               decided_by="L1", ver=0)
                )
        return SessionState(
            session_id=session_id, pack_version=pack.pack_version, mode=mode,
            customer_type=customer_type, items=tuple(items),
        )

    def judge(self, utterance: Utterance, pack: RulePack, state: SessionState) -> JudgeResult:
        return JudgeResult()  # 항상 빈 결과 — stub 은 아무것도 감지하지 않는다

    async def refine(self, utterance: Utterance, pack: RulePack, state: SessionState) -> JudgeResult:
        return JudgeResult()

    def apply(self, state: SessionState, result: JudgeResult) -> SessionState:
        return state  # 빈 result 는 상태를 바꾸지 않는다

    def fold(self, events: Sequence[dict]) -> SessionState:
        raise NotImplementedError(
            "M2.fold() 는 stub 미구현. 리포트용 fold 는 app/fold.py 를 쓴다 "
            "(별개 목적: 종료 요약 집계 vs 실시간 SessionState 복원)."
        )

    def answer(self, question: str, pack: RulePack, state: SessionState):
        return None  # 근거 없으면 None — P4 그대로 지킴

    def rephrase(self, source: Utterance, pack: RulePack, state: SessionState):
        return None

    def briefing(self, pack: RulePack, customer_type: str):
        raise NotImplementedError("briefing 은 stub 범위 밖 (팩 발행 시 미리 생성되는 캐시)")

    def documents(self, pack: RulePack, state: SessionState):
        raise NotImplementedError("documents 는 stub 범위 밖")


def build_stub_engine() -> Engine:
    return StubEngine()
