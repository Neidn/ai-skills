# 측정 쿼리

## 스키마 가정

아래 쿼리는 이 최소 스키마를 가정한다. 컬럼명이 다르면 바꿔 쓰되 **의미**는 유지한다.

| 테이블 | 핵심 컬럼 |
|---|---|
| `fills` | `order_no`, `code`(종목코드 6자리), `market`(KOSPI/KOSDAQ), `side`(buy/sell), `qty`, `price`, `fee`, `tax`, `executed_at`(timestamptz), `venue`(KRX/NXT), `strategy_name` |
| `trades` (라운드트립) | `code`, `strategy_name`, `entry_at`, `exit_at`, `qty`, `gross_pnl`, `fee`, `tax`, `net_pnl`, `realized_r`, `close_reason` |
| `cash_events` | `code`, `kind`(dividend/split/bonus/rights), `ex_date`, `amount`, `ratio` |
| `index_daily` | `index_code`(KOSPI/KOSDAQ), `trade_date`, `close`, `high`, `low` |
| `trading_calendar` | `trade_date`, `is_open` |
| `shadow_trades` (선택) | `trades` + `block_reason`(NULL = 실거래됐을 신호) |

## 타입 함정 (먼저 확인)

- **종목코드는 문자열이다.** `005930`을 정수로 저장하면 `5930`이 된다. 조인이 조용히
  0행이 된다. 엑셀·CSV 경유 데이터에서 특히 흔하다.
- **금액은 정수 원 단위로 저장한다.** float 누적 오차가 수수료(원 단위 절사) 대조를
  깨뜨린다. 비율 계산 때만 `::numeric`으로 바꾼다.
- **시간대.** `executed_at`이 naive면 KST인지 UTC인지 먼저 확인한다. 집계는
  `(executed_at AT TIME ZONE 'Asia/Seoul')::date`로 한다.
- **파라미터 쪽에 캐스트를 붙이지 않는다.** `%s::date`는 sqlite 테스트 하네스에서
  `?::date`가 되어 깨진다. 컬럼 쪽에만 붙인다.

```sql
-- ❌ UTC 날짜로 잘린다 (KST 09:00 이전 체결이 전날로 간다)
WHERE executed_at::date = %s
-- ✅
WHERE (executed_at AT TIME ZONE 'Asia/Seoul')::date = %s
```

## 1. 체결내역 대조 (ground truth)

증권사 일별 체결조회를 먼저 받고, DB 집계를 그 옆에 놓는다. **둘이 다르면 증권사를
따른다.** 메서드명·필드명은 증권사 API마다 다르다.

```python
rows = broker.fetch_daily_fills(start="2026-09-01", end="2026-09-30")   # 증권사 원장

buy_amt  = sum(r["qty"] * r["price"] for r in rows if r["side"] == "buy")
sell_amt = sum(r["qty"] * r["price"] for r in rows if r["side"] == "sell")
fees     = sum(r["fee"] for r in rows)
taxes    = sum(r["tax"] for r in rows)       # 거래세 + 농특세. 매도에만 붙는다

print(f"fills={len(rows)} buy={buy_amt:,} sell={sell_amt:,} fee={fees:,} tax={taxes:,}")
print(f"비용/매도대금 = {(fees + taxes) / sell_amt:.3%}")
```

**매수대금 ≠ 매도대금인 구간의 net은 기말 보유분 평가가 필요하다.** 실현손익만
비교하려면 라운드트립이 닫힌 거래만 쓴다. 미실현은 증권사 잔고 평가로 따로 적는다.

DB 쪽 같은 구간:

```sql
SELECT side, COUNT(*) AS n,
       SUM(qty * price) AS amt, SUM(fee) AS fee, SUM(tax) AS tax
FROM fills
WHERE (executed_at AT TIME ZONE 'Asia/Seoul')::date BETWEEN %s AND %s
GROUP BY side;
```

