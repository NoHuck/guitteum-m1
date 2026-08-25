"""fixtures/ 를 메모리에 올려서 replay 모드에 물린다.

M2·M3·STT 없이 오늘 돌리기 위한 임시 데이터 소스.
실제 팩/이벤트가 붙으면 이 파일은 통째로 걷어낸다.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

CONTRACTS_DIR = Path(__file__).resolve().parent.parent / "contracts"
FIXTURES_DIR = CONTRACTS_DIR / "fixtures"


@lru_cache
def load_ws_messages() -> list[dict[str, Any]]:
    return json.loads((FIXTURES_DIR / "ws_messages.json").read_text())


@lru_cache
def load_scenario_events() -> list[dict[str, Any]]:
    return json.loads((FIXTURES_DIR / "events_scenario_a.json").read_text())


@lru_cache
def load_rulepack() -> dict[str, Any]:
    return json.loads(
        (FIXTURES_DIR / "rulepack_DEP-2026.08-v3.json").read_text()
    )


@lru_cache
def required_item_codes() -> tuple[str, ...]:
    pack = load_rulepack()
    return tuple(it["code"] for it in pack["items"] if it["type"] == "required")
