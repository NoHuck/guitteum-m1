# 귀띔 M1 게이트웨이

프론트(M4) ↔ 판정엔진(M2) ↔ DB 사이를 잇는 FastAPI 서버.

## 구현됨

- ✅ `POST /sessions` — 세션 생성, ws_url 반환. 계약대로 바디 필수·201 반환
- ✅ `WS /ws/{session_id}` — replay 모드. ws_messages.json 중 s2c 16건 송출 (seq 0~15)
- ✅ `GET /sessions/{session_id}/report` — fold 결과, fixture 정답과 일치 확인됨
- ✅ `GET /packs`, `GET /packs/{pack_version}` — 팩 조회
- ✅ `GET /presets` — 심사용 프리셋 목록
- ✅ `GET /evidence/{evidence_ref}` — 근거 원문 위치 (page_image_url 은 자리표시자)
- ✅ 이벤트 append-only 저장 (메모리, DB 아직 아님)
- ✅ `StubEngine` — M2 Protocol 최소 구현, rulepack fixture 실제 로드 확인됨

## 미구현 (다음 슬라이스)

- `GET /sessions/{id}` (요약 조회), `/sessions/{id}/events`, `report.pdf`
- `/packs/{v}/briefing`, `/packs/publish`, `/documents` 계열
- 오디오 업링크 (ws 바이너리 프레임) 와 live·trace·text 모드
- Postgres 전환 (지금은 메모리)
- PII 마스킹 (events.schema.json 이 저장 전 마스킹을 요구함)
- 실제 STT 연동 (현준 님 모델 확정 후)
- 실제 M2 엔진 연동 (StubEngine → 실물 교체)

## 계약과 어긋난 채 남아 있는 것

- `GET /sessions/{id}/report` 응답 모양이 `api.openapi.yaml` 의 `Report` 스키마와
  다르다. 계약은 `sections{summary,omission,commission,comprehension,timeline}` 에
  `generated_at`·`sources`·`disclaimer` 를 요구하는데 지금은 평평한 구조다.
  `docs/frontend-endpoints.md` 는 현재(평평한) 모양을 적어 두었다. 어느 쪽에
  맞출지 팀에서 정한 뒤 고친다.
- `Engine.fold()` 와 `app/fold.py` 가 따로 논다. `engine_contract.py` 는
  "trace 재생과 리포트가 같은 함수를 쓴다" 고 하고 `SessionState` 주석은
  "서로 다른 접기 코드를 쓰면 두 값이 갈라진다" 고 경고한다. M2 연동 전에 정리 필요.

## 실행

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

```bash
curl -X POST localhost:8000/sessions \
  -H 'Content-Type: application/json' -d '{"mode":"replay","preset_id":"preset-dep-a"}'
# -> 201 과 함께 ws_url. 그 url 로 붙으면 replay 시작
curl localhost:8000/sessions/{id}/report
```

## 계약

`contracts/` 폴더는 8/28 동결 대상, **읽기 전용**. 여기 스키마가 이상해 보여도
직접 고치지 말고 팀 회의에서 제기할 것.
