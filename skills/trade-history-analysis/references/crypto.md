# 코인·선물

## 계약 종류별 손익 — 가격×수량으로 다시 계산하지 않는다

| 계약 | 수량 단위 | 손익 통화 | 롱 손익 |
|---|---|---|---|
| 선형 (USDT-M) | 기초자산 (BTC 0.01개) | USDT | `qty × (exit − entry)` |
| 인버스 (코인 마진, BitMEX XBTUSD) | USD 계약 | BTC | `qty × (1/entry − 1/exit)` |
| 쿼토 (BitMEX ETHUSD) | 계약 × 승수 | BTC | `qty × 승수 × (exit − entry)` |

거래소가 체결마다 주는 **현금흐름 필드**(BitMEX `execCost`)를 쓰면 계약 종류와 상관없이
`트레이드 손익 = −Σ execCost`다. 스크립트의 `cash` 열이 이 역할을 한다. 계약마다 부호
관례가 다르다(XBTUSD는 매수가 음수, ETHUSD는 매수가 양수). 그래도 합계 공식은 같다.
부호를 손으로 맞추려고 하지 않는다.

**코인 마진 계좌는 자산 자체가 코인이다.** BTC 기준 수익률과 USD 기준 수익률이 크게
다르다. 상승장에서 USD 손익은 대부분 가격 효과다. 행동 분석은 **마진 통화 기준**으로 한다.

## 펀딩·정산·청산은 따로

- **펀딩**은 트레이드 손익이 아니다. 따로 합산해서 원장 대조에만 쓴다. 펀딩 수취가 큰
  해가 있으면 "펀딩을 받는 쪽에 오래 머무는" 습관일 수 있다. 이건 별도 지표로 적는다.
- **만기 정산**(분기물): 거래소가 강제로 포지션을 닫는 행이다. 재구성에 넣지 않으면
  만기물 트레이드가 미청산으로 남는다.
- **강제청산**: BitMEX는 `text == "Liquidation"`. 연도별 청산 체결 건수는 노출 배수와
  같이 본다. 레버리지를 줄인 시점을 찾는 가장 쉬운 신호다.
- 원장(지갑) 실현손익은 **부분 청산 때마다** 잡힌다. 재구성은 0→0에서만 잡는다. 그래서
  기간 끝에 큰 미청산 포지션이 있으면 두 합계가 그 포지션의 부분 실현분만큼 다르다.

## BitMEX execution CSV

| 필드 | 의미 |
|---|---|
| `execType` | `Trade` / `Funding` / `Settlement` — `Trade`만 재구성 |
| `side`, `lastQty`, `lastPx` | 방향, 체결 수량(계약), 체결가 |
| `execCost`, `execComm` | 현금흐름, 수수료 (XBt = 1e-8 BTC). `execComm` 음수 = maker 리베이트 |
| `lastLiquidityInd` | `AddedLiquidity` = maker, `RemovedLiquidity` = taker |
| `ordType`, `execInst` | `Limit`/`Market`/`Stop`, `ParticipateDoNotInitiate` = post-only |
| `text` | `Submission from www.bitmex.com` = 웹 UI 수동 주문, `Liquidation`, `Amend…` |
| `orderID` | 주문 ID (분할 진입·청산 횟수) |

지갑 CSV(`transactType` = `RealisedPNL` / `Deposit` / `Withdrawal`)로 일별 자산을
만들 때는 `transactStatus == Completed`만 쓴다. 취소된 출금이 같이 들어 있다.

## Binance USDT-M

`GET /fapi/v1/userTrades` 응답을 `generic` 형식으로 매핑한다.

| generic 열 | userTrades 필드 |
|---|---|
| `time` | `time` (epoch ms — 스크립트가 자동 인식) |
| `symbol` | **헤지 모드면 `symbol + "_" + positionSide`** — 같은 심볼에 롱·숏이 동시에 있어서, 합치면 서로 상쇄돼 트레이드가 깨진다 |
| `side` | `side` (BUY/SELL) |
| `qty`, `price` | `qty`, `price` |
| `notional` | `quoteQty` |
| `fee` | `commission` (USDT가 아니면 환산 필요 — `commissionAsset` 확인) |
| `liquidity` | `maker` true → `maker` |
| `order_id` | `orderId` |

펀딩·실현손익 원장은 `GET /fapi/v1/income`(`incomeType` = `FUNDING_FEE`,
`REALIZED_PNL`, `COMMISSION`)이다. 두 API 모두 한 번에 조회할 수 있는 기간과 과거 보관
기간에 제한이 있다. 쓰기 전에 공식 문서에서 현재 값을 확인하고, 주기적으로 받아 쌓는다.

`/futures/data/*` 시장 통계(OI·롱숏비율 등)는 보관 기간이 짧다. 진입 맥락 분석에 쓸
계획이면 지금부터 수집한다.

## 진입 맥락용 캔들

체결가로 캔들을 만들지 않는다(SKILL.md 4절). 거래소 공개 klines나 아카이브(예: Binance
`data.binance.vision`)에서 **같은 기간의 실제 시세**를 받는다. 다른 거래소 시세로
대체하면 그 사실을 적는다. 베이시스 차이가 단기 지표를 바꿀 수 있다.
