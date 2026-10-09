# 주문 수명주기와 대조

## 1. 상태 전이

| 현재 | 이벤트 | 다음 | 포지션 변화 |
|---|---|---|---|
| `NEW` (로컬 생성) | 접수 응답 OK | `ACCEPTED` | 없음 |
| `NEW` | 거부 응답 | `REJECTED` | 없음 |
| `NEW` | 타임아웃 | `UNKNOWN` | 없음. **미체결·체결 조회로 확정** |
| `ACCEPTED` | 체결 (일부) | `PARTIAL` | +체결 수량 |
| `ACCEPTED`/`PARTIAL` | 체결 (잔량 0) | `FILLED` | +체결 수량 |
| `ACCEPTED`/`PARTIAL` | 정정 확인 | `REPLACED` → 새 주문 `ACCEPTED` | 없음. 새 주문은 원주문번호를 참조 |
| `ACCEPTED`/`PARTIAL` | 취소 확인 | `CANCELLED` | 없음 (부분체결분은 유지) |
| `ACCEPTED`/`PARTIAL` | 세션 종료 | `EXPIRED` | 없음 (잔량 소멸) |
| `REPLACING`/`CANCELLING` | 정정·취소 거부 (이미 체결) | 체결 상태로 | 체결 이벤트를 따른다 |

규칙:

- **포지션은 체결 이벤트로만 바뀐다.** 다른 전이는 주문 레코드만 바꾼다.
- 정정·취소를 보냈다고 상태를 바꾸지 않는다. `REPLACING`/`CANCELLING` 중간 상태를 두고
  **응답을 받으면** 확정한다. 정정·취소와 체결은 경합한다.
- `UNKNOWN`은 정상 상태다. 확정될 때까지 같은 종목·방향에 새 주문을 내지 않는다.
- 체결 이벤트는 `(주문번호, 체결번호)`로 **중복 제거**한다. 웹소켓 재연결 후 같은
  체결이 다시 올 수 있다.
- 장 마감 후 남은 `ACCEPTED`/`PARTIAL`이 있으면 `EXPIRED`로 바꾸기 전에 증권사
  미체결 조회로 확인한다. 애프터마켓·NXT 주문은 세션 종료 시점이 다르다.

## 2. 대조 루프

```python
def reconcile(broker, store, *, trade_date):
    # 1) 체결: 증권사가 진실. 로컬에 없는 체결은 추가, 로컬에만 있는 체결은 경보.
    remote = {(f.order_no, f.fill_no): f for f in broker.fills(trade_date)}
    local  = {(f.order_no, f.fill_no): f for f in store.fills(trade_date)}
    for key in remote.keys() - local.keys():
        store.apply_fill(remote[key], source="reconcile")      # 체결통보 유실분
    for key in local.keys() - remote.keys():
        alert("local-only fill", key)                          # 버그. 자동 삭제하지 않는다

    # 2) 미체결
    remote_open = {o.order_no for o in broker.open_orders()}
    for o in store.open_orders():
        if o.order_no not in remote_open:
            store.resolve_from_history(o)                      # 체결/취소/만료 중 무엇인지 조회

    # 3) 잔고
    holdings = broker.holdings()                               # {code: (qty, avg)}
    for code in holdings.keys() | store.position_codes():
        qty = holdings.get(code, (0, None))[0]
        lq = store.position_qty(code)
        if lq != qty:
            if lq and qty and (qty % lq == 0 or lq % qty == 0):
                lock_symbol(code, reason="qty ratio mismatch - corporate action?")
            else:
                lock_symbol(code, reason="qty mismatch")
            alert("holding mismatch", code, local=lq, broker=qty)
```

- 실행 시점: 장 시작 전, 장중 주기(예: 5분), 웹소켓 재연결 직후, 장 마감 후.
- 대조 중에 나온 체결은 `source="reconcile"`로 표시한다. 그 비율이 높으면 실시간
  경로가 망가진 것이다.
- `lock_symbol`은 **신규 진입만** 막는다. 손절은 증권사 잔고 수량 기준으로 계속한다.

## 3. 재시작 복구 순서

순서가 중요하다. 손절 공백을 최소화한다.

1. 토큰 확보 (공유 캐시 우선, 없으면 발급)
2. **증권사 잔고 조회 → 보유 종목 손절가 계산 → 현재가 확인 → 손절 대상이면 즉시 처리**
3. 미체결 조회 → 로컬 open 주문과 대조
4. 당일 체결 대조 (2절)
5. 실시간 시세·체결통보 구독
6. 그다음에 신규 진입 로직 활성화

2번을 5번 뒤로 미루면 구독이 끝날 때까지 손절이 없다.

## 4. 테스트 목록

상태 머신은 가짜 브로커로 테스트한다. **실전에서 오는 순서로** 이벤트를 만든다.
아무도 만들지 않는 행을 DB에 직접 넣는 방식은 쓰지 않는다.

- [ ] 접수 후 무체결 → 포지션 0
- [ ] 부분체결 3회 → 수량 합 정확, 평균 체결가 정확
- [ ] 같은 체결 이벤트 2회 수신 → 1회만 반영
- [ ] 정정 요청 중 원주문 전량 체결 → 정정 거부, 상태 `FILLED`
- [ ] 취소 요청 중 부분체결 → 부분체결분 유지, 잔량 취소
- [ ] 타임아웃 → `UNKNOWN` → 조회 결과 접수됨 → 재주문하지 않음
- [ ] 장 마감 → 잔량 `EXPIRED`, 다음날 open 주문 0
- [ ] 거부(호가단위 오류) → 재시도하지 않음, 원인 기록
- [ ] 웹소켓 끊김 중 체결 → 대조 루프가 복구
- [ ] 분할로 잔고 수량 ×5 → 종목 잠금, 손절 미발동
- [ ] 프로세스 강제 종료 후 재시작 → 손절 점검이 구독보다 먼저 실행
- [ ] 킬 스위치 1단계 → 신규 진입 차단, 손절 경로는 동작
