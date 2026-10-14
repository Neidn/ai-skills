#!/usr/bin/env python3
"""체결 내역 → 트레이드(포지션 0→0 구간) 재구성 + 행동 지표 요약.

입력 형식(--format):
  generic  열: time, symbol, side(buy/sell), qty, price
           선택 열: fee, notional, cash, order_id, liquidity(maker/taker), order_type
  bitmex   BitMEX execution CSV (execType=Trade/Funding). 인버스·쿼토 계약은
           cash = -execCost, fee = execComm (XBt → BTC)로 처리한다
  kis      한국투자증권 주식일별주문체결조회(inquire-daily-ccld) output1을
           CSV/JSON으로 저장한 것. 주문 단위 행이며 시각은 주문 시각(ord_tmd)이다
           --kis-profit 에 기간별매매손익현황조회(inquire-period-trade-profit)
           output1을 주면 일자·종목별 fee+tl_tax를 체결금액 비례로 배분한다

선택 입력:
  --equity CSV(date, equity)  일별 계좌 평가금. 있으면 노출 배수와 %자산 손익을 계산

출력:
  <out>/trades.csv   트레이드 1행
  <out>/summary.md   요약 지표 (전체 / 연도별 / 보유시간 구간별)
  표준출력          summary.md 내용

예:
  python reconstruct_trades.py fills.csv --format generic --out out/
  python reconstruct_trades.py 'aoa-execution-*.csv' --format bitmex --out out/
  python reconstruct_trades.py ccld.json --format kis --kis-profit profit.json --out out/
"""

from __future__ import annotations

import argparse
import glob
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# 정규화 후 열: time, symbol, side(+1/-1), qty(>0), price, notional(>0),
#               cash(부호 있는 현금흐름; 매수 −, 매도 +), fee(지불 +), order_id,
#               maker(bool|NaN), is_limit(bool|NaN)


# ---------------------------------------------------------------------------
# 어댑터
# ---------------------------------------------------------------------------

def _read_any(path: str) -> pd.DataFrame:
    files = sorted(glob.glob(path)) or [path]
    frames = []
    for f in files:
        if f.lower().endswith(".json"):
            data = json.loads(Path(f).read_text(encoding="utf-8"))
            if isinstance(data, dict):  # {"output1": [...]} 형태 허용
                data = data.get("output1") or data.get("output") or []
            frames.append(pd.DataFrame(data))
        else:
            frames.append(pd.read_csv(f, encoding="utf-8-sig", low_memory=False, dtype=str))
    return pd.concat(frames, ignore_index=True)


def _num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(",", "", regex=False), errors="coerce")


def load_generic(path: str) -> pd.DataFrame:
    df = _read_any(path)
    need = {"time", "symbol", "side", "qty", "price"}
    missing = need - set(df.columns)
    if missing:
        sys.exit(f"generic 형식에 필요한 열이 없다: {sorted(missing)}")
    tcol = df["time"].astype(str)
    if tcol.str.fullmatch(r"\d{12,13}").all():          # epoch ms (Binance 등)
        times = pd.to_datetime(tcol.astype("int64"), unit="ms")
    else:
        times = pd.to_datetime(tcol, format="mixed")
    out = pd.DataFrame({
        "time": times,
        "symbol": df["symbol"].astype(str),
        "side": np.where(df["side"].str.lower().str.startswith("b"), 1, -1),
        "qty": _num(df["qty"]).abs(),
        "price": _num(df["price"]),
    })
    out["notional"] = _num(df["notional"]).abs() if "notional" in df else out.qty * out.price
    out["cash"] = _num(df["cash"]) if "cash" in df else -out.side * out.notional
    out["fee"] = _num(df["fee"]).fillna(0.0) if "fee" in df else 0.0
    out["order_id"] = df["order_id"].astype(str) if "order_id" in df else out.index.astype(str)
    out["maker"] = (df["liquidity"].str.lower().str.startswith("m")
                    if "liquidity" in df else np.nan)
    out["is_limit"] = (df["order_type"].str.lower().str.contains("limit|지정")
                       if "order_type" in df else np.nan)
    return out


def load_bitmex(path: str) -> pd.DataFrame:
    df = _read_any(path)
    df.columns = [c.lower() for c in df.columns]
    t = df[df["exectype"] == "Trade"].copy()
    out = pd.DataFrame({
        "time": pd.to_datetime(t["transacttime"], format="mixed"),
        "symbol": t["symbol"],
        "side": np.where(t["side"] == "Buy", 1, -1),
        "qty": _num(t["lastqty"]),
        "price": _num(t["lastpx"]),
        # execCost: XBt. 인버스(XBTUSD)는 매수 −, 쿼토(ETHUSD)는 매수 +로 부호가
        # 계약마다 다르지만, 어느 쪽이든 손익 = −Σ execCost 이다.
        "cash": -_num(t["execcost"]) / 1e8,
        "notional": _num(t["execcost"]).abs() / 1e8,
        "fee": _num(t["execcomm"]) / 1e8,
        "order_id": t["orderid"].astype(str),
        "maker": t["lastliquidityind"] == "AddedLiquidity",
        "is_limit": t["ordtype"].isin(["Limit", "StopLimit"]),
    })
    return out


