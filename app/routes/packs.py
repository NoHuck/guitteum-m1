"""api.openapi.yaml 의 /packs, /packs/{pack_version}

오늘 범위: 조회만. 발행(/packs/publish)은 관리자 토큰 필요, M3 담당이라 제외.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.fixtures import load_rulepack

router = APIRouter(prefix="/packs", tags=["packs"])


@router.get("")
def list_packs(product_code: str | None = Query(default=None)):
    """오늘 범위엔 fixture 팩 하나뿐이라 목록도 항상 그 하나."""
    pack = load_rulepack()
    if product_code and pack["product"]["code"] != product_code:
        return {"packs": []}
    return {
        "packs": [
            {
                "pack_version": pack["pack_version"],
                "product_code": pack["product"]["code"],
                "product_name": pack["product"]["name"],
                "published_at": pack["published_at"],
            }
        ]
    }


@router.get("/{pack_version}")
def get_pack(pack_version: str):
    pack = load_rulepack()
    if pack["pack_version"] != pack_version:
        raise HTTPException(status_code=404, detail="unknown pack_version")
    return pack
