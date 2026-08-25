# 귀띔 M1 게이트웨이 — 프론트 연동 명세

> 원본: `contracts/api.openapi.yaml`, `contracts/ws_protocol.schema.json`
> 이 문서는 그 계약에서 **프론트가 실제로 부를 경로만** 추려 정리한 것.
> 필드 상세나 예외 케이스는 원본 스키마가 항상 우선한다.

## 상태 표시

| 표시 | 의미 |
|---|---|
| ✅ 구현됨 | 오늘 replay 슬라이스로 실제 동작 확인 완료 |
| 🚧 예정 | 계약엔 있음, 아직 미구현 |

---

## 1. 세션 생성 — `POST /sessions` ✅

세션을 하나 만들고 WebSocket 주소를 받는다. **프론트가 상담 화면에 들어갈 때 제일 먼저 호출.**

```
POST /sessions
Content-Type: application/json

{
  "mode": "replay",          // live | replay | trace | text
  "preset_id": "preset-dep-a"  // 심사용 프리셋. /presets 목록에서 고른 값
}
```

응답 `201`:
```json
{
  "session_id": "SESS-01M0...",
  "pack_version": "DEP-2026.08-v3",
  "ws_url": "/ws/SESS-01M0..."
}
```

받은 `ws_url`로 바로 WebSocket 연결.

---

## 2. WebSocket — `WS /ws/{session_id}` ✅ (replay만)

연결하면 **가장 먼저** `hello`를 보내야 한다. 안 보내면 서버가 끊는다.

```json
// 클라 → 서버, 최초 1회
{ "t": "hello", "mode": "replay", "preset_id": "preset-dep-a" }
```

이후 서버가 메시지를 순서대로 밀어준다. **`seq`는 단조 증가**, 화면은 그대로 순서 지켜서 렌더.

| `t` | 의미 | 프론트가 할 일 |
|---|---|---|
| `ready` | 세션 초기 상태 + 항목 9개 목록 | 체크리스트 초기 렌더 |
| `partial` | STT 미확정 전사 | 회색조로 흘려보이기만, 저장 X |
| `utterance` | 확정 발화 | 대화 로그에 추가 |
| `alert` | 숫자 오류 등 경보 | 강조 표시 |
| `verdict` | 항목 상태 갱신 | 체크리스트 해당 항목 갱신. **`ver` 큰 것만 반영**, 작은 게 늦게 와도 무시 |
| `assist` | 개입 제안(넛지·재진술 등) | 화면에 개입 슬롯 1건만 표시 (우선순위 1~7) |
| `progress` | 진행률 | 진행바 |
| `ping` / `pong` | 하트비트 | 30초 무응답 시 재연결 트리거 |
| `error` | 에러 | 아래 에러 코드 표 참조 |
| `ended` | 세션 종료 | `/sessions/{id}/report` 호출로 전환 |

**오늘 범위(replay)에서 안 오는 것:** 오디오 바이너리 프레임. live 모드부터 필요.

---

## 3. 세션 요약 — `GET /sessions/{session_id}` 🚧

이벤트를 접은 현재 상태(파생물). 원본 아님.

```
GET /sessions/{session_id}
→ 200 SessionDetail
```

---

## 4. 종료 리포트 — `GET /sessions/{session_id}/report` ✅

```
GET /sessions/{session_id}/report
```

```json
{
  "session_id": "...",
  "pack_version": "DEP-2026.08-v3",
  "product_code": "SHB-MYPLUS-TD",
  "started_at": "...", "ended_at": "...", "duration_ms": 182000,
  "summary": {
    "items_total": 6, "met": 4, "partial": 0, "unmet": 2, "waived": 0,
    "violations": 1, "alerts": 2, "assists_adopted": 1
  },
  "verdicts": [ { "item_code": "...", "axis": "...", "state": "...", "decided_by": "..." } ],
  "alerts_detail": [...],
  "assists_detail": [...]
}
```

⚠️ 세션이 아직 WS로 replay를 안 거쳤으면 `409` — 리포트는 이벤트가 있어야 나온다.

**PDF 버전** `GET /sessions/{session_id}/report.pdf` 🚧 — 증빙용 다운로드.

---

## 5. 근거 원문 — `GET /evidence/{evidence_ref}` 🚧

alert·verdict·assist에 붙어 나오는 `evidence_ref`를 풀어서 원문 위치를 준다. **인용문 클릭 시 원문 하이라이트 기능**에 필요.

```json
{
  "doc_id": "05_상품설명서_정기예금",
  "doc_title": "...", "publisher": "신한은행", "snapshot_date": "2026-08-20",
  "page": 3,
  "span": "1개월 미만: 연 0.10%",
  "bbox": [x0, y0, x1, y1],
  "page_image_url": "...",
  "context": "스팬 주변 문단"
}
```

화면은 `page_image_url` 위에 `bbox`를 겹쳐 그린다. 외부 링크로 안 보내고 좌표를 주는 이유는 원문이 나중에 개정돼도 과거 근거가 그대로 보이게 하려는 것 — 계약 원문 설명 그대로.

---

## 6. 팩 조회 — `GET /packs/{pack_version}` 🚧

체크리스트 항목 정의 원본. `rulepack.schema.json` 그대로 반환.

## 7. 상담 전 브리핑 — `GET /packs/{pack_version}/briefing` 🚧

세션 시작 전 화면(반드시 말할 것 / 하면 안 되는 말 요약). 캐시돼 있어서 실시간 LLM 호출 없음.

## 8. 심사용 프리셋 목록 — `GET /presets` 🚧

세션 생성 시 `preset_id`로 쓸 목록. **이게 없으면 세션 생성 폼에 뭘 넣을지 프론트가 하드코딩해야 함 — 우선순위 높게 요청하세요.**

---

## 인증

읽기 전부 무인증 (`security: []`). 쓰기 경로(문서 업로드·팩 발행 등, 오늘 범위 아님)만 `Authorization: Bearer <token>` 필요.

---

## 에러 코드 (REST·WS 공용)

```
stt_unavailable | pack_not_found | invalid_message | session_expired
rate_limited | internal | not_found | validation_failed | conflict
```

```json
{ "code": "session_expired", "message": "...", "retryable": true, "detail": {} }
```

`retryable: true`면 프론트가 자동 재시도해도 되는 케이스.

---

## 오늘 당장 프론트가 붙일 수 있는 것

1. `POST /sessions` (mode=replay, preset_id 하드코딩 가능 — `preset-dep-a`)
2. 받은 `ws_url`로 연결, `hello` 전송
3. `ready/partial/utterance/alert/verdict/assist` 렌더
4. `ended` 오면 `GET /sessions/{id}/report` 호출해서 요약 화면

`/presets`, `/packs/{version}`, `/evidence/{ref}`는 다음 슬라이스. 현준·재호한테 우선순위 이 순서로 요청하시면 됩니다.
