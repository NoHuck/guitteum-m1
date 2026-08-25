"""api.openapi.yaml 의 /presets, /evidence/{evidence_ref}"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.catalog import list_presets, resolve_evidence

presets_router = APIRouter(prefix="/presets", tags=["presets"])
evidence_router = APIRouter(prefix="/evidence", tags=["evidence"])


@presets_router.get("")
def get_presets():
    return {"presets": list_presets()}


@evidence_router.get("/{evidence_ref}")
def get_evidence(evidence_ref: str):
    result = resolve_evidence(evidence_ref)
    if result is None:
        raise HTTPException(status_code=404, detail="unknown evidence_ref")
    return result
