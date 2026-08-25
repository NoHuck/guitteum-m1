"""오늘 범위의 정적 데이터: 프리셋 1개, evidence_ref 해석 규칙.

계약(api.openapi.yaml)은 Preset·evidence 응답 '모양'만 정의하고 실제
목록/참조 규칙은 안 정해져 있다. 여기서 M1이 임시로 정한 것 — 실 서비스
에선 M3(팩 발행 관리자)가 프리셋을 발행하는 경로가 따로 생겨야 한다.

evidence_ref 규칙(오늘 M1이 정한 것, 팀 확인 필요):
  = rulepack item 의 code 를 그대로 쓴다.
  각 item 이 evidence 를 정확히 하나씩 갖고 있어 (rulepack.schema.json
  의 item.evidence, cardinality=1) item_code 가 곧 근거 하나를 가리키는
  자연스러운 키가 된다. 다른 스킴(해시, UUID)을 팀이 원하면 여기만 고치면
  된다 — routes 쪽은 안 건드려도 됨.
"""

from __future__ import annotations

from app.fixtures import load_rulepack, load_scenario_events


def list_presets() -> list[dict]:
    events = load_scenario_events()
    started = events[0]["session_started"]
    pack = load_rulepack()

    return [
        {
            "preset_id": started.get("preset_id", "preset-dep-a"),
            "label": "정기예금 · 중도해지 이자율 누락 + 되물음 시나리오",
            "description": "시나리오 A. 숫자 오류 → 되물음/재진술 → 금지 발언 → 정정, 종료 시 필수 2건 미고지",
            "mode": "replay",
            "product_code": pack["product"]["code"],
            "pack_version": pack["pack_version"],
            "customer_profile": started.get("customer_profile", {"type": "general", "tags": []}),
        }
    ]


def resolve_evidence(evidence_ref: str) -> dict | None:
    """evidence_ref(=item_code) 를 rulepack에서 찾아 근거 응답으로 변환.

    page_image_url 은 자리표시자다. 03_규정문서/ 에 실제 PDF가 들어오고
    페이지 래스터화가 붙기 전까지는 진짜 이미지를 못 만든다 — 오늘 회의에서
    "PDF 누가 올리나요"가 이것 때문에 필요하다.
    """
    pack = load_rulepack()
    item = next((it for it in pack["items"] if it["code"] == evidence_ref), None)
    if item is None:
        return None

    ev = item["evidence"]
    source = next(
        (s for s in pack["sources"] if s["doc_id"] == ev["doc_id"]), None
    )

    return {
        "doc_id": ev["doc_id"],
        "doc_title": source["title"] if source else ev["doc_id"],
        "publisher": source["publisher"] if source else None,
        "snapshot_date": source["snapshot_date"] if source else None,
        "page": ev["page"],
        "span": ev["span"],
        "bbox": ev.get("bbox"),
        "legal_basis": (
            f"{item['legal_basis'][0]['law']} {item['legal_basis'][0]['article']}"
            if item.get("legal_basis")
            else None
        ),
        "page_image_url": f"/static/pending/{ev['doc_id']}/p{ev['page']}.png",
        "context": None,  # 원문 PDF 없어 앞뒤 문단 추출 불가. 오늘 범위 밖
    }
