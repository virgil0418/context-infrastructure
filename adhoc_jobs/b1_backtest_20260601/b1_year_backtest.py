from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


TDX_SYS_PATH = Path(r"F:\new_tdx64\PYPlugins\sys")
DEFAULT_TQ_INIT_PATH = Path(r"F:\z哥\b1_year_backtest_tq.py")
DEFAULT_OUT_DIR = Path(r"F:\z哥\runs\20260601-b1-system-full-audit")
MAX_REFRESH_BATCH_SIZE = 100
DEFAULT_START_DATE = "20260101"
DEFAULT_END_DATE = "20260601"
SOURCE_260415_DIR = Path(r"F:\z哥\260415AI文稿")
SOURCE_WIKI_DIR = Path(r"F:\z哥\zettaranc-knowledge\wiki\zettaranc\concepts")


if str(TDX_SYS_PATH) not in sys.path:
    sys.path.insert(0, str(TDX_SYS_PATH))


@dataclass
class FormulaHit:
    code: str
    signal_date: str
    value: str


@dataclass
class TradeResult:
    code: str
    name: str
    industry: str
    signal_source: str
    candidate_decision: str
    signal_date: str
    entry_date: str
    exit_date: str
    b1_close: float
    entry_price: float
    stop_price: float
    initial_risk_pct: float
    final_exit_price: float
    total_return_pct: float
    max_return_pct: float
    adverse_return_pct: float
    r_multiple: float
    days_held: int
    exit_reason: str
    partial_actions: str
    setup_score: int
    setup_grade: str
    j_value: float
    pct_chg_signal: float
    amplitude_signal: float
    wl: float
    yl: float
    formula_satisfied: str
    formula_missing: str
    z_satisfied: str
    z_missing: str
    system_satisfied: str
    system_missing: str
    hard_exclude_reasons: str
    downgrade_reasons: str
    exclusion_evidence_date: str
    s1_status: str
    s1_evidence: str
    didi_status: str
    didi_evidence: str
    historical_like: str
    risk_flags: str
    operation: str


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def to_float(value: Any, default: float = math.nan) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def pct(value: float | None) -> float:
    if value is None or math.isnan(value):
        return math.nan
    return round(value * 100, 2)


def bool_text(items: list[tuple[bool, str]]) -> tuple[str, str]:
    yes = [label for ok, label in items if ok]
    no = [label for ok, label in items if not ok]
    return "；".join(yes), "；".join(no)


def join_text(items: list[str], default: str = "") -> str:
    cleaned = [item for item in items if item]
    return "；".join(cleaned) if cleaned else default


def date_at(df: pd.DataFrame, pos: int) -> str:
    return str(df.index[pos].date())


def last_true_date(df: pd.DataFrame, mask: pd.Series) -> str:
    positions = [df.index.get_loc(index) for index in mask[mask].index]
    positions = [pos for pos in positions if isinstance(pos, int)]
    return date_at(df, positions[-1]) if positions else ""


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def sma_tdx(series: pd.Series, n: int, m: int) -> pd.Series:
    out: list[float] = []
    prev = math.nan
    for raw in series.astype(float):
        value = 0.0 if pd.isna(raw) else float(raw)
        if math.isnan(prev):
            prev = value
        else:
            prev = (m * value + (n - m) * prev) / n
        out.append(prev)
    return pd.Series(out, index=series.index)


def rolling_min_pairs(volume: pd.Series, idx: int) -> float:
    values = []
    for start in range(1, 16, 2):
        a = idx - start
        b = idx - start - 1
        if a >= 0 and b >= 0:
            values.append(min(volume.iloc[a], volume.iloc[b]))
    return min(values) if values else math.nan


def calc_turnover_up_wave(df: pd.DataFrame, idx: int, active_capital_wan_shares: float) -> tuple[float | None, float | None]:
    if idx < 20 or not active_capital_wan_shares or math.isnan(active_capital_wan_shares):
        return None, None
    recent = df.iloc[max(0, idx - 59) : idx + 1].copy()
    if len(recent) < 20:
        return None, None
    low_label = recent["Low"].idxmin()
    low_pos = recent.index.get_loc(low_label)
    after_low = recent.iloc[low_pos:]
    if len(after_low) < 3:
        return None, None
    high_label = after_low["High"].idxmax()
    high_pos = recent.index.get_loc(high_label)
    if high_pos <= low_pos:
        return None, None
    wave = recent.iloc[low_pos : high_pos + 1]
    low = float(wave["Low"].iloc[0])
    high = float(wave["High"].max())
    gain = high / low - 1 if low > 0 else None
    turnover = float(wave["Volume"].sum()) / (active_capital_wan_shares * 10000)
    return turnover, gain


def detect_s1_reset(df: pd.DataFrame, idx: int) -> dict[str, Any]:
    start = max(0, idx - 80)
    evidence: list[dict[str, Any]] = []
    c = df["Close"]
    o = df["Open"]
    h = df["High"]
    l = df["Low"]
    v = df["Volume"]
    for pos in range(start, idx):
        if pos < 20:
            continue
        avg20 = float(v.iloc[max(0, pos - 19) : pos + 1].mean())
        if not avg20 or math.isnan(avg20):
            continue
        close = float(c.iloc[pos])
        open_price = float(o.iloc[pos])
        high_price = float(h.iloc[pos])
        low60 = float(l.iloc[max(0, pos - 59) : pos + 1].min())
        rise_from_low = close / low60 - 1 if low60 > 0 else 0
        body_or_stall = close <= open_price or close / high_price <= 0.96 or float(df["pct_chg"].iloc[pos]) < 0.015
        high_position = rise_from_low >= 0.18 or close >= float(h.iloc[max(0, pos - 59) : pos + 1].quantile(0.75))
        huge_volume = float(v.iloc[pos]) >= 1.8 * avg20
        if high_position and huge_volume and body_or_stall:
            evidence.append(
                {
                    "pos": pos,
                    "date": date_at(df, pos),
                    "high": float(h.iloc[pos]),
                    "volume": float(v.iloc[pos]),
                    "reason": "高位天量阴线/S1",
                }
            )
    if not evidence:
        return {"status": "无S1", "evidence": "", "evidence_date": "", "reset": True}

    latest = evidence[-1]
    after = df.iloc[latest["pos"] + 1 : idx + 1]
    if after.empty:
        return {
            "status": "S1未结构重置",
            "evidence": f"{latest['date']} {latest['reason']}",
            "evidence_date": latest["date"],
            "reset": False,
        }
    covered = bool((after["Close"] > latest["high"]).any())
    shrink_back = bool(after["Volume"].tail(5).mean() < latest["volume"] * 0.65) if len(after) >= 5 else False
    clean_structure = bool(df["Close"].iloc[idx] > df["YL"].iloc[idx] and df["WL"].iloc[idx] > df["YL"].iloc[idx])
    if covered and shrink_back and clean_structure:
        status = "S1已结构重置"
        reset = True
    else:
        status = "S1未结构重置"
        reset = False
    missing: list[str] = []
    if not covered:
        missing.append("未带量盖过S1高点")
    if not shrink_back:
        missing.append("盖过后未重新缩量")
    if not clean_structure:
        missing.append("未重新站回白黄线结构")
    detail = f"{latest['date']} {latest['reason']}"
    if missing:
        detail += f"({join_text(missing)})"
    return {"status": status, "evidence": detail, "evidence_date": latest["date"], "reset": reset}


def detect_didi(df: pd.DataFrame, idx: int) -> dict[str, Any]:
    start = max(1, idx - 60)
    for pos in range(start + 1, idx + 1):
        prev = df.iloc[pos - 1]
        row = df.iloc[pos]
        low60 = float(df["Low"].iloc[max(0, pos - 59) : pos + 1].min())
        high_position = bool(float(row["Close"]) / low60 - 1 >= 0.18) if low60 > 0 else False
        prev_yin = bool(prev["Close"] <= prev["Open"])
        curr_yin = bool(row["Close"] <= row["Open"])
        stair_down = bool(row["Close"] < prev["Low"])
        not_shrink = bool(row["Volume"] >= prev["Volume"] * 0.75)
        if high_position and prev_yin and curr_yin and stair_down and not_shrink:
            return {
                "status": "嘀嘀/阶梯量风险",
                "evidence": f"{date_at(df, pos - 1)}~{date_at(df, pos)} 高位两阴阶梯量",
                "evidence_date": date_at(df, pos),
            }
    return {"status": "无嘀嘀", "evidence": "", "evidence_date": ""}


def classify_historical_like(row: dict[str, Any]) -> str:
    labels: list[str] = []
    if row["n_shape"] and row["key_k_recent"] and row["shrink_ok"] and row["near_yellow"] and row["small_body"]:
        labels.append("华纳药厂/娜娜图：放量启动后缩量回踩，接近黄线或碗沿")
    if row["n_shape"] and row["shrink_ok"] and row["long_consolidation"]:
        labels.append("国轩高科变量型：时间换空间，洗盘不极致但结构还在")
    if row["n_shape"] and row["high_box"] and row["red_fat_green_thin"]:
        labels.append("新瀚新材横盘压缩型：回调不深，高位箱体压缩")
    if row["far_above_yellow"] and row["shrink_ok"] and row["strong_trend"]:
        labels.append("昂利康高控盘激进型：强趋势里缩量，止损盯白线")
    if row["messy"]:
        labels.append("反面像：呼吸紊乱，和完美 B1 有距离")
    if row["big_yin_risk"]:
        labels.append("反面像：放量阴线后 B1，容易变成一波流回落")
    return "；".join(labels) if labels else "暂未匹配到高置信历史模板"


