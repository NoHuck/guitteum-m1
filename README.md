# 귀띔 M1 게이트웨이

프론트(M4) ↔ 판정엔진(M2) ↔ DB 사이를 잇는 FastAPI 서버.

## 오늘(8/25) 범위

- ✅ `POST /sessions` — 세션 생성, ws_url 반환
- ✅ `WS /ws/{session_id}` — replay 모드, fixtures/ws_messages.json 25건 송출
- ✅ `GET /sessions/{session_id}/report` — fold 결과, fixture 정답과 일치 확인됨
- ✅ 이벤트 append-only 저장 (메모리, DB 아직 아님)
- ✅ `StubEngine` — M2 Protocol 최소 구현, rulepack fixture 실제 로드 확인됨

## 미구현 (다음 슬라이스)

- `/packs`, `/presets`, `/sessions/{id}` (요약 조회), `/evidence/{ref}`
- Postgres 전환 (지금은 메모리)
- 실제 STT 연동 (현주 님 모델 확정 후)
- 실제 M2 엔진 연동 (StubEngine → 실물 교체)

## 실행

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

```bash
curl -X POST localhost:8000/sessions
# -> ws_url 로 붙으면 replay 시작
curl localhost:8000/sessions/{id}/report
```

## 계약

`contracts/` 폴더는 8/28 동결 대상, **읽기 전용**. 여기 스키마가 이상해 보여도
직접 고치지 말고 팀 회의에서 제기할 것.