체결 건수가 다르면 **체결통보 유실**(`stock-trading-execution`)을 의심한다. 금액은
같은데 세금이 다르면 세율 하드코딩을 의심한다.

## 2. 비용 분해 — 엣지가 비용에 먹히는가

```sql
SELECT strategy_name,
       COUNT(*)                                        AS n,
       SUM(gross_pnl)                                  AS gross,
       SUM(fee + tax)                                  AS cost,
       ROUND(100.0 * SUM(fee + tax)
             / NULLIF(SUM(CASE WHEN gross_pnl > 0 THEN gross_pnl END), 0), 1) AS cost_pct_of_wins,
       ROUND(AVG(net_pnl)::numeric, 0)                 AS per_trade_net
FROM trades
WHERE exit_at > NOW() - INTERVAL '90 days'
GROUP BY strategy_name
ORDER BY per_trade_net DESC;
```

`cost_pct_of_wins`가 30%를 넘으면 회전율을 낮추는 쪽이 신호 개선보다 효과가 크다.

## 3. 전략·시장·보유기간별 net — 매매당으로 정규화

```sql
SELECT t.strategy_name,
       f.market,
       CASE WHEN (t.entry_at AT TIME ZONE 'Asia/Seoul')::date
               = (t.exit_at  AT TIME ZONE 'Asia/Seoul')::date
            THEN 'intraday' ELSE 'overnight' END       AS holding,
       COUNT(*)                                        AS n,
       COUNT(DISTINCT (t.entry_at AT TIME ZONE 'Asia/Seoul')::date) AS entry_days,
       ROUND(AVG(t.net_pnl)::numeric, 0)               AS per_trade_net,
       ROUND(100.0 * SUM((t.net_pnl > 0)::int) / COUNT(*), 1) AS wr_pct
FROM trades t
JOIN (SELECT DISTINCT code, market FROM fills) f USING (code)
WHERE t.exit_at > NOW() - INTERVAL '90 days'
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3;
```

`entry_days`가 `n`보다 훨씬 작으면 표본이 같은 날에 몰려 있다. 판정에는
`entry_days`를 실질 표본으로 본다.

## 4. 손실 꼬리 — 손절이 갭을 막는가

```sql
SELECT CASE WHEN realized_r <  -1.5 THEN '< -1.5R'
            WHEN realized_r <  -1.05 THEN '-1.5R ~ -1.05R'
            WHEN realized_r <= -0.95 THEN '≈ -1R'
            WHEN realized_r <  0     THEN '-1R ~ 0'
            ELSE '>= 0' END AS bucket,
       COUNT(*) AS n,
       ROUND(AVG(realized_r)::numeric, 2) AS avg_r
FROM trades
WHERE exit_at > NOW() - INTERVAL '180 days'
GROUP BY bucket ORDER BY MIN(realized_r);
```

`< -1.05R` 비중이 높으면 그 거래의 `close_reason`과 진입·청산 시각을 본다. 장 시작
직후 청산(갭), 프로세스 재시작 직후 청산(손절 공백), 하한가·VI 구간이 흔한 원인이다.

## 5. 기업행위 탐지 — 판정 구간의 이상치부터

```sql
-- 구간 내 기업행위가 있었던 종목의 해당일 전후 거래
SELECT e.code, e.kind, e.ex_date, e.ratio,
       t.entry_at, t.exit_at, t.net_pnl, t.close_reason
FROM cash_events e
JOIN trades t ON t.code = e.code
 AND e.ex_date BETWEEN (t.entry_at AT TIME ZONE 'Asia/Seoul')::date
                   AND (t.exit_at  AT TIME ZONE 'Asia/Seoul')::date
WHERE e.ex_date > CURRENT_DATE - 180
ORDER BY e.ex_date;
```

`cash_events`가 없으면 가격 점프로 찾는다. 전일 종가 대비 **가격제한폭 밖**의 변화는
기업행위 외에는 생길 수 없다.