def load_kis(path: str, profit_path: str | None) -> pd.DataFrame:
    df = _read_any(path)
    df.columns = [c.lower() for c in df.columns]
    q = _num(df["tot_ccld_qty"])
    df = df[q > 0].copy()
    ts = pd.to_datetime(df["ord_dt"].astype(str) + df["ord_tmd"].astype(str).str.zfill(6),
                        format="%Y%m%d%H%M%S")
    side = np.where(df["sll_buy_dvsn_cd"].astype(str).str.zfill(2) == "02", 1, -1)
    qty = _num(df["tot_ccld_qty"])
    price = _num(df["avg_prvs"])
    amt = _num(df["tot_ccld_amt"]) if "tot_ccld_amt" in df else qty * price
    out = pd.DataFrame({
        "time": ts, "symbol": df["pdno"].astype(str), "side": side,
        "qty": qty, "price": price, "notional": amt.abs(),
        "order_id": df["odno"].astype(str),
        "maker": np.nan,  # KRX는 maker/taker 구분 수수료가 없다
        "is_limit": (df["ord_dvsn_name"].astype(str).str.contains("지정")
                     if "ord_dvsn_name" in df else np.nan),
    })
    out["cash"] = -out.side * out.notional
    out["fee"] = 0.0
    if profit_path:
        p = _read_any(profit_path)
        p.columns = [c.lower() for c in p.columns]
        p["cost"] = _num(p.get("fee", 0)).fillna(0) + _num(p.get("tl_tax", 0)).fillna(0)
        cost = p.groupby([p["trad_dt"].astype(str), p["pdno"].astype(str)])["cost"].sum()
        key = list(zip(out.time.dt.strftime("%Y%m%d"), out.symbol))
        day_amt = out.groupby([out.time.dt.strftime("%Y%m%d"), out.symbol]).notional.transform("sum")
        out["fee"] = [cost.get(k, 0.0) for k in key] * (out.notional / day_amt).fillna(0)
    else:
        print("경고: --kis-profit 없음 → 수수료·거래세 0으로 계산 (gross)", file=sys.stderr)
    return out


# ---------------------------------------------------------------------------
# 재구성
# ---------------------------------------------------------------------------

def reconstruct(f: pd.DataFrame) -> pd.DataFrame:
    """심볼별 순포지션이 0→0 이 되는 구간을 1 트레이드로 묶는다.

    포지션 부호가 한 체결 안에서 뒤집히면 그 체결을 비율로 나눠 앞 트레이드를 닫고
    나머지로 새 트레이드를 연다.
    """
    f = f.sort_values(["symbol", "time"], kind="stable").reset_index(drop=True)
    rows = []
    for sym, g in f.groupby("symbol", sort=False):
        pos = 0.0
        ep = None
        cost_open = 0.0  # 현재 열린 포지션의 진입 명목(원가 기준)
        for r in g.itertuples(index=False):
            sq = r.side * r.qty
            if ep is None:
                ep = _new_ep(sym, r, 1.0)
                cost_open = 0.0
            new = pos + sq
            if pos != 0 and new != 0 and math.copysign(1, new) != math.copysign(1, pos):
                frac = abs(pos) / r.qty
                _add(ep, r, frac, adding=False)
                ep["end"] = r.time
                rows.append(ep)
                ep = _new_ep(sym, r, 1 - frac)
                _add(ep, r, 1 - frac, adding=True)
                pos, cost_open = new, r.notional * (1 - frac)
                ep["peak_notional"] = cost_open
                continue
            adding = abs(new) > abs(pos)
            _add(ep, r, 1.0, adding=adding)
            if adding:
                cost_open += r.notional
            elif pos != 0:
                cost_open *= max(0.0, 1 - r.qty / abs(pos))
            ep["peak_notional"] = max(ep["peak_notional"], cost_open)
            pos = new
            if abs(pos) < 1e-12:
                ep["end"] = r.time
                rows.append(ep)
                ep, pos = None, 0.0
        if ep is not None:
            ep["end"] = g.time.iloc[-1]
            ep["open"] = True
            rows.append(ep)

    t = pd.DataFrame(rows)
    if t.empty:
        return t
    t["open"] = t["open"].fillna(False).astype(bool) if "open" in t else False
    t["n_entry_orders"] = t.pop("entry_orders").apply(len)
    t["n_exit_orders"] = t.pop("exit_orders").apply(len)
    t["entry_vwap"] = t.entry_val / t.entry_qty
    # 첫 진입가 대비 평균진입가: 음수 = 불리한 방향으로 추가 진입(물타기)
    t["vwap_vs_first_pct"] = (t.entry_vwap / t.first_price - 1) * 100 * t.direction
    t["hold_hours"] = (t.end - t.start).dt.total_seconds() / 3600
    t["net"] = t.gross - t.fee
    t["maker_share"] = t.maker_notional / t.maker_known_notional.replace(0, np.nan)
    t["limit_share"] = t.limit_notional / t.limit_known_notional.replace(0, np.nan)
    drop = ["entry_val", "entry_qty", "maker_notional", "maker_known_notional",
            "limit_notional", "limit_known_notional"]
    return t.drop(columns=drop)