def iter_batches(items: list[str], batch_size: int) -> list[list[str]]:
    return [items[i : i + batch_size] for i in range(0, len(items), batch_size)]


def parse_tdx_json(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if raw is None:
        return {}
    text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {"raw": parsed}
    except json.JSONDecodeError:
        return {"raw": text}


def refresh_daily_kline(tq: Any, stocks: list[str], enabled: bool) -> dict[str, Any]:
    if not enabled:
        return {
            "enabled": False,
            "period": "1d",
            "stock_count": len(stocks),
            "started_at": now_iso(),
            "finished_at": now_iso(),
            "ok": None,
            "message": "skipped by --skip-refresh",
            "batches": [],
        }
    batches = iter_batches(stocks, MAX_REFRESH_BATCH_SIZE)
    summary: dict[str, Any] = {
        "enabled": True,
        "period": "1d",
        "stock_count": len(stocks),
        "batch_size": MAX_REFRESH_BATCH_SIZE,
        "batch_count": len(batches),
        "started_at": now_iso(),
        "batches": [],
    }
    for index, batch in enumerate(batches, start=1):
        item: dict[str, Any] = {"batch": index, "count": len(batch), "first": batch[0], "last": batch[-1], "started_at": now_iso()}
        try:
            raw = tq.refresh_kline(stock_list=batch, period="1d")
            parsed = parse_tdx_json(raw)
            error_id = parsed.get("ErrorId")
            item.update(
                {
                    "finished_at": now_iso(),
                    "ok": str(error_id) == "0",
                    "error_id": "" if error_id is None else str(error_id),
                    "error": str(parsed.get("Error", "")),
                    "raw": parsed.get("raw", raw),
                }
            )
        except Exception as exc:
            item.update({"finished_at": now_iso(), "ok": False, "error": repr(exc)})
        summary["batches"].append(item)
    ok_count = sum(1 for item in summary["batches"] if item.get("ok"))
    summary["ok_batch_count"] = ok_count
    summary["failed_batch_count"] = len(summary["batches"]) - ok_count
    summary["ok"] = bool(summary["batches"]) and ok_count == len(summary["batches"])
    summary["finished_at"] = now_iso()
    return summary


def collect_formula_hits(
    tq: Any,
    stocks: list[str],
    start_date: str,
    end_date: str,
    return_count: int,
    batch_size: int,
) -> tuple[list[FormulaHit], dict[str, Any]]:
    hits: list[FormulaHit] = []
    stats: dict[str, Any] = {
        "formula_name": "B1",
        "start_date": start_date,
        "end_date": end_date,
        "return_count": return_count,
        "stock_count": len(stocks),
        "batch_size": batch_size,
        "started_at": now_iso(),
        "batches": [],
        "zero_count": 0,
        "null_count": 0,
        "cell_count": 0,
    }
    for index, batch in enumerate(iter_batches(stocks, batch_size), start=1):
        batch_stats: dict[str, Any] = {"batch": index, "count": len(batch), "started_at": now_iso()}
        try:
            res = tq.formula_process_mul_xg(
                formula_name="B1",
                return_count=return_count,
                return_date=True,
                stock_list=batch,
                stock_period="1d",
                start_time=start_date,
                end_time=end_date,
                count=0,
            )
            batch_hits = 0
            for code in batch:
                xg = (res.get(code, {}) or {}).get("XG") or []
                for item in xg:
                    value = item.get("Value")
                    date = str(item.get("Date", ""))
                    if not date:
                        continue
                    stats["cell_count"] += 1
                    if value in (None, ""):
                        stats["null_count"] += 1
                    elif str(value) in ("0", "0.0"):
                        stats["zero_count"] += 1
                    else:
                        hits.append(FormulaHit(code=code, signal_date=date, value=str(value)))
                        batch_hits += 1
            batch_stats.update(
                {
                    "finished_at": now_iso(),
                    "ok": str(res.get("ErrorId", "")) in ("0", "19"),
                    "error_id": str(res.get("ErrorId", "")),
                    "hit_count": batch_hits,
                }
            )
        except Exception as exc:
            batch_stats.update({"finished_at": now_iso(), "ok": False, "error": repr(exc), "hit_count": 0})
        stats["batches"].append(batch_stats)
    stats["hit_count"] = len(hits)
    stats["ok_batch_count"] = sum(1 for item in stats["batches"] if item.get("ok"))
    stats["failed_batch_count"] = len(stats["batches"]) - stats["ok_batch_count"]
    stats["finished_at"] = now_iso()
    return hits, stats


def collect_market_data(tq: Any, stocks: list[str], count: int, batch_size: int) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    merged: dict[str, list[pd.DataFrame]] = {field: [] for field in ("Open", "High", "Low", "Close", "Volume", "Amount")}
    stats: dict[str, Any] = {"stock_count": len(stocks), "count": count, "batch_size": batch_size, "started_at": now_iso(), "batches": []}
    for index, batch in enumerate(iter_batches(stocks, batch_size), start=1):
        item: dict[str, Any] = {"batch": index, "count": len(batch), "started_at": now_iso()}
        try:
            data = tq.get_market_data(
                field_list=list(merged.keys()),
                stock_list=batch,
                period="1d",
                count=count,
                dividend_type="front",
                fill_data=False,
            )
            fields_ok = 0
            for field in merged:
                df = data.get(field)
                if df is not None and not df.empty:
                    merged[field].append(df)
                    fields_ok += 1
            item.update({"finished_at": now_iso(), "ok": fields_ok > 0, "fields_ok": fields_ok})
        except Exception as exc:
            item.update({"finished_at": now_iso(), "ok": False, "error": repr(exc)})
        stats["batches"].append(item)
    out: dict[str, pd.DataFrame] = {}
    for field, parts in merged.items():
        if parts:
            out[field] = pd.concat(parts, axis=1)
    stats["ok_batch_count"] = sum(1 for item in stats["batches"] if item.get("ok"))
    stats["failed_batch_count"] = len(stats["batches"]) - stats["ok_batch_count"]
    stats["finished_at"] = now_iso()
    return out, stats


def dataframe_for_code(data: dict[str, pd.DataFrame], code: str) -> pd.DataFrame | None:
    frames: dict[str, pd.Series] = {}
    for field in ("Open", "High", "Low", "Close", "Volume", "Amount"):
        df = data.get(field)
        if df is None or code not in df.columns:
            return None
        frames[field] = pd.to_numeric(df[code], errors="coerce")
    out = pd.DataFrame(frames).dropna(subset=["Open", "High", "Low", "Close"])
    if len(out) < 130:
        return None
    return out


def enrich_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    c = df["Close"]
    o = df["Open"]
    h = df["High"]
    l = df["Low"]
    v = df["Volume"]
    df["WL"] = ema(ema(c, 10), 10)
    df["YL"] = (c.rolling(14).mean() + c.rolling(28).mean() + c.rolling(57).mean() + c.rolling(114).mean()) / 4
    df["BB"] = (c.rolling(3).mean() + c.rolling(6).mean() + c.rolling(12).mean() + c.rolling(24).mean()) / 4
    den = h.rolling(9).max() - l.rolling(9).min()
    rsv = (c - l.rolling(9).min()) / den.replace(0, math.nan) * 100
    rsv = rsv.fillna(50)
    k = sma_tdx(rsv, 3, 1)
    d = sma_tdx(k, 3, 1)
    df["J"] = 3 * k - 2 * d
    real_yang = (c > o) & ~(c < c.shift(1))
    real_yin = (c < o) & ~(c > c.shift(1))
    df["real_yang"] = real_yang
    df["real_yin"] = real_yin
    df["yang_yin_ok"] = (((v * real_yang).rolling(21).sum() > 1.5 * (v * real_yin).rolling(21).sum()) | ((v * real_yang).rolling(14).sum() > 1.5 * (v * real_yin).rolling(14).sum())).fillna(False)
    avg40 = v.rolling(40).mean()
    df["plry"] = (v > 1.8 * v.shift(1)) & (c > o) & (v > 1.5 * avg40)
    v40p = v.shift(1).rolling(40).mean()
    bd = (c > c.shift(1)) & (c >= o)
    bigv = v > 1.75 * v40p
    r55 = c.rolling(40).min() + 0.55 * (c.rolling(40).max() - c.rolling(40).min())
    df["key_k"] = bd & bigv & (c > r55)
    df["pct_chg"] = c / c.shift(1) - 1
    df["amplitude"] = (h - l) / c.shift(1)
    df["avg_amount_28_yi"] = df["Amount"].rolling(28).mean() / 100000000
    return df


def signal_features(code: str, info: dict[str, Any], df: pd.DataFrame, signal_pos: int, entry_price: float, stop_price: float) -> dict[str, Any]:
    row = df.iloc[signal_pos]
    c = df["Close"]
    h = df["High"]
    l = df["Low"]
    v = df["Volume"]
    o = df["Open"]
    active_capital = to_float(info.get("ActiveCapital"))
    market_cap_yi = float(row["Close"] * active_capital * 100 / 100000000) if not math.isnan(active_capital) else math.nan
    idx = signal_pos
    zm1 = rolling_min_pairs(v, idx)
    shrink_ok = bool((v.iloc[idx] < ema(v, 34).iloc[idx]) or (v.iloc[idx] < v.iloc[max(0, idx - 4) : idx + 1].max() * 0.5) or (not math.isnan(zm1) and v.iloc[idx] <= zm1))
    rise_from_60_low = float(c.iloc[idx] / l.iloc[max(0, idx - 59) : idx + 1].min() - 1)
    retreat_from_60_high = float(c.iloc[idx] / h.iloc[max(0, idx - 59) : idx + 1].max() - 1)
    turnover_up_wave, up_wave_gain = calc_turnover_up_wave(df, idx, active_capital)
    wl = float(row["WL"])
    yl = float(row["YL"])
    near_yellow = bool(abs(row["Close"] / yl - 1) <= 0.06) if yl else False
    near_white = bool(abs(row["Close"] / wl - 1) <= 0.04) if wl else False
    near_support = "靠近黄线" if near_yellow else ("靠近白线" if near_white else ("黄线上方但距离偏远" if row["Close"] > yl else "黄线下方"))
    key_k_recent = bool((df["key_k"] | df["plry"]).iloc[max(0, idx - 27) : idx + 1].any())
    small_body = bool(abs(row["Close"] / row["Open"] - 1) <= 0.025 and row["amplitude"] <= 0.055)
    ideal_b1_day = bool(-0.02 <= row["pct_chg"] <= 0.018 and row["amplitude"] < 0.04)
    long_consolidation = bool((h.iloc[max(0, idx - 14) : idx + 1].max() / l.iloc[max(0, idx - 14) : idx + 1].min() - 1) <= 0.18)
    high_box = bool(retreat_from_60_high > -0.12 and rise_from_60_low > 0.18)
    recent_real_yang = df["real_yang"].iloc[max(0, idx - 20) : idx + 1]
    recent_real_yin = df["real_yin"].iloc[max(0, idx - 20) : idx + 1]
    red_mean = v.iloc[max(0, idx - 20) : idx + 1][recent_real_yang].mean()
    green_mean = v.iloc[max(0, idx - 20) : idx + 1][recent_real_yin].mean()
    red_fat_green_thin = bool((0 if pd.isna(red_mean) else red_mean) >= (0 if pd.isna(green_mean) else green_mean))
    strong_trend = bool(df["WL"].iloc[idx] > df["YL"].iloc[idx] and df["WL"].iloc[idx] > df["WL"].iloc[max(0, idx - 5)] and df["YL"].iloc[idx] >= df["YL"].iloc[max(0, idx - 5)])
    far_above_yellow = bool(row["Close"] / yl - 1 > 0.08) if yl else False
    messy = bool(row["amplitude"] > 0.08 or df["amplitude"].iloc[max(0, idx - 7) : idx + 1].mean() > 0.065)
    recent_big_yin = ((c < c.shift(1)) & (c <= o) & (v > v.rolling(20).mean() * 1.5)).iloc[max(0, idx - 9) : idx + 1]
    big_yin_risk = bool(recent_big_yin.any())
    big_yin_date = last_true_date(df, recent_big_yin) if big_yin_risk else ""
    two_limit_down = (((c / c.shift(1) - 1) <= -0.098) & ((c / c.shift(1) - 1) <= -0.098).shift(1)).iloc[max(0, idx - 23) : idx + 1]
    two_limit_down_risk = bool(two_limit_down.any())
    two_limit_down_date = last_true_date(df, two_limit_down) if two_limit_down_risk else ""
    no_two_limit_down = not two_limit_down_risk
    maxvol_yin = ((v == v.iloc[max(0, idx - 27) : idx + 1].max()) & df["real_yin"]).iloc[max(0, idx - 27) : idx + 1]
    maxvol_yin_risk = bool(maxvol_yin.any())
    maxvol_yin_date = last_true_date(df, maxvol_yin) if maxvol_yin_risk else ""
    no_maxvol_yin = not maxvol_yin_risk
    s1_info = detect_s1_reset(df, idx)
    didi_info = detect_didi(df, idx)
    liquidity_ok = bool(row["avg_amount_28_yi"] >= 0.005)
    mv_ok = bool(market_cap_yi >= 50) if not math.isnan(market_cap_yi) else False
    n_shape = bool(row["Close"] > yl and rise_from_60_low >= 0.12 and retreat_from_60_high <= -0.03)
    risk_pct = (entry_price - stop_price) / entry_price if entry_price > 0 else math.nan

    formula_items = [
        (row["J"] <= 13, f"J<=13({row['J']:.1f})"),
        (wl > yl, "白线>黄线"),
        (row["Close"] > yl, "收盘>黄线"),
        (bool(row["yang_yin_ok"]), "14/21日阳量强于阴量"),
        (key_k_recent, "28日内有关键K/倍量柱"),
        (shrink_ok, "当前缩量/地量"),
        (liquidity_ok, "28日均额>50万"),
        (mv_ok, "市值>50亿"),
        (no_maxvol_yin, "无28日天量阴线"),
        (no_two_limit_down, "24日无两连跌停"),
    ]
    z_items = [
        (n_shape, "N型/上涨后回调"),
        (key_k_recent, "左侧有异动或关键K"),
        (shrink_ok, "右侧缩量"),
        (near_yellow or near_white, near_support),
        (small_body, "B1日波动温和"),
        (ideal_b1_day, "B1日涨跌幅/振幅温和"),
        (turnover_up_wave is None or turnover_up_wave <= 0.40, "建仓波换手未明显过热"),
        (up_wave_gain is None or up_wave_gain <= 0.45, "建仓波涨幅未明显过高"),
    ]
    formula_satisfied, formula_missing = bool_text(formula_items)
    z_satisfied, z_missing = bool_text(z_items)
    risk_flags: list[str] = []
    hard_exclude_reasons: list[str] = []
    downgrade_reasons: list[str] = []
    exclusion_dates: list[str] = []
    if info.get("IsSTGP") == "1":
        risk_flags.append("ST")
        hard_exclude_reasons.append("ST")
    if info.get("IsQuitGP") == "1":
        risk_flags.append("退市风险")
        hard_exclude_reasons.append("退市风险")
    if messy:
        risk_flags.append("K线/呼吸偏乱")
        hard_exclude_reasons.append("K线/呼吸极乱")
    if big_yin_risk:
        risk_flags.append("近期放量阴线")
        downgrade_reasons.append(f"近期放量阴线({big_yin_date})")
        if big_yin_date:
            exclusion_dates.append(big_yin_date)
    if maxvol_yin_risk:
        hard_exclude_reasons.append(f"28日天量阴线未解除({maxvol_yin_date})")
        if maxvol_yin_date:
            exclusion_dates.append(maxvol_yin_date)
    if s1_info["status"] == "S1未结构重置":
        hard_exclude_reasons.append(str(s1_info["evidence"]))
        if s1_info.get("evidence_date"):
            exclusion_dates.append(str(s1_info["evidence_date"]))
    elif s1_info["status"] == "S1已结构重置":
        downgrade_reasons.append(str(s1_info["evidence"]))
    if didi_info["status"] != "无嘀嘀":
        hard_exclude_reasons.append(str(didi_info["evidence"]))
        if didi_info.get("evidence_date"):
            exclusion_dates.append(str(didi_info["evidence_date"]))
    if two_limit_down_risk:
        hard_exclude_reasons.append(f"24日内两连跌停({two_limit_down_date})")
        if two_limit_down_date:
            exclusion_dates.append(two_limit_down_date)
    if far_above_yellow:
        risk_flags.append("离黄线偏远")
        downgrade_reasons.append("离黄线偏远")
    if risk_pct > 0.05:
        risk_flags.append(f"初始止损偏宽({risk_pct:.1%})")
        if risk_pct > 0.08:
            hard_exclude_reasons.append(f"初始止损不可写/过宽({risk_pct:.1%})")
        else:
            downgrade_reasons.append(f"初始止损偏宽({risk_pct:.1%})")
    if turnover_up_wave is not None and turnover_up_wave > 0.40:
        risk_flags.append(f"建仓波换手偏高({turnover_up_wave:.0%})")
        hard_exclude_reasons.append(f"建仓波累计换手>40%({turnover_up_wave:.0%})")
    if up_wave_gain is not None and up_wave_gain > 0.45:
        risk_flags.append(f"建仓波涨幅偏高({up_wave_gain:.0%})")
        hard_exclude_reasons.append(f"建仓波涨幅过高({up_wave_gain:.0%})")
    if not key_k_recent:
        downgrade_reasons.append("缺左侧异动/关键K")
    if not n_shape:
        downgrade_reasons.append("N型结构不足")
    if not shrink_ok:
        downgrade_reasons.append("右侧缩量不足")
    if not ideal_b1_day:
        downgrade_reasons.append("B1日涨跌幅/振幅不够温和")

    system_items = [
        (row["J"] <= 13 and wl > yl and row["Close"] > yl, "蓝色入口：B1基础条件成立"),
        (key_k_recent and n_shape and shrink_ok, "橙色证据：左侧异动+N型+缩量回踩"),
        (turnover_up_wave is None or turnover_up_wave <= 0.40, "建仓波换手<=40%"),
        (up_wave_gain is None or up_wave_gain <= 0.45, "建仓波涨幅不过热"),
        (s1_info["status"] != "S1未结构重置", "黄色应对：无未解除S1"),
        (didi_info["status"] == "无嘀嘀", "黄色应对：无嘀嘀/阶梯量"),
        (not two_limit_down_risk, "无两连跌停"),
        (risk_pct <= 0.08, "止损可写"),
    ]
    system_satisfied, system_missing = bool_text(system_items)

    score = 0
    score += 12 if row["J"] <= 13 else -20
    score += 8 if wl > yl else -12
    score += 8 if row["Close"] > yl else -12
    score += 10 if n_shape else -8
    score += 10 if key_k_recent else -6
    score += 10 if shrink_ok else -6
    score += 8 if near_yellow or near_white else -3
    score += 8 if ideal_b1_day else -4
    score += 6 if bool(row["yang_yin_ok"]) else 0
    score += 6 if risk_pct <= 0.05 else -8
    score += 4 if no_maxvol_yin and no_two_limit_down else -8
    score += 4 if turnover_up_wave is None or turnover_up_wave <= 0.40 else -8
    score += 4 if up_wave_gain is None or up_wave_gain <= 0.45 else -6
    score -= 30 if info.get("IsSTGP") == "1" or info.get("IsQuitGP") == "1" else 0
    score -= 10 if messy else 0

    hist = classify_historical_like(
        {
            "n_shape": n_shape,
            "key_k_recent": key_k_recent,
            "shrink_ok": shrink_ok,
            "near_yellow": near_yellow,
            "small_body": small_body,
            "long_consolidation": long_consolidation,
            "high_box": high_box,
            "red_fat_green_thin": red_fat_green_thin,
            "far_above_yellow": far_above_yellow,
            "strong_trend": strong_trend,
            "messy": messy,
            "big_yin_risk": big_yin_risk,
        }
    )

    if score >= 70 and risk_pct <= 0.05 and not risk_flags:
        grade = "A"
    elif score >= 62 and risk_pct <= 0.06:
        grade = "B"
    elif score >= 50:
        grade = "C"
    else:
        grade = "D"

    if hard_exclude_reasons:
        candidate_decision = "命中但排除"
    elif score >= 62 and risk_pct <= 0.06 and row["J"] <= 13 and wl > yl and row["Close"] > yl and key_k_recent and shrink_ok:
        candidate_decision = "可操作B1"
    elif row["J"] <= 13 and wl > yl and row["Close"] > yl:
        candidate_decision = "结构观察"
    else:
        candidate_decision = "反面学习样本"

    return {
        "formula_satisfied": formula_satisfied,
        "formula_missing": formula_missing,
        "z_satisfied": z_satisfied,
        "z_missing": z_missing,
        "system_satisfied": system_satisfied,
        "system_missing": system_missing,
        "hard_exclude_reasons": join_text(hard_exclude_reasons, "无硬排除"),
        "downgrade_reasons": join_text(downgrade_reasons, "无降级项"),
        "exclusion_evidence_date": join_text(sorted(set(exclusion_dates)), ""),
        "s1_status": str(s1_info["status"]),
        "s1_evidence": str(s1_info["evidence"]),
        "didi_status": str(didi_info["status"]),
        "didi_evidence": str(didi_info["evidence"]),
        "candidate_decision": candidate_decision,
        "historical_like": hist,
        "risk_flags": "；".join(risk_flags) if risk_flags else "暂无硬风险",
        "score": int(score),
        "grade": grade,
        "j_value": float(row["J"]),
        "pct_chg_signal": float(row["pct_chg"]),
        "amplitude_signal": float(row["amplitude"]),
        "wl": wl,
        "yl": yl,
    }


def build_operation(result: dict[str, Any]) -> str:
    parts = [
        f"{result['signal_date']} B1 信号成立",
        f"{result['entry_date']} 次日开盘 {result['entry_price']:.2f} 入场",
        f"初始止损 {result['stop_price']:.2f}，风险 {result['initial_risk_pct']:.2f}%",
    ]
    if result.get("partial_actions"):
        parts.append(result["partial_actions"])
    parts.append(f"{result['exit_date']} {result['exit_reason']}，最终收益 {result['total_return_pct']:.2f}%")
    return "；".join(parts)


def simulate_trade(
    code: str,
    info: dict[str, Any],
    df: pd.DataFrame,
    signal_date: str,
    max_hold_days: int,
    signal_source: str = "unknown",
) -> TradeResult | None:
    signal_ts = pd.Timestamp(datetime.strptime(signal_date, "%Y%m%d"))
    if signal_ts not in df.index:
        return None
    signal_pos = df.index.get_loc(signal_ts)
    if not isinstance(signal_pos, int) or signal_pos + 1 >= len(df):
        return None
    entry_pos = signal_pos + 1
    signal_row = df.iloc[signal_pos]
    entry_row = df.iloc[entry_pos]
    entry_price = float(entry_row["Open"])
    stop_price = round(float(signal_row["Low"]) * 0.995, 3)
    if entry_price <= 0 or stop_price <= 0:
        return None

    features = signal_features(code, info, df, signal_pos, entry_price, stop_price)
    features["signal_source"] = signal_source
    initial_risk = (entry_price - stop_price) / entry_price
    if initial_risk <= 0:
        return None

    position = 1.0
    realized_return = 0.0
    partial_actions: list[str] = []
    max_return = -999.0
    adverse_return = 999.0
    max_close = entry_price
    final_exit_price = float(entry_row["Close"])
    exit_date = str(df.index[entry_pos].date())
    exit_reason = "持有至回放结束"
    end_pos = min(len(df) - 1, entry_pos + max_hold_days - 1)

    if entry_price <= stop_price:
        final_exit_price = entry_price
        exit_reason = "次日开盘已低于止损，放弃交易"
        position = 0.0

    for pos in range(entry_pos, end_pos + 1):
        row = df.iloc[pos]
        date_text = str(df.index[pos].date())
        open_price = float(row["Open"])
        high_price = float(row["High"])
        low_price = float(row["Low"])
        close_price = float(row["Close"])
        final_exit_price = close_price
        exit_date = date_text
        max_close = max(max_close, close_price)
        max_return = max(max_return, high_price / entry_price - 1)
        adverse_return = min(adverse_return, low_price / entry_price - 1)
        days_held = pos - entry_pos + 1

        if position <= 0:
            break

        if open_price <= stop_price:
            final_exit_price = open_price
            realized_return += position * (final_exit_price / entry_price - 1)
            exit_reason = "开盘跳空破止损"
            position = 0.0
            break
        if low_price <= stop_price:
            final_exit_price = stop_price
            realized_return += position * (final_exit_price / entry_price - 1)
            exit_reason = "盘中触发初始止损"
            position = 0.0
            break

        if days_held >= 3 and max_close < entry_price * 1.03 and close_price <= entry_price * 1.01:
            final_exit_price = close_price
            realized_return += position * (final_exit_price / entry_price - 1)
            exit_reason = "3天未恢复上涨"
            position = 0.0
            break

        if max_close >= entry_price * 1.03 and close_price < entry_price:
            final_exit_price = close_price
            realized_return += position * (final_exit_price / entry_price - 1)
            exit_reason = "盈转亏离场"
            position = 0.0
            break

        day_pct = float(row["pct_chg"]) if not pd.isna(row["pct_chg"]) else 0.0
        if position > 0.5 and (close_price / entry_price - 1 >= 0.12 or (day_pct >= 0.04 and close_price / entry_price - 1 >= 0.06)):
            sell_qty = 0.5
            realized_return += sell_qty * (close_price / entry_price - 1)
            position -= sell_qty
            partial_actions.append(f"{date_text} 半仓放飞 {close_price:.2f}，半仓收益 {(close_price / entry_price - 1) * 100:.2f}%")

        if position > 0 and close_price / entry_price - 1 >= 0.25:
            final_exit_price = close_price
            realized_return += position * (final_exit_price / entry_price - 1)
            exit_reason = "达到25%目标止盈"
            position = 0.0
            break

        avg20 = df["Volume"].iloc[max(0, pos - 19) : pos + 1].mean()
        s1_like = bool(
            close_price / entry_price - 1 >= 0.08
            and row["Volume"] > 2.2 * avg20
            and (close_price <= open_price or close_price / high_price <= 0.96 or day_pct < 0.015)
        )
        if position > 0 and s1_like:
            if position > 0.5:
                sell_qty = 0.5
                realized_return += sell_qty * (close_price / entry_price - 1)
                position -= sell_qty
                partial_actions.append(f"{date_text} S1/放量滞涨先卖半仓 {close_price:.2f}，半仓收益 {(close_price / entry_price - 1) * 100:.2f}%")
            else:
                final_exit_price = close_price
                realized_return += position * (final_exit_price / entry_price - 1)
                exit_reason = "S1/放量滞涨清剩余仓位"
                position = 0.0
                break

        if position > 0 and days_held >= 3 and max_close >= entry_price * 1.05 and close_price < row["WL"]:
            final_exit_price = close_price
            realized_return += position * (final_exit_price / entry_price - 1)
            exit_reason = "跌破白线离场"
            position = 0.0
            break

        if position > 0 and pos > 0:
            prev = df.iloc[pos - 1]
            if close_price < row["YL"] and float(prev["Close"]) < float(prev["YL"]):
                final_exit_price = close_price
                realized_return += position * (final_exit_price / entry_price - 1)
                exit_reason = "连续两日收盘跌破黄线"
                position = 0.0
                break

    if position > 0:
        realized_return += position * (final_exit_price / entry_price - 1)
        exit_reason = "持有至最新/最大持有期"

    total_return = realized_return
    days_held = max(1, df.index.get_loc(pd.Timestamp(exit_date)) - entry_pos + 1) if pd.Timestamp(exit_date) in df.index else 1
    result = {
        "code": code,
        "name": str(info.get("Name", "")),
        "industry": str(info.get("rs_hyname", "")),
        "signal_source": str(features.get("signal_source", "unknown")),
        "candidate_decision": str(features["candidate_decision"]),
        "signal_date": str(signal_ts.date()),
        "entry_date": str(df.index[entry_pos].date()),
        "exit_date": exit_date,
        "b1_close": round(float(signal_row["Close"]), 3),
        "entry_price": round(entry_price, 3),
        "stop_price": round(stop_price, 3),
        "initial_risk_pct": pct(initial_risk),
        "final_exit_price": round(final_exit_price, 3),
        "total_return_pct": pct(total_return),
        "max_return_pct": pct(max_return),
        "adverse_return_pct": pct(adverse_return),
        "r_multiple": round(total_return / initial_risk, 2),
        "days_held": int(days_held),
        "exit_reason": exit_reason,
        "partial_actions": "；".join(partial_actions),
        "setup_score": int(features["score"]),
        "setup_grade": str(features["grade"]),
        "j_value": round(float(features["j_value"]), 2),
        "pct_chg_signal": pct(float(features["pct_chg_signal"])),
        "amplitude_signal": pct(float(features["amplitude_signal"])),
        "wl": round(float(features["wl"]), 3),
        "yl": round(float(features["yl"]), 3),
        "formula_satisfied": str(features["formula_satisfied"]),
        "formula_missing": str(features["formula_missing"]),
        "z_satisfied": str(features["z_satisfied"]),
        "z_missing": str(features["z_missing"]),
        "system_satisfied": str(features["system_satisfied"]),
        "system_missing": str(features["system_missing"]),
        "hard_exclude_reasons": str(features["hard_exclude_reasons"]),
        "downgrade_reasons": str(features["downgrade_reasons"]),
        "exclusion_evidence_date": str(features["exclusion_evidence_date"]),
        "s1_status": str(features["s1_status"]),
        "s1_evidence": str(features["s1_evidence"]),
        "didi_status": str(features["didi_status"]),
        "didi_evidence": str(features["didi_evidence"]),
        "historical_like": str(features["historical_like"]),
        "risk_flags": str(features["risk_flags"]),
    }
    result["operation"] = build_operation(result)
    return TradeResult(**result)


def dedupe_signal_dates(df: pd.DataFrame, dates: list[str], min_gap_days: int) -> list[str]:
    kept: list[str] = []
    last_pos = -9999
    for date in sorted(set(dates)):
        ts = pd.Timestamp(datetime.strptime(date, "%Y%m%d"))
        if ts not in df.index:
            continue
        pos = df.index.get_loc(ts)
        if not isinstance(pos, int):
            continue
        if pos - last_pos >= min_gap_days:
            kept.append(date)
            last_pos = pos
    return kept


def semantic_signal_dates(df: pd.DataFrame, start_date: str, end_date: str, min_gap_days: int) -> list[str]:
    start_ts = pd.Timestamp(datetime.strptime(start_date, "%Y%m%d"))
    end_ts = pd.Timestamp(datetime.strptime(end_date, "%Y%m%d"))
    raw_dates: list[str] = []
    for pos in range(120, len(df) - 1):
        ts = df.index[pos]
        if ts < start_ts or ts > end_ts:
            continue
        row = df.iloc[pos]
        if pd.isna(row["J"]) or pd.isna(row["WL"]) or pd.isna(row["YL"]):
            continue
        entry_price = float(df.iloc[pos + 1]["Open"])
        stop_price = float(row["Low"]) * 0.995
        if entry_price <= 0 or stop_price <= 0:
            continue
        initial_risk = (entry_price - stop_price) / entry_price
        if initial_risk <= 0 or initial_risk > 0.08:
            continue

        volume = df["Volume"]
        close = df["Close"]
        low = df["Low"]
        high = df["High"]
        zm1 = rolling_min_pairs(volume, pos)
        shrink_ok = bool(
            (volume.iloc[pos] < ema(volume, 34).iloc[pos])
            or (volume.iloc[pos] < volume.iloc[max(0, pos - 4) : pos + 1].max() * 0.5)
            or (not math.isnan(zm1) and volume.iloc[pos] <= zm1)
        )
        key_k_recent = bool((df["key_k"] | df["plry"]).iloc[max(0, pos - 27) : pos + 1].any())
        rise_from_60_low = float(close.iloc[pos] / low.iloc[max(0, pos - 59) : pos + 1].min() - 1)
        retreat_from_60_high = float(close.iloc[pos] / high.iloc[max(0, pos - 59) : pos + 1].max() - 1)
        n_shape = bool(close.iloc[pos] > row["YL"] and rise_from_60_low >= 0.10 and retreat_from_60_high <= -0.02)
        near_yellow = bool(abs(close.iloc[pos] / row["YL"] - 1) <= 0.07) if row["YL"] else False
        small_enough = bool(abs(float(row["pct_chg"])) <= 0.045 and float(row["amplitude"]) <= 0.075)
        trend_ok = bool(row["WL"] > row["YL"] and close.iloc[pos] > row["YL"])

        if row["J"] <= 13 and trend_ok and shrink_ok and key_k_recent and small_enough and (n_shape or near_yellow):
            raw_dates.append(ts.strftime("%Y%m%d"))
    return dedupe_signal_dates(df, raw_dates, min_gap_days=min_gap_days)


def collect_semantic_hits(
    market_data: dict[str, pd.DataFrame],
    stocks: list[str],
    start_date: str,
    end_date: str,
    min_gap_days: int,
) -> tuple[list[FormulaHit], dict[str, Any], dict[str, pd.DataFrame]]:
    hits: list[FormulaHit] = []
    enriched: dict[str, pd.DataFrame] = {}
    stats: dict[str, Any] = {
        "source": "semantic_b1",
        "start_date": start_date,
        "end_date": end_date,
        "stock_count": len(stocks),
        "started_at": now_iso(),
        "scanned_stock_count": 0,
        "candidate_stock_count": 0,
        "hit_count": 0,
    }
    for code in stocks:
        raw_df = dataframe_for_code(market_data, code)
        if raw_df is None:
            continue
        df = enrich_indicators(raw_df)
        stats["scanned_stock_count"] += 1
        dates = semantic_signal_dates(df, start_date=start_date, end_date=end_date, min_gap_days=min_gap_days)
        if not dates:
            continue
        enriched[code] = df
        stats["candidate_stock_count"] += 1
        for date in dates:
            hits.append(FormulaHit(code=code, signal_date=date, value="semantic_b1"))
    stats["hit_count"] = len(hits)
    stats["finished_at"] = now_iso()
    return hits, stats, enriched


def merge_hits(formula_hits: list[FormulaHit], semantic_hits: list[FormulaHit]) -> list[FormulaHit]:
    source_by_key: dict[tuple[str, str], set[str]] = {}
    for hit in formula_hits:
        source_by_key.setdefault((hit.code, hit.signal_date), set()).add("tdx_formula_b1")
    for hit in semantic_hits:
        source_by_key.setdefault((hit.code, hit.signal_date), set()).add("semantic_b1")
    merged: list[FormulaHit] = []
    for (code, signal_date), sources in sorted(source_by_key.items(), key=lambda item: (item[0][1], item[0][0])):
        source = "+".join(sorted(sources))
        merged.append(FormulaHit(code=code, signal_date=signal_date, value=source))
    return merged


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"trade_count": 0}
    returns = [float(r["total_return_pct"]) for r in rows]
    wins = [r for r in rows if float(r["total_return_pct"]) > 0]
    stopped = [r for r in rows if "止损" in str(r["exit_reason"])]
    return {
        "trade_count": len(rows),
        "win_count": len(wins),
        "loss_count": len(rows) - len(wins),
        "win_rate_pct": round(len(wins) / len(rows) * 100, 2),
        "avg_return_pct": round(sum(returns) / len(returns), 2),
        "median_return_pct": round(float(pd.Series(returns).median()), 2),
        "best_return_pct": round(max(returns), 2),
        "worst_return_pct": round(min(returns), 2),
        "stop_count": len(stopped),
    }


