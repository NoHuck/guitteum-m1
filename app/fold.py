"""events -> state 로 접는다.

README.md: "상태는 이벤트를 접어서 다시 계산할 수 있지만,
이벤트는 상태에서 복원할 수 없다."

핵심 규칙 (디스코드 어제 23:07 현준 메모):
  화면과 리포트는 supersede 되지 않은 마지막 이벤트만 읽는다.

이 파일의 집계 로직은 contracts/validate.py 의 "종료 요약 대조"
블록과 반드시 같은 답을 내야 한다 (거기가 정답을 정의한다).
차이가 생기면 fold.py 가 잘못이지 validate.py 가 잘못이 아니다.

  - 필수(required) 항목인데 omission 축 verdict 이벤트가 한 번도
    없으면 기본 상태는 "unmet" (판정 전 = 아직 못 채움).
  - verdict/assist 는 supersede 안 된 것만 최신으로 채택.
  - alert 는 supersede 없음. 전부 센다.
  - assists_adopted 는 outcome="adopted" 인, supersede 안 된
    assist 이벤트 개수.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SessionSummary:
    session_id: str
    pack_version: str
    product_code: str | None
    started_at: str | None
    ended_at: str | None
    duration_ms: int | None
    verdicts: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)
    alerts: list[dict[str, Any]] = field(default_factory=list)
    assists: list[dict[str, Any]] = field(default_factory=list)
    counted: dict[str, int] = field(default_factory=dict)  # met/partial/unmet/waived
    violations: int = 0

    def to_report(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "pack_version": self.pack_version,
            "product_code": self.product_code,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_ms": self.duration_ms,
            "summary": {
                "items_total": sum(self.counted.values()),
                **self.counted,
                "violations": self.violations,
                "alerts": len(self.alerts),
                "assists_adopted": sum(
                    1 for a in self.assists if a.get("outcome") == "adopted"
                ),
            },
            "verdicts": [
                {"item_code": ic, "axis": ax, **v}
                for (ic, ax), v in sorted(self.verdicts.items())
            ],
            "alerts_detail": self.alerts,
            "assists_detail": self.assists,
        }


def fold(events: list[dict[str, Any]], required_item_codes: list[str]) -> SessionSummary:
    """events_scenario_a.json 같은 이벤트 열을 SessionSummary 로 접는다.

    required_item_codes: rulepack 에서 type="required" 인 item code 목록.
    omission 축 unmet 기본값 계산에 필요하다 (rulepack.item.code 참조,
    validate.py 의 `required = [c for c, it in codes.items() if
    it["type"] == "required"]` 와 동일 소스여야 한다).
    """
    if not events:
        raise ValueError("empty event list")

    session_id = events[0]["session_id"]
    pack_version = events[0]["pack_version"]
    summary = SessionSummary(
        session_id=session_id,
        pack_version=pack_version,
        product_code=None,
        started_at=None,
        ended_at=None,
        duration_ms=None,
    )

    superseded_ids = {e["supersedes"] for e in events if e.get("supersedes")}

    final_verdicts: dict[tuple[str, str], dict[str, Any]] = {}

    for e in events:
        kind = e["kind"]
        eid = e["event_id"]

        if kind == "session_started":
            body = e["session_started"]
            summary.product_code = (body.get("product") or {}).get("code")
            summary.started_at = e["occurred_at"]

        elif kind == "session_ended":
            summary.ended_at = e["occurred_at"]
            summary.duration_ms = e["session_ended"].get("duration_ms")

        elif kind == "alert":
            summary.alerts.append({"event_id": eid, **e["alert"]})

        elif kind == "verdict":
            if eid in superseded_ids:
                continue
            v = e["verdict"]
            final_verdicts[(v["item_code"], v["axis"])] = {
                "state": v["state"],
                "decided_by": v["decided_by"],
                "event_id": eid,
            }

        elif kind == "assist":
            if eid in superseded_ids:
                continue
            body = e["assist"]
            summary.assists.append(
                {
                    "event_id": eid,
                    "assist_type": body.get("assist_type"),
                    "outcome": body.get("outcome"),
                    "item_code": body.get("item_code"),
                }
            )

    summary.verdicts = final_verdicts

    counted = {"met": 0, "partial": 0, "unmet": 0, "waived": 0}
    for code in required_item_codes:
        state = final_verdicts.get((code, "omission"), {}).get("state", "unmet")
        counted[state] = counted.get(state, 0) + 1
    summary.counted = counted

    summary.violations = sum(
        1
        for (code, axis), v in final_verdicts.items()
        if axis == "commission" and v["state"] == "violated"
    )

    return summary
