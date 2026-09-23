# 측정 쿼리

## 스키마 가정

아래 쿼리는 이 최소 스키마를 가정한다. 컬럼명이 다르면 바꿔 쓰되 **의미**는 유지한다.

| 테이블 | 핵심 컬럼 |
|---|---|
| `positions` | `symbol`, `strategy_name`, `side`(long/short), `status`, `entry_price`, `exit_price`, `quantity`, `realized_pnl`, `close_reason`, `opened_at`, `closed_at` |
| `shadow_positions` (선택) | 위 + `block_reason`(NULL = 실거래됐을 신호), `realized_r` |

## 타입 함정 (먼저 확인)

시간 컬럼이 `TEXT`로 저장된 스키마가 흔하다. 캐스트 없이 비교하면 조용히 틀리거나
터진다.

```sql
-- ❌ text > timestamptz → operator does not exist
WHERE opened_at > NOW() - INTERVAL '30 days'
-- ✅
WHERE opened_at::timestamptz > NOW() - INTERVAL '30 days'
```

**파라미터 쪽에 캐스트를 붙이지 않는다.** `%s::date`는 sqlite 기반 테스트 하네스에서
`?::date`가 되어 `unrecognized token: ":"`로 깨진다. Postgres는 리터럴을 알아서
강제변환하므로 컬럼 쪽에만 붙인다.

```sql
-- ❌ 테스트에서만 깨진다 (그래서 오래 무테스트로 남는다)
WHERE closed_at::date >= %s::date
-- ✅
WHERE closed_at::date >= %s
```

불리언처럼 쓰는 `INTEGER` 플래그(`is_active`)도 `= 1`로 비교한다. `IS TRUE`는 타입
에러다.

## 1. 원장 대조 (ground truth)

거래소에서 먼저 받고, DB 집계를 그 옆에 놓는다. **둘이 다르면 거래소를 따른다.**

```python
# 거래소 원장. 실현손익 / 수수료 / 펀딩은 별개 항목이다.
rows = client.fetch_income(start_ms=..., end_ms=...)   # 거래소별 메서드명은 다름

gross   = sum(r["income"] for r in rows if r["incomeType"] == "REALIZED_PNL")
fees    = sum(r["income"] for r in rows if r["incomeType"] == "COMMISSION")
funding = sum(r["income"] for r in rows if r["incomeType"] == "FUNDING_FEE")
net     = gross + fees + funding          # fees·funding은 보통 음수로 내려온다

wins  = [r["income"] for r in rows if r["incomeType"] == "REALIZED_PNL" and r["income"] > 0]
losses= [r["income"] for r in rows if r["incomeType"] == "REALIZED_PNL" and r["income"] < 0]
pf    = sum(wins) / abs(sum(losses)) if losses else None

print(f"N={len(wins)+len(losses)} gross={gross:.3f} fees={fees:.3f} "
      f"funding={funding:.3f} net={net:.3f} PF(gross)={pf}")
print(f"수수료/gross 비중 = {abs(fees)/sum(w for w in wins):.1%}")   # 30%↑면 경고
```

**PF를 gross로 계산했으면 그렇게 표기한다.** net PF가 1.0을 밑도는데 gross PF가 1.1인
경우는 흔하고, 그건 엣지가 없다는 뜻이다.

## 2. 전략별 net 집계 — 매매당으로 정규화

```sql
SELECT strategy_name,
       COUNT(*)                                   AS n,
       ROUND(SUM(realized_pnl)::numeric, 3)       AS total,
       ROUND(AVG(realized_pnl)::numeric, 4)       AS per_trade,   -- 판정은 이 열로
       ROUND(100.0 * SUM((realized_pnl > 0)::int) / COUNT(*), 1) AS wr_pct,
       ROUND(
         SUM(CASE WHEN realized_pnl > 0 THEN realized_pnl ELSE 0 END) /
         NULLIF(ABS(SUM(CASE WHEN realized_pnl < 0 THEN realized_pnl ELSE 0 END)), 0)
       , 2)                                       AS pf
FROM positions
WHERE status = 'closed'
  AND realized_pnl IS NOT NULL
  AND closed_at::timestamptz > NOW() - INTERVAL '30 days'
GROUP BY strategy_name
HAVING COUNT(*) >= 30          -- 표본 미달은 순위에 올리지 않는다
ORDER BY per_trade DESC;
```

`HAVING`을 빼고 순위를 보고 싶다면 `n`을 반드시 같이 출력하고, 30 미만 행은 **판정
대상이 아니라고 명시**한다.

## 3. 측면(롱/숏)·심볼별 분리

통합 집계는 상쇄되어 문제를 감춘다. 특히 롱/숏은 항상 분리한다.