def learning_bucket(row: dict[str, Any]) -> str:
    if row["candidate_decision"] == "命中但排除":
        return "命中但排除"
    if "止损" in str(row["exit_reason"]):
        return "反例-止损"
    if row["exit_reason"] == "3天未恢复上涨":
        return "反例-没涨就走"
    if "盈转亏" in str(row["exit_reason"]):
        return "边界-盈转亏"
    if float(row["total_return_pct"]) >= 10:
        return "正例-强收益"
    if float(row["total_return_pct"]) > 0:
        return "正例-小赚或防守成功"
    return "边界-不亏或小亏"


def write_csv_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        if rows:
            writer.writerows(rows)


def build_terms_glossary(sample_map: dict[str, str]) -> list[dict[str, str]]:
    source_base = str(SOURCE_260415_DIR)
    wiki_base = str(SOURCE_WIKI_DIR)
    return [
        {
            "术语": "择时",
            "别名": "红色模块、总开关、活跃市值择时",
            "所属模块": "红色/择时",
            "定义": "交易前先判断市场环境能不能做、做多少、在哪个池子做。",
            "判断规则": "多头区间可围绕 B1/B2/B3 进攻，空头区间默认防守或小仓练手。",
            "选股用途": "决定 B1 候选是否进入当日计划池。",
            "交易动作": "过滤、仓位控制",
            "硬排除/降级/离场属性": "降级",
            "量化字段": "market_timing_status, active_market_value",
            "来源文件": f"{source_base}\\知行交易模块_操作版.md; {source_base}\\AI文稿_交易概念全量整理.md",
            "2026样例": sample_map.get("择时", ""),
        },
        {
            "术语": "B1",
            "别名": "建仓波买点、挖掘牛",
            "所属模块": "蓝色/买入入口",
            "定义": "体系第一类买点，核心是 J 值低位叠加趋势线和建仓结构。",
            "判断规则": "J<=13、白线>黄线、收盘>黄线，结合缩量回踩与左侧异动。",
            "选股用途": "作为公式/语义命中入口。",
            "交易动作": "买入入口",
            "硬排除/降级/离场属性": "入口",
            "量化字段": "j_value, wl, yl, formula_satisfied",
            "来源文件": f"{source_base}\\Obsidian_知行交易知识库\\20_概念\\买入模块\\B1.md; {wiki_base}\\03-买卖信号\\B1建仓波.md",
            "2026样例": sample_map.get("B1", ""),
        },
        {
            "术语": "建仓波",
            "别名": "建拉冲中的建、主力吸筹波",
            "所属模块": "橙色/判断依据",
            "定义": "资金在底部或趋势初段吸筹建仓的波段。",
            "判断规则": "建仓波涨幅通常约30%，累计换手超过40%视为废B1。",
            "选股用途": "判断 B1 是吸筹还是一波流出货。",
            "交易动作": "过滤、质量判断",
            "硬排除/降级/离场属性": "硬排除",
            "量化字段": "turnover_up_wave, up_wave_gain",
            "来源文件": f"{source_base}\\Obsidian_知行交易知识库\\20_概念\\判断依据\\建仓波.md; {wiki_base}\\03-买卖信号\\B1建仓波.md",
            "2026样例": sample_map.get("建仓波", ""),
        },
        {
            "术语": "N型结构",
            "别名": "上涨回踩再上、结构证据",
            "所属模块": "橙色/判断依据",
            "定义": "上涨后的回踩与再上结构，用于确认趋势和止损位置。",
            "判断规则": "从低点有一定涨幅，回落不破坏趋势，B1 日仍在黄线/白线有效区。",
            "选股用途": "没有 N 型的 B1 降为观察或反面样本。",
            "交易动作": "过滤、止损定位",
            "硬排除/降级/离场属性": "降级",
            "量化字段": "n_shape, rise_from_60_low, retreat_from_60_high",
            "来源文件": f"{source_base}\\Obsidian_知行交易知识库\\20_概念\\判断依据\\N型结构.md; {wiki_base}\\02-底层工具\\N型结构.md",
            "2026样例": sample_map.get("N型结构", ""),
        },
        {
            "术语": "S1",
            "别名": "顶部放量阴线、天量阴线、出货信号",
            "所属模块": "黄色/应对模块",
            "定义": "高位出现放巨量 K 线，尤其放量阴线，提示主力可能出货。",
            "判断规则": "看量不看色；出现后按风险处理。只有带量盖过 S1 高点、重新缩量回踩并形成干净结构才解除。",
            "选股用途": "B1 候选若存在 S1未结构重置，进入命中但排除。",
            "交易动作": "卖出、防守、硬排除",
            "硬排除/降级/离场属性": "硬排除/离场",
            "量化字段": "s1_status, s1_evidence, hard_exclude_reasons",
            "来源文件": f"{source_base}\\Obsidian_知行交易知识库\\20_概念\\应对模块\\S1.md; {wiki_base}\\03-买卖信号\\S1信号.md",
            "2026样例": sample_map.get("S1", ""),
        },
        {
            "术语": "顶部放量阴线",
            "别名": "高位放量阴线、28日天量阴线",
            "所属模块": "黄色/应对模块",
            "定义": "高位出现明显放量的阴线，是出货和风险释放的核心信号。",
            "判断规则": "高位、放量、阴线或滞涨三者叠加，优先按 S1 或嘀嘀风险处理。",
            "选股用途": "触发 hard_exclude_reasons 或 downgrade_reasons。",
            "交易动作": "卖出、防守",
            "硬排除/降级/离场属性": "硬排除",
            "量化字段": "no_maxvol_yin, s1_status",
            "来源文件": f"{source_base}\\Obsidian_知行交易知识库\\20_概念\\应对模块\\顶部放量阴线.md",
            "2026样例": sample_map.get("顶部放量阴线", ""),
        },
        {
            "术语": "嘀嘀",
            "别名": "滴滴、阶梯量出货、两阴确认",
            "所属模块": "黄色/应对模块",
            "定义": "高位阶梯量出货中的两根阴线信号，第二根确认时重点处理。",
            "判断规则": "必须是高位、两根阴线、第二根收盘低于第一根低点，量能没有明显缩掉。",
            "选股用途": "B1 候选若出现嘀嘀/阶梯量，命中但排除。",
            "交易动作": "卖出、防守",
            "硬排除/降级/离场属性": "硬排除/离场",
            "量化字段": "didi_status, didi_evidence",
            "来源文件": f"{source_base}\\Obsidian_知行交易知识库\\20_概念\\应对模块\\滴滴.md",
            "2026样例": sample_map.get("嘀嘀", ""),
        },
        {
            "术语": "没涨",
            "别名": "没涨就走、成本区腻歪",
            "所属模块": "黄色/应对模块",
            "定义": "买入后没有快速脱离成本区，说明市场没有证明交易正确。",
            "判断规则": "买后 3 天最大收盘收益不足 3%，且仍贴近成本区，主动离场。",
            "选股用途": "不是选股排除，而是收益验证中的离场规则。",
            "交易动作": "卖出、防守",
            "硬排除/降级/离场属性": "离场",
            "量化字段": "exit_reason=3天未恢复上涨",
            "来源文件": f"{source_base}\\Obsidian_知行交易知识库\\20_概念\\应对模块\\没涨.md",
            "2026样例": sample_map.get("没涨", ""),
        },
        {
            "术语": "盈转亏",
            "别名": "赢转亏、营转亏、盘转亏",
            "所属模块": "黄色/应对模块",
            "定义": "持仓从盈利状态转为亏损状态时的优先处理信号。",
            "判断规则": "曾有 3% 以上浮盈后跌回成本线下，按盈转亏离场。",
            "选股用途": "不是选股排除，而是收益验证中的离场规则。",
            "交易动作": "卖出、防守",
            "硬排除/降级/离场属性": "离场",
            "量化字段": "exit_reason=盈转亏离场",
            "来源文件": f"{source_base}\\Obsidian_知行交易知识库\\20_概念\\应对模块\\盈转亏.md",
            "2026样例": sample_map.get("盈转亏", ""),
        },
        {
            "术语": "白线",
            "别名": "牵牛绳、短期趋势线",
            "所属模块": "灰色/线位执行",
            "定义": "短期趋势牵引线，强势票通常不轻易跌破。",
            "判断规则": "B2/B3 或有浮盈后跌破白线，强度下降，应离场或减仓。",
            "选股用途": "B1 入口要求白线>黄线；离场用于跌破白线。",
            "交易动作": "入口确认、离场",
            "硬排除/降级/离场属性": "入口/离场",
            "量化字段": "wl, exit_reason=跌破白线离场",
            "来源文件": f"{source_base}\\知行交易模块_操作版.md; {wiki_base}\\02-底层工具\\白线黄线系统.md",
            "2026样例": sample_map.get("白线", ""),
        },
        {
            "术语": "黄线",
            "别名": "大哥成本线、中期多空线",
            "所属模块": "灰色/线位执行",
            "定义": "中期多空与主力成本参考线，黄线之上代表结构仍有交易价值。",
            "判断规则": "B1 入口要求收盘>黄线；连续两日收在黄线下方按破黄线离场。",
            "选股用途": "确认 B1 是否仍在可交易结构内。",
            "交易动作": "入口确认、离场",
            "硬排除/降级/离场属性": "入口/离场",
            "量化字段": "yl, exit_reason=连续两日收盘跌破黄线",
            "来源文件": f"{source_base}\\知行交易模块_操作版.md; {wiki_base}\\02-底层工具\\白线黄线系统.md",
            "2026样例": sample_map.get("黄线", ""),
        },
    ]


