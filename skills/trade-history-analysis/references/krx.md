# 국내주식 (한국투자증권 Open API)

기준: 한국투자증권 공식 샘플 레포 `koreainvestment/open-trading-api`
(`examples_llm/domestic_stock/`), 2026-10-14 확인. TR ID·필드는 바뀔 수 있으므로 쓰기 전에
같은 레포의 해당 폴더에서 다시 확인한다.

## 받을 데이터 두 개

| 용도 | API | TR ID | 단위 |
|---|---|---|---|
| 트레이드 재구성 | 주식일별주문체결조회 `/uapi/domestic-stock/v1/trading/inquire-daily-ccld` | 실전 `TTTC0081R`(3개월 이내) · `CTSC9215R`(3개월 이전) / 모의 `VTTC0081R` · `VTSC9215R` | **주문** 1행 |
| 비용(수수료·세금) | 기간별매매손익현황조회 `/uapi/domestic-stock/v1/trading/inquire-period-trade-profit` | `TTTC8715R` | 일자 × 종목 1행 |

### 주식일별주문체결조회 output1 — 스크립트가 읽는 필드

| 필드 | 의미 | 스크립트 사용 |
|---|---|---|
| `ord_dt` | 주문일자 YYYYMMDD | 시각 |
| `ord_tmd` | 주문시각 HHMMSS | 시각 (**체결 시각 아님**) |
| `odno` / `orgn_odno` | 주문번호 / 원주문번호 | 주문 ID |
| `sll_buy_dvsn_cd` | `01` 매도 · `02` 매수 | 방향 |
| `pdno` | 종목코드 | 심볼 (앞자리 0 유지 — 문자열로 읽는다) |
| `tot_ccld_qty` | 총체결수량 | 수량. 0이면 미체결·취소 행 → 제외 |
| `avg_prvs` | 체결 평균가 | 가격 |
| `tot_ccld_amt` | 총체결금액 | 명목 |
| `ord_dvsn_name` | 주문구분명 (지정가·시장가 등) | limit% |
| `cncl_yn` | 취소여부 | 참고 |

요청 파라미터: `SLL_BUY_DVSN_CD=00`(전체), `CCLD_DVSN=01`(체결만) 권장,
`INQR_DVSN=01`(정순), `INQR_DVSN_3=00`, `EXCG_ID_DVSN_CD`는 **NXT 체결도 있으면 `ALL`**
(기본 `KRX`면 대체거래소 체결이 빠져 포지션이 0으로 안 돌아온다).

페이징: 실전 1회 100건, 모의 15건. 응답 헤더 `tr_cont`가 `M`/`F`면 `ctx_area_fk100`·
`ctx_area_nk100`을 넘겨 연속조회한다. 3개월 이전 조회는 장 마감 후, 짧은 기간으로 나눠
부르라고 공식 샘플이 권고한다.

**공식 샘플의 `COLUMN_MAPPING`(한글 라벨)은 output2 쪽이 한 칸씩 밀려 있다**
(`tot_ccld_amt`가 "매입평균가격"으로 붙는 등). 저장할 때는 **원래 영문 키**로 저장한다.

### 받아서 저장하기 (공식 샘플 함수 사용)

```python
# open-trading-api/examples_llm/domestic_stock/inquire_daily_ccld 에서 실행
import kis_auth as ka
from inquire_daily_ccld import inquire_daily_ccld
ka.auth(); env = ka.getTREnv()
df1, _ = inquire_daily_ccld(
    env_dv="real", pd_dv="inner", cano=env.my_acct, acnt_prdt_cd=env.my_prod,
    inqr_strt_dt="20260901", inqr_end_dt="20261014",
    sll_buy_dvsn_cd="00", ccld_dvsn="01", inqr_dvsn="01", inqr_dvsn_3="00",
    excg_id_dvsn_cd="ALL",
)
df1.to_csv("ccld.csv", index=False)          # 영문 키 그대로
```

비용 파일은 같은 방식으로 `inquire_period_trade_profit`의 output1을 저장한다(`trad_dt`,
`pdno`, `fee`, `tl_tax` 필드 사용).

```bash
python scripts/reconstruct_trades.py ccld.csv --format kis --kis-profit profit.csv --out out/
```

계좌번호·앱키는 `kis_auth` 설정 파일에만 두고, 저장한 CSV를 공유할 때는 계좌 관련
열(`ord_gno_brno`, `inqr_ip_addr`, `ctac_tlno` 등)을 지운다.

## 주문 단위 데이터의 한계

- **분할 체결이 안 보인다.** 지정가 한 주문이 여러 번에 나눠 체결돼도 1행이다.
  `n_entry_orders`는 "주문 수"이지 "체결 수"가 아니다.
- **보유시간은 주문 시각 기준 근사다.** 장 시작 전에 걸어둔 지정가가 10시에 체결되면
  보유시간이 실제보다 길게 잡힌다. 스캘핑(분 단위) 분석에서는 오차가 결론을 바꿀 수 있다.
- 체결 시각이 필요하면 앞으로의 거래는 **실시간 체결통보**(`H0STCNI0`, 모의 `H0STCNI9`;
  필드 `STCK_CNTG_HOUR` 체결시각, `CNTG_QTY`, `CNTG_UNPR`, `ODER_NO`)를 저장해서
  `generic` 형식으로 넣는다. 과거분은 복원할 수 없다.

## KRX 특성이 지표 해석에 주는 영향

| 특성 | 영향 |
|---|---|
| **비용이 체결 행에 없다** | `--kis-profit` 없이 돌리면 gross다. 일자·종목 비용을 체결금액 비례로 배분하므로 하루 여러 트레이드면 근사다 |
| **거래세는 매도에만, 세율은 해마다 바뀐다** | 상수로 넣지 않는다. 기간손익 API의 `tl_tax`를 쓴다. 회전율 높은 단타일수록 결론이 비용에 좌우된다 |
| **maker/taker 수수료 구분이 없다** | `maker%`는 비어 있다. `limit%`(지정가 비중)만 본다. 지정가의 이점은 리베이트가 아니라 슬리피지 회피다 |
| **개인 공매도 제약** | 사실상 롱 온리 → `long%`는 의미가 없다. 방향 편향 대신 **현금 비중(노출 배수)**을 본다 |
| **1주 단위** | 고가주는 분할 진입이 안 된다. 분할 횟수가 적다고 "한 번에 들어가는 습관"으로 읽지 않는다 |
| **동시호가·VI 단일가 체결** | 장 시작·마감 주문은 주문 시각과 체결가의 관계가 약하다. 진입 맥락 분석에서 09:00·15:20 이후 주문을 따로 본다 |
| **배당락·액면분할·무상증자** | 수량이 불연속으로 바뀌어 포지션이 0으로 안 돌아온다(미청산으로 남는다). 미청산 트레이드가 분할 비율만큼 어긋나 있으면 기업행위다. 자동 보정하지 말고 표시한다 |
| **결제 T+2, 미수** | 노출 배수 > 1이면 미수·신용을 쓴 것이다. 그 트레이드는 따로 본다 |
| **가격제한폭(±30%)** | 하한가에 잠긴 손절은 체결되지 않는다. 최악 트레이드가 제한폭 근처면 "손절을 안 한 것"이 아니라 "못 한 것"일 수 있다 |

장 운영 규칙의 기준값·조회처는 `stock-trading-execution`의 `references/krx-market-rules.md`를
따른다.