def _new_ep(sym, r, frac):
    return dict(symbol=sym, start=r.time, end=None, direction=int(r.side),
                first_price=r.price, gross=0.0, fee=0.0, fills=0,
                entry_orders=set(), exit_orders=set(), entry_val=0.0, entry_qty=0.0,
                peak_notional=0.0, maker_notional=0.0, maker_known_notional=0.0,
                limit_notional=0.0, limit_known_notional=0.0)


def _add(ep, r, frac, adding):
    ep["gross"] += r.cash * frac
    ep["fee"] += r.fee * frac
    ep["fills"] += 1
    n = r.notional * frac
    (ep["entry_orders"] if adding else ep["exit_orders"]).add(r.order_id)
    if adding:
        ep["entry_val"] += r.price * r.qty * frac
        ep["entry_qty"] += r.qty * frac
    if isinstance(r.maker, (bool, np.bool_)):
        ep["maker_known_notional"] += n
        ep["maker_notional"] += n if r.maker else 0.0
    if isinstance(r.is_limit, (bool, np.bool_)):
        ep["limit_known_notional"] += n
        ep["limit_notional"] += n if r.is_limit else 0.0


# ---------------------------------------------------------------------------
# 요약
# ---------------------------------------------------------------------------

def attach_equity(t: pd.DataFrame, equity_path: str) -> pd.DataFrame:
    e = _read_any(equity_path)
    e = pd.Series(_num(e["equity"]).values,
                  index=pd.to_datetime(e["date"], format="mixed").dt.normalize()).sort_index()
    e = e[~e.index.duplicated(keep="last")]
    # 진입 전날 종가 기준 자산 (당일 손익이 섞이지 않게)
    eq = e.shift(1).reindex(t.start.dt.normalize(), method="ffill")
    # 0 이하 자산(전액 출금 직후 등)으로 나누면 의미 없는 배수가 나온다 → 제외
    eq = eq.where(eq > e.abs().max() * 1e-6).values  # 부동소수 잔여(≈0)도 제외
    t = t.copy()
    t["equity"] = eq
    t["exposure_x"] = t.peak_notional / t.equity
    t["net_pct_equity"] = t.net / t.equity * 100
    return t


def _stats(d: pd.DataFrame) -> dict:
    w, l = d[d.net > 0], d[d.net < 0]
    s = {
        "N": len(d),
        "win%": 100 * len(w) / len(d) if len(d) else np.nan,
        "PF": w.net.sum() / -l.net.sum() if len(l) else np.nan,
        "payoff": w.net.mean() / -l.net.mean() if len(w) and len(l) else np.nan,
        "net": d.net.sum(),
        "fee": d.fee.sum(),
        "long%": 100 * (d.direction > 0).mean(),
        "hold_h_med": d.hold_hours.median(),
        "hold_h_med_win": w.hold_hours.median(),
        "hold_h_med_loss": l.hold_hours.median(),
        "entry_orders_med": d.n_entry_orders.median(),
        "exit_orders_med": d.n_exit_orders.median(),
        "avg_down%": 100 * (d.vwap_vs_first_pct < 0).mean(),
        "maker%": 100 * (d.maker_share * d.peak_notional).sum() / d.peak_notional[d.maker_share.notna()].sum()
        if d.maker_share.notna().any() else np.nan,
        "limit%": 100 * (d.limit_share * d.peak_notional).sum() / d.peak_notional[d.limit_share.notna()].sum()
        if d.limit_share.notna().any() else np.nan,
    }
    if "exposure_x" in d:
        s["exposure_x_med"] = d.exposure_x.median()
        s["exposure_x_p90"] = d.exposure_x.quantile(0.9)
        s["avgW%eq"] = w.net_pct_equity.mean()
        s["avgL%eq"] = l.net_pct_equity.mean()
        s["worst%eq"] = d.net_pct_equity.min()
    return s