def build_sample_map(rows: list[dict[str, Any]]) -> dict[str, str]:
    sample: dict[str, str] = {}
    if rows:
        b1 = next((row for row in rows if row["candidate_decision"] == "可操作B1"), rows[0])
        sample["B1"] = f"{b1['code']} {b1['name']} {b1['signal_date']} {b1['candidate_decision']} 收益{b1['total_return_pct']}%"
        sample["白线"] = sample["B1"]
        sample["黄线"] = sample["B1"]
    for row in rows:
        text = f"{row['code']} {row['name']} {row['signal_date']} {row['candidate_decision']} 收益{row['total_return_pct']}%"
        if "S1未结构重置" in row.get("s1_status", "") and "S1" not in sample:
            sample["S1"] = text
        if "天量阴线" in row.get("hard_exclude_reasons", "") and "顶部放量阴线" not in sample:
            sample["顶部放量阴线"] = text
        if "嘀嘀" in row.get("didi_status", "") and "嘀嘀" not in sample:
            sample["嘀嘀"] = text
        if "3天未恢复上涨" == row.get("exit_reason") and "没涨" not in sample:
            sample["没涨"] = text
        if "盈转亏" in row.get("exit_reason", "") and "盈转亏" not in sample:
            sample["盈转亏"] = text
        if "建仓波" in row.get("hard_exclude_reasons", "") and "建仓波" not in sample:
            sample["建仓波"] = text
        if "N型" in row.get("system_satisfied", "") and "N型结构" not in sample:
            sample["N型结构"] = text
    return sample