```sql
SELECT side, COUNT(*) AS n,
       ROUND(AVG(realized_pnl)::numeric, 4) AS per_trade
FROM positions
WHERE status='closed' AND realized_pnl IS NOT NULL
  AND closed_at::timestamptz > NOW() - INTERVAL '90 days'
GROUP BY side;
```

## 4. 청산 사유 분포 (귀속 검증)

```sql
SELECT close_reason, COUNT(*) AS n,
       ROUND(AVG(realized_pnl)::numeric, 4) AS per_trade
FROM positions
WHERE status='closed'
GROUP BY close_reason ORDER BY n DESC;
```

**손절 사유가 0건이거나 비정상적으로 적으면 귀속 버그다.** 전략이 손절을 안 맞을 수는
없다. `bug-patterns.md` 1번을 읽는다. 거래소 측 조건부 주문 이력 건수와 대조해 확인한다.

## 5. 부분청산 누적 검증

TP1 체결이 있는 거래의 손익이 leg 합과 맞는지 확인한다. 로그·체결 테이블이 있으면
직접 대조하고, 없으면 **부호로 판정**한다.

```sql
-- TP1을 거친 거래가 손실로 기록돼 있으면 덮어쓰기 버그를 의심한다.
-- (TP1에 닿은 뒤 트레일링에 걸려 소폭 손실은 가능하나, 비율이 높으면 버그다)
SELECT close_reason,
       COUNT(*) FILTER (WHERE realized_pnl < 0) AS neg,
       COUNT(*)                                 AS n
FROM positions
WHERE status='closed' AND close_reason IN ('tp_hit','trailing_stop','sl_hit')
GROUP BY close_reason;
```

## 6. 표본 카운트 — 판단 전에 먼저 돌린다

```sql
SELECT DATE_TRUNC('week', closed_at::timestamptz) AS wk,
       COUNT(*) AS trades,
       COUNT(DISTINCT DATE(closed_at::timestamptz)) AS active_days
FROM positions
WHERE status='closed' AND closed_at::timestamptz > NOW() - INTERVAL '60 days'
GROUP BY wk ORDER BY wk;
```

거래 없는 날 비중이 높으면 **엣지 문제가 아니라 처리량(throughput) 문제**다. 승률을
고치려 들기 전에 신호가 왜 안 나오는지 본다.

## 7. 구간 레짐 확인 — 판정 전에 먼저 돌린다

측면별·레짐별 비교를 하기 전에 **그 구간이 방향성 구간이었는지** 본다. 캔들 테이블의
시간 컬럼은 epoch ms `BIGINT`인 경우가 많으므로 파라미터를 ms로 만들어 넘긴다.

```python
from datetime import datetime, timezone
start_ms = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)

cur.execute("""
  SELECT symbol, COUNT(*) AS bars,
         (ARRAY_AGG(close ORDER BY open_time ASC))[1]  AS first_px,
         (ARRAY_AGG(close ORDER BY open_time DESC))[1] AS last_px,
         MAX(high) AS hi, MIN(low) AS lo
  FROM klines
  WHERE interval_type = '1h' AND open_time >= %s
    AND symbol IN ('BTCUSDT', 'SOLUSDT')
  GROUP BY symbol ORDER BY symbol
""", (start_ms,))

for r in cur.fetchall():
    d = dict(r)
    f, l = float(d["first_px"]), float(d["last_px"])
    print(f"{d['symbol']:<9} {(l/f-1)*100:+6.2f}%  "
          f"range {(float(d['hi'])/float(d['lo'])-1)*100:.1f}%  bars={d['bars']}")
```

기준 자산이 구간에서 크게 한 방향으로 움직였으면 **측면별 비교는 무효다.** 유리했던
쪽의 성적도 같이 버린다.

## 8. shadow book — 게이트 비용

`block_reason`별로 나누면 각 게이트가 돈을 아꼈는지 버렸는지 보인다. USDT가 아니라
**R 배수**로 집계한다 — 사이징이 시점마다 달라서 절대금액은 비교 불가다.

```sql
SELECT COALESCE(block_reason, '(would have traded)') AS gate,
       COUNT(*) AS n,
       ROUND(AVG(realized_r)::numeric, 3) AS avg_r
FROM shadow_positions
WHERE status='closed'
GROUP BY gate ORDER BY n DESC;
```

`avg_r`이 양수인 차단 사유는 **그 게이트가 돈을 버리고 있다는 뜻**이다. 단, 먼저
`(would have traded)` 행의 R 분포가 실거래와 일치하는지 확인한다 — 일치하지 않으면
시뮬레이션이 실거래를 예측하지 못하므로 나머지 행도 근거가 못 된다.