```sql
SELECT code, trade_date, close,
       LAG(close) OVER w AS prev_close,
       ROUND((close::numeric / LAG(close) OVER w - 1) * 100, 1) AS chg_pct
FROM daily_prices                       -- 원주가(비수정) 일봉
WINDOW w AS (PARTITION BY code ORDER BY trade_date)
ORDER BY ABS(close::numeric / NULLIF(LAG(close) OVER w, 0) - 1) DESC
LIMIT 20;
-- |chg_pct| > 30 이면 기업행위(또는 데이터 오류). 해당 종목 손익을 따로 본다
```

## 6. 표본 카운트 — 판단 전에 먼저 돌린다

```sql
SELECT DATE_TRUNC('week', exit_at AT TIME ZONE 'Asia/Seoul') AS wk,
       COUNT(*) AS trades,
       COUNT(DISTINCT (entry_at AT TIME ZONE 'Asia/Seoul')::date) AS entry_days
FROM trades
WHERE exit_at > NOW() - INTERVAL '90 days'
GROUP BY wk ORDER BY wk;
```

거래 없는 주가 많으면 **엣지 문제가 아니라 처리량 문제**다. 신호가 왜 안 나오는지,
유니버스 필터(거래대금·시장경보 제외)가 너무 좁지 않은지 먼저 본다.

## 7. 벤치마크·레짐 확인 — 판정 전에 먼저 돌린다

```sql
SELECT index_code,
       (ARRAY_AGG(close ORDER BY trade_date ASC))[1]  AS first_close,
       (ARRAY_AGG(close ORDER BY trade_date DESC))[1] AS last_close,
       MAX(high) AS hi, MIN(low) AS lo, COUNT(*) AS days
FROM index_daily
WHERE trade_date BETWEEN %s AND %s
GROUP BY index_code;
```

```python
for r in cur.fetchall():
    f, l = float(r["first_close"]), float(r["last_close"])
    print(f"{r['index_code']:<7} {(l/f-1)*100:+6.2f}%  "
          f"range {(float(r['hi'])/float(r['lo'])-1)*100:.1f}%  days={r['days']}")
```

기준지수가 구간에서 크게 한 방향으로 움직였으면 롱 온리 book의 절대수익은 판정 근거가
아니다. 매매별 초과수익(같은 보유기간 지수 수익률 차감)으로 다시 본다.

```sql
SELECT t.strategy_name, COUNT(*) AS n,
       ROUND(AVG(t.net_pnl / (t.qty * t.entry_price)
                 - (ix_exit.close / ix_entry.close - 1))::numeric * 100, 3) AS avg_excess_pct
FROM trades t
JOIN index_daily ix_entry ON ix_entry.index_code = %s
 AND ix_entry.trade_date = (t.entry_at AT TIME ZONE 'Asia/Seoul')::date
JOIN index_daily ix_exit  ON ix_exit.index_code  = %s
 AND ix_exit.trade_date  = (t.exit_at  AT TIME ZONE 'Asia/Seoul')::date
GROUP BY t.strategy_name;
```

(종가 기준 근사다. 장중 진입·청산이면 그 사실을 표기한다. `entry_price`가 스키마에
없으면 `fills`에서 가져온다.)

## 8. shadow book — 게이트 비용

```sql
SELECT COALESCE(block_reason, '(would have traded)') AS gate,
       COUNT(*) AS n,
       ROUND(AVG(realized_r)::numeric, 3) AS avg_r
FROM shadow_trades
WHERE exit_at IS NOT NULL
GROUP BY gate ORDER BY n DESC;
```

원화 금액이 아니라 **R 배수**로 집계한다. `avg_r`이 양수인 차단 사유는 그 게이트가 돈을
버리고 있다는 뜻이다. 먼저 `(would have traded)` 행이 실거래 R 분포와 일치하는지
확인한다. shadow 체결은 **상한가 잠김·VI·거래정지 구간에서 체결을 가정하지 않아야**
실거래를 예측한다.