def write_terms_glossary(out_dir: Path, rows: list[dict[str, Any]]) -> None:
    terms = build_terms_glossary(build_sample_map(rows))
    fields = ["术语", "别名", "所属模块", "定义", "判断规则", "选股用途", "交易动作", "硬排除/降级/离场属性", "量化字段", "来源文件", "2026样例"]
    write_csv_rows(out_dir / "terms_glossary.csv", terms, fields)
    lines = [
        "# 260415 核心交易术语表",
        "",
        "这份术语表把 `260415AI文稿` 的模块化概念落到 B1 选股、排除、离场和 2026 样例字段。出现冲突时，优先采用更利于风控和可回测的口径。",
        "",
        "| 术语 | 所属模块 | 定义 | 选股/交易用途 | 属性 | 量化字段 | 2026样例 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for term in terms:
        lines.append(
            f"| {term['术语']} | {term['所属模块']} | {term['定义']} | {term['选股用途']} | {term['硬排除/降级/离场属性']} | {term['量化字段']} | {term['2026样例']} |"
        )
    (out_dir / "terms_glossary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_outputs(
    out_dir: Path,
    hits: list[FormulaHit],
    trades: list[TradeResult],
    refresh_status: dict[str, Any],
    formula_stats: dict[str, Any],
    market_stats: dict[str, Any],
    semantic_stats: dict[str, Any],
    start_date: str,
    end_date: str,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    hit_rows = [asdict(hit) for hit in hits]
    trade_rows = [asdict(trade) for trade in trades]
    for row in trade_rows:
        row["month"] = row["signal_date"][:7]
        row["learning_bucket"] = learning_bucket(row)
    selected = [row for row in trade_rows if row["candidate_decision"] == "可操作B1"]
    excluded = [row for row in trade_rows if row["candidate_decision"] == "命中但排除"]
    observe = [row for row in trade_rows if row["candidate_decision"] == "结构观察"]
    negative = [row for row in trade_rows if row["candidate_decision"] == "反面学习样本"]
    selected_top = sorted(selected, key=lambda row: (-row["setup_score"], -row["r_multiple"], -row["total_return_pct"]))[:20]
    failed_quality = [
        row
        for row in trade_rows
        if row["setup_score"] >= 62 and row["initial_risk_pct"] <= 6 and row["total_return_pct"] <= 0
    ]
    failed_quality = sorted(failed_quality, key=lambda row: (row["total_return_pct"], -row["setup_score"]))[:8]
    all_summary = summarize_rows(trade_rows)
    selected_summary = summarize_rows(selected)
    high_quality_summary = summarize_rows([row for row in trade_rows if row["setup_score"] >= 62 and row["initial_risk_pct"] <= 6])
    decision_counts = dict(Counter(row["candidate_decision"] for row in trade_rows).most_common())
    source_counts = dict(Counter(row["signal_source"] for row in trade_rows).most_common())
    bucket_counts = dict(Counter(row["learning_bucket"] for row in trade_rows).most_common())

    (out_dir / "signal_hits.json").write_text(json.dumps(hit_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "formula_hits.json").write_text(json.dumps(hit_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "tdx_refresh_status.json").write_text(json.dumps(refresh_status, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "formula_stats.json").write_text(json.dumps(formula_stats, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "market_data_stats.json").write_text(json.dumps(market_stats, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "semantic_b1_stats.json").write_text(json.dumps(semantic_stats, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "trade_backtest.json").write_text(
        json.dumps(
            {
                "start_date": start_date,
                "end_date": end_date,
                "trade_count": len(trade_rows),
                "selected_count": len(selected),
                "excluded_count": len(excluded),
                "observe_count": len(observe),
                "negative_count": len(negative),
                "summary": all_summary,
                "selected_summary": selected_summary,
                "high_quality_summary": high_quality_summary,
                "decision_counts": decision_counts,
                "source_counts": source_counts,
                "bucket_counts": bucket_counts,
                "selected": selected,
                "excluded": excluded,
                "trades": trade_rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    fieldnames = list(trade_rows[0].keys()) if trade_rows else []
    write_csv_rows(out_dir / "trade_backtest.csv", trade_rows, fieldnames)
    write_csv_rows(out_dir / "all_formula_or_semantic_hits.csv", trade_rows, fieldnames)
    write_csv_rows(out_dir / "b1_2026_learning_samples.csv", trade_rows, fieldnames)
    write_csv_rows(out_dir / "b1_candidates_pass.csv", selected, fieldnames)
    write_csv_rows(out_dir / "b1_candidates_excluded.csv", excluded, fieldnames)
    write_csv_rows(out_dir / "b1_candidates_observe.csv", observe, fieldnames)
    write_csv_rows(out_dir / "b1_negative_learning_samples.csv", negative, fieldnames)
    write_csv_rows(out_dir / "selected_b1.csv", selected_top, fieldnames)
    write_terms_glossary(out_dir, trade_rows)

    official_hit_count = int(formula_stats.get("hit_count", 0) or 0)
    semantic_enabled = bool(semantic_stats.get("enabled"))
    semantic_used = bool(semantic_stats.get("used_for_backtest"))
    signal_source_text = "通达信公式 B1 + z 哥语义 B1 合并候选" if semantic_enabled else "通达信公式 B1"
    lines = [
        "# 260415 核心概念驱动的 B1 系统审计报告",
        "",
        f"- 回放区间：`{start_date}` 到 `{end_date}`；实际最新交易日以本地通达信日线为准。",
        f"- 盘后日线自动刷新：{'成功' if refresh_status.get('ok') else '失败/跳过'}；全市场 {refresh_status.get('stock_count', 0)} 只，批次 {refresh_status.get('ok_batch_count', 0)}/{refresh_status.get('batch_count', 0)}。",
        f"- 通达信公式 `B1` 历史命中：{official_hit_count} 条。",
    ]
    if semantic_enabled:
        lines.append(
            f"- z 哥语义 B1 复算：扫描 {semantic_stats.get('scanned_stock_count', 0)} 只，候选股票 {semantic_stats.get('candidate_stock_count', 0)} 只，候选信号 {semantic_stats.get('hit_count', 0)} 条。"
        )
    lines.extend(
        [
        f"- 本报告用于交易回放的信号来源：{signal_source_text}；去重后完成交易回放：{len(trade_rows)} 笔。",
        f"- 全部回放：胜率 {all_summary.get('win_rate_pct', 0)}%，平均收益 {all_summary.get('avg_return_pct', 0)}%，中位收益 {all_summary.get('median_return_pct', 0)}%，最好 {all_summary.get('best_return_pct', 0)}%，最差 {all_summary.get('worst_return_pct', 0)}%，止损 {all_summary.get('stop_count', 0)} 笔。",
        f"- 决策分布：{json.dumps(decision_counts, ensure_ascii=False)}。",
        f"- 来源分布：{json.dumps(source_counts, ensure_ascii=False)}。",
        f"- 学习分类：{json.dumps(bucket_counts, ensure_ascii=False)}。",
        f"- 可操作 B1：{selected_summary.get('trade_count', 0)} 笔，胜率 {selected_summary.get('win_rate_pct', 0)}%，平均收益 {selected_summary.get('avg_return_pct', 0)}%。",
        "",
        "## 系统口径",
        "",
        "- 红色择时：决定能不能做、做多少、在哪个池子做；当前脚本先留出字段，后续可接活跃市值。",
        "- 蓝色入口：B1 需要 J<=13、白线>黄线、收盘>黄线，并保留官方公式与语义命中来源。",
        "- 橙色证据：左侧异动/关键K、N型结构、缩量回踩、建仓波换手和涨幅不过热。",
        "- 黄色应对：S1未结构重置、嘀嘀/阶梯量、两连跌停、止损不可写等进入命中但排除。",
        "- 灰色执行：次日开盘入场，B1 K 线低点下 0.5% 止损，没涨、盈转亏、S1、破白线、破黄线负责离场验证。",
        "",
        "## 可操作 B1 样本",
        "",
        ]
    )
    if selected_top:
        lines.append("| 代码 | 名称 | 来源 | B1日 | 入场 | 止损 | 离场 | 收益 | 决策理由 | 完整操作 |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | ---: | --- | --- |")
        for row in selected_top:
            reason = f"{row['system_satisfied']}；{row['historical_like']}"
            lines.append(
                f"| {row['code']} | {row['name']} | {row['signal_source']} | {row['signal_date']} | {row['entry_date']} {row['entry_price']} | {row['stop_price']}({row['initial_risk_pct']}%) | {row['exit_date']} {row['exit_reason']} | {row['total_return_pct']}% | {reason} | {row['operation']} |"
            )
    else:
        lines.append("本轮没有进入可操作 B1 的样本。")

    lines.extend(["", "## 命中但排除样本", ""])
    if excluded:
        lines.append("| 代码 | 名称 | 来源 | B1日 | 排除原因 | 证据日期 | S1状态 | 不满足条件 | 回测收益 |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | ---: |")
        for row in excluded[:40]:
            lines.append(
                f"| {row['code']} | {row['name']} | {row['signal_source']} | {row['signal_date']} | {row['hard_exclude_reasons']} | {row['exclusion_evidence_date']} | {row['s1_status']} | {row['system_missing']} | {row['total_return_pct']}% |"
            )
    else:
        lines.append("本轮没有命中但排除样本。")

    lines.extend(
        [
            "",
            "## 高分但失败的样本",
            "",
            "这部分用于防止只看成功图。高分 B1 仍然会失败，失败时要按止损、3天不涨或盈转亏执行。",
            "",
        ]
    )
    if failed_quality:
        lines.append("| 代码 | 名称 | B1日 | 入场 | 止损 | 离场原因 | 收益 | 最大浮盈 | 最大逆行 | 失败说明 |")
        lines.append("| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | --- |")
        for row in failed_quality:
            lines.append(
                f"| {row['code']} | {row['name']} | {row['signal_date']} | {row['entry_date']} {row['entry_price']} | {row['stop_price']}({row['initial_risk_pct']}%) | {row['exit_reason']} | {row['total_return_pct']}% | {row['max_return_pct']}% | {row['adverse_return_pct']}% | {row['risk_flags']}；缺口：{row['z_missing']} |"
            )
    else:
        lines.append("本轮高质量过滤下没有亏损样本。")

    lines.extend(
        [
            "",
            "## 回放口径",
            "",
            "1. B1 信号日只确认公式和图形，不在当日追买。",
            "2. 次日开盘价作为入场价；如果开盘已经低于止损，视为放弃交易。",
            "3. 初始止损取 B1 信号 K 线最低点下方 0.5%；初始风险超过 5%-6% 的样本会被降权。",
            "4. 持仓前三天若没有恢复上涨，按 3 天不涨离场。",
            "5. 曾经有 3% 以上浮盈后跌回成本线以下，按盈转亏离场。",
            "6. 出现 12% 以上浮盈，或中阳加速并已有 6% 以上收益，先半仓放飞。",
            "7. 后续出现 25% 目标、S1/放量滞涨、跌破白线、连续两日跌破黄线，按规则离场。",
            "",
            "## 产物",
            "",
            f"- 全量命中与回放：`{out_dir / 'all_formula_or_semantic_hits.csv'}`",
            f"- 可操作 B1：`{out_dir / 'b1_candidates_pass.csv'}`",
            f"- 命中但排除：`{out_dir / 'b1_candidates_excluded.csv'}`",
            f"- 2026 学习样本：`{out_dir / 'b1_2026_learning_samples.csv'}`",
            f"- 术语表 CSV：`{out_dir / 'terms_glossary.csv'}`",
            f"- 术语表 MD：`{out_dir / 'terms_glossary.md'}`",
            f"- 官方公式统计：`{out_dir / 'formula_stats.json'}`",
            f"- 语义复算统计：`{out_dir / 'semantic_b1_stats.json'}`",
            f"- 刷新状态：`{out_dir / 'tdx_refresh_status.json'}`",
        ]
    )
    (out_dir / "b1_year_backtest_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out_dir / "b1_system_audit_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Backtest 2026 B1 signals with entry, stop, exit and returns.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--start-date", default=DEFAULT_START_DATE)
    parser.add_argument("--end-date", default=DEFAULT_END_DATE)
    parser.add_argument("--formula-return-count", type=int, default=180)
    parser.add_argument("--formula-batch-size", type=int, default=100)
    parser.add_argument("--market-count", type=int, default=320)
    parser.add_argument("--market-batch-size", type=int, default=100)
    parser.add_argument("--max-hold-days", type=int, default=40)
    parser.add_argument("--signal-gap-days", type=int, default=8)
    parser.add_argument("--skip-refresh", action="store_true")
    parser.add_argument("--semantic-scan", action="store_true", help="Scan semantic B1 candidates when TDX formula has few/no hits.")
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    from tqcenter import tq

    try:
        tq.initialize(str(DEFAULT_TQ_INIT_PATH))
        all_stocks = tq.get_stock_list(market="5")
        refresh_status = refresh_daily_kline(tq, all_stocks, enabled=not args.skip_refresh)
        hits, formula_stats = collect_formula_hits(
            tq,
            all_stocks,
            start_date=args.start_date,
            end_date=args.end_date,
            return_count=args.formula_return_count,
            batch_size=args.formula_batch_size,
        )
        hit_codes = sorted({hit.code for hit in hits})
        market_stocks = all_stocks if args.semantic_scan or not hit_codes else hit_codes
        infos = {code: tq.get_stock_info(code) for code in market_stocks}
        market_data, market_stats = collect_market_data(tq, market_stocks, count=args.market_count, batch_size=args.market_batch_size)
    finally:
        try:
            tq.close()
        except Exception:
            pass

    semantic_stats: dict[str, Any] = {"enabled": False}
    semantic_enriched: dict[str, pd.DataFrame] = {}
    formula_hits = hits
    if args.semantic_scan or not hits:
        semantic_hits, semantic_stats, semantic_enriched = collect_semantic_hits(
            market_data,
            market_stocks,
            start_date=args.start_date,
            end_date=args.end_date,
            min_gap_days=args.signal_gap_days,
        )
        hits = merge_hits(formula_hits, semantic_hits)
        semantic_stats["used_for_backtest"] = True
        semantic_stats["merged_hit_count"] = len(hits)
        semantic_stats["formula_hit_count"] = len(formula_hits)
        semantic_stats["enabled"] = True

    hits_by_code: dict[str, list[str]] = {}
    source_by_key: dict[tuple[str, str], str] = {}
    for hit in hits:
        hits_by_code.setdefault(hit.code, []).append(hit.signal_date)
        source_by_key[(hit.code, hit.signal_date)] = hit.value

    trades: list[TradeResult] = []
    for code, dates in hits_by_code.items():
        df = semantic_enriched.get(code)
        if df is None:
            raw_df = dataframe_for_code(market_data, code)
            if raw_df is None:
                continue
            df = enrich_indicators(raw_df)
        dates = dedupe_signal_dates(df, dates, min_gap_days=args.signal_gap_days)
        for date in dates:
            trade = simulate_trade(
                code,
                infos.get(code, {}),
                df,
                date,
                max_hold_days=args.max_hold_days,
                signal_source=source_by_key.get((code, date), "unknown"),
            )
            if trade:
                trades.append(trade)

    trades = sorted(trades, key=lambda item: (item.signal_date, item.code))
    write_outputs(
        args.out_dir,
        hits=hits,
        trades=trades,
        refresh_status=refresh_status,
        formula_stats=formula_stats,
        market_stats=market_stats,
        semantic_stats=semantic_stats,
        start_date=args.start_date,
        end_date=args.end_date,
    )
    final_hit_codes = sorted({hit.code for hit in hits})
    print(
        json.dumps(
            {
                "hit_count": len(hits),
                "hit_stock_count": len(final_hit_codes),
                "semantic_hit_count": semantic_stats.get("hit_count"),
                "trade_count": len(trades),
                "refresh_ok": refresh_status.get("ok"),
                "out_dir": str(args.out_dir),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