def _fmt(df: pd.DataFrame) -> str:
    def f(v):
        if isinstance(v, (float, np.floating)):
            if np.isnan(v):
                return ""
            if float(v).is_integer() or abs(v) >= 1000:
                return f"{v:,.0f}"
            return f"{v:,.2f}"
        return str(v)
    cols = list(df.columns)
    lines = ["| " + " | ".join([df.index.name or ""] + cols) + " |",
             "|" + "---|" * (len(cols) + 1)]
    for idx, row in df.iterrows():
        lines.append("| " + " | ".join([str(idx)] + [f(row[c]) for c in cols]) + " |")
    return "\n".join(lines)


def summarize(t: pd.DataFrame, ledger_total: float | None) -> str:
    closed = t[~t.open]
    out = ["# 트레이드 재구성 요약", ""]
    out.append(f"- 트레이드 {len(closed):,}건 (미청산 {int(t.open.sum())}건 제외), "
               f"기간 {closed.start.min():%Y-%m-%d} ~ {closed.end.max():%Y-%m-%d}")
    out.append(f"- 순손익 합계 {closed.net.sum():,.4f} (수수료 {closed.fee.sum():,.4f} 차감, "
               "펀딩·배당·이자 미포함)")
    if ledger_total is not None:
        out.append(f"- 원장 대조: 원장 {ledger_total:,.4f} vs 재구성 {closed.net.sum():,.4f} "
                   f"(차이 {ledger_total - closed.net.sum():,.4f}) — 차이는 펀딩·미청산·기업행위부터 본다")
    top = closed.net.nlargest(max(1, len(closed) // 20)).sum()
    if closed.net.sum() > 0:
        out.append(f"- 상위 5% 트레이드가 순손익의 {top / closed.net.sum() * 100:.0f}%")
    out += ["", "## 전체", "", _fmt(pd.DataFrame([_stats(closed)], index=pd.Index(["all"], name="")).T.rename(columns={"all": "값"}))]
    by_year = pd.DataFrame({y: _stats(d) for y, d in closed.groupby(closed.start.dt.year)}).T
    by_year.index.name = "year"
    out += ["", "## 연도별", "", _fmt(by_year)]
    buckets = pd.cut(closed.hold_hours, [-1e-9, 0.25, 1, 4, 24, 72, 168, 1e9],
                     labels=["<15m", "15m-1h", "1-4h", "4-24h", "1-3d", "3-7d", ">7d"])
    hb = closed.groupby(buckets, observed=True).apply(
        lambda d: pd.Series({"N": len(d), "win%": 100 * (d.net > 0).mean(), "net": d.net.sum()}))
    hb.index.name = "hold"
    out += ["", "## 보유시간 구간", "", _fmt(hb)]
    worst = closed.nsmallest(10, "net")[["symbol", "start", "direction", "hold_hours", "net",
                                          "n_entry_orders", "vwap_vs_first_pct"]]
    worst = worst.set_index("symbol")
    out += ["", "## 최악 10건", "", _fmt(worst)]
    out += ["", "## 읽는 법", "",
            "- `avg_down%`: 평균진입가가 첫 진입가보다 불리한 트레이드 비율 (물타기 성향)",
            "- `hold_h_med_loss` > `hold_h_med_win`: 손실 트레이드를 더 오래 든다",
            "- `maker%`/`limit%`: 진입 명목 가중. KRX는 maker 개념이 없어 limit%만 의미 있다",
            "- `exposure_x`: 트레이드 중 최대 진입명목 ÷ 전일 자산 (--equity 필요)"]
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("fills", help="체결 파일 경로 (glob 허용)")
    ap.add_argument("--format", choices=["generic", "bitmex", "kis"], default="generic")
    ap.add_argument("--kis-profit", help="kis: 기간별매매손익현황조회 output1 (수수료·제세금 배분용)")
    ap.add_argument("--equity", help="CSV(date, equity) 일별 자산")
    ap.add_argument("--ledger-total", type=float, help="원장 기준 실현손익 합계 (대조용)")
    ap.add_argument("--out", default="out")
    a = ap.parse_args()

    if a.format == "bitmex":
        f = load_bitmex(a.fills)
    elif a.format == "kis":
        f = load_kis(a.fills, a.kis_profit)
    else:
        f = load_generic(a.fills)
    f = f.dropna(subset=["time", "qty", "price"])
    f = f[f.qty > 0]

    t = reconstruct(f)
    if t.empty:
        sys.exit("재구성된 트레이드가 없다")
    if a.equity:
        t = attach_equity(t, a.equity)
    outdir = Path(a.out)
    outdir.mkdir(parents=True, exist_ok=True)
    t.to_csv(outdir / "trades.csv", index=False)
    md = summarize(t, a.ledger_total)
    (outdir / "summary.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
