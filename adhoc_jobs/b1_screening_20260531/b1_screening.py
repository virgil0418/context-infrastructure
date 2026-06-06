from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


TDX_SYS_PATH = Path(r"F:\new_tdx64\PYPlugins\sys")
DEFAULT_OUT_DIR = Path(r"D:\project\context-infrastructure\adhoc_jobs\b1_screening_20260531")
DEFAULT_TQ_INIT_PATH = Path(r"F:\z哥\b1_screening_tq.py")
MAX_REFRESH_BATCH_SIZE = 100
DEFAULT_REFRESH_BATCH_SIZE = 100


if str(TDX_SYS_PATH) not in sys.path:
    sys.path.insert(0, str(TDX_SYS_PATH))


@dataclass
class StockResult:
    code: str
    name: str
    industry: str
    category: str
    latest_date: str
    tdx_formula_b1_date: str
    tdx_formula_b1_value: str
    close: float
    pct_chg: float
    amplitude: float
    j_value: float
    wl: float
    yl: float
    wl_gt_yl: bool
    close_gt_yl: bool
    close_gt_65: bool
    yang_yin_ok: bool
    key_k_recent: bool
    plry_count_28: int
    shrink_ok: bool
    liquidity_ok: bool
    mv_ok: bool
    no_high_open_big_yin: bool
    no_maxvol_yin: bool
    no_two_limit_down: bool
    avg_amount_28_yi: float
    market_cap_yi: float
    rise_from_60_low: float
    retreat_from_60_high: float
    turnover_up_wave: float | None
    up_wave_gain: float | None
    near_support: str
    stop_loss: float
    formula_satisfied: str
    formula_missing: str
    z_satisfied: str
    z_missing: str
    historical_like: str
    risk_flags: str
    action: str
    score: int
    priority: str


def to_float(value: Any, default: float = math.nan) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def bool_text(items: list[tuple[bool, str]]) -> tuple[str, str]:
    yes = [label for ok, label in items if ok]
    no = [label for ok, label in items if not ok]
    return "；".join(yes), "；".join(no)


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


def calc_turnover_up_wave(df: pd.DataFrame, active_capital_wan_shares: float) -> tuple[float | None, float | None]:
    if len(df) < 20 or not active_capital_wan_shares or math.isnan(active_capital_wan_shares):
        return None, None
    recent = df.tail(60).copy()
    low_pos = int(recent["Low"].idxmin()) if recent.index.dtype.kind in "iu" else None
    if low_pos is None:
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


def classify_historical_like(row: dict[str, Any]) -> str:
    labels: list[str] = []
    if row["n_shape"] and row["key_k_recent"] and row["shrink_ok"] and row["near_yellow"] and row["small_body"]:
        labels.append("华纳药厂/娜娜图：放量启动后缩量回踩，接近黄线或碗沿")
    if row["n_shape"] and row["shrink_ok"] and row["long_consolidation"]:
        labels.append("国轩高科变量型：时间换空间，洗盘不极致但仍在结构内")
    if row["n_shape"] and row["high_box"] and row["red_fat_green_thin"]:
        labels.append("新瀚新材横盘压缩型：回调不深，高位箱体压缩")
    if row["far_above_yellow"] and row["shrink_ok"] and row["strong_trend"]:
        labels.append("昂利康高控盘激进型：强趋势里缩量，止损要盯白线")
    if row["messy"]:
        labels.append("反面像：犬牙交错/呼吸紊乱，和完美 B1 有距离")
    if row["big_yin_risk"]:
        labels.append("反面像：中银证券式大阴后 B1，容易是难做的一波流回落")
    return "；".join(labels) if labels else "暂未匹配到高置信历史模板"


def analyze_one(
    code: str,
    name: str,
    info: dict[str, Any],
    data: dict[str, pd.DataFrame],
    formula_probe: dict[str, dict[str, str]],
) -> StockResult | None:
    frames = {}
    for field in ("Open", "High", "Low", "Close", "Volume", "Amount"):
        df = data.get(field)
        if df is None or code not in df.columns:
            return None
        frames[field] = pd.to_numeric(df[code], errors="coerce")
    df = pd.DataFrame(frames).dropna()
    if len(df) < 120:
        return None

    c = df["Close"]
    o = df["Open"]
    h = df["High"]
    l = df["Low"]
    v = df["Volume"]
    amount = df["Amount"]

    wl = ema(ema(c, 10), 10)
    yl = (c.rolling(14).mean() + c.rolling(28).mean() + c.rolling(57).mean() + c.rolling(114).mean()) / 4
    bb = (c.rolling(3).mean() + c.rolling(6).mean() + c.rolling(12).mean() + c.rolling(24).mean()) / 4

    den = h.rolling(9).max() - l.rolling(9).min()
    rsv = (c - l.rolling(9).min()) / den.replace(0, math.nan) * 100
    rsv = rsv.fillna(50)
    k = sma_tdx(rsv, 3, 1)
    d = sma_tdx(k, 3, 1)
    j = 3 * k - 2 * d

    real_yang = (c > o) & ~(c < c.shift(1))
    real_yin = (c < o) & ~(c > c.shift(1))
    vol_yang_14 = (v * real_yang).rolling(14).sum()
    vol_yin_14 = (v * real_yin).rolling(14).sum()
    vol_yang_21 = (v * real_yang).rolling(21).sum()
    vol_yin_21 = (v * real_yin).rolling(21).sum()
    yang_yin_ok = ((vol_yang_21 > 1.5 * vol_yin_21) | (vol_yang_14 > 1.5 * vol_yin_14)).fillna(False)

    avg40 = v.rolling(40).mean()
    plry = (v > 1.8 * v.shift(1)) & (c > o) & (v > 1.5 * avg40)
    v40p = v.shift(1).rolling(40).mean()
    bd = (c > c.shift(1)) & (c >= o)
    bigv = v > 1.75 * v40p
    r55 = c.rolling(40).min() + 0.55 * (c.rolling(40).max() - c.rolling(40).min())
    r65 = c.rolling(40).min() + 0.65 * (c.rolling(40).max() - c.rolling(40).min())
    key_k = bd & bigv & (c > r55)
    sp = bd & (v > 2 * v40p) & (c > r65)

    idx = len(df) - 1
    latest = df.iloc[idx]
    prev = df.iloc[idx - 1]
    latest_date = str(df.index[idx].date()) if hasattr(df.index[idx], "date") else str(df.index[idx])

    zm1 = rolling_min_pairs(v, idx)
    shrink_ok = bool((v.iloc[idx] < ema(v, 34).iloc[idx]) or (v.iloc[idx] < v.tail(5).max() * 0.5) or (not math.isnan(zm1) and v.iloc[idx] <= zm1))
    avg_amount_28_yi = float(amount.tail(28).mean() / 10000)
    active_capital = to_float(info.get("ActiveCapital"))
    market_cap_yi = float(c.iloc[idx] * active_capital * 100 / 100000000) if not math.isnan(active_capital) else math.nan
    liquidity_ok = avg_amount_28_yi >= 0.005
    mv_ok = market_cap_yi >= 50 if not math.isnan(market_cap_yi) else False
    top15_open = o >= (o.rolling(28).min() + 0.925 * (o.rolling(28).max() - o.rolling(28).min()))
    fd15 = (c < c.shift(1)) & (c <= o) & (v >= 1.15 * v.shift(1))
    no_high_open_big_yin = not bool((top15_open & fd15).tail(28).any())
    no_maxvol_yin = not bool(((v == v.tail(28).max()) & real_yin).tail(28).any())
    ld = (c / c.shift(1) - 1) <= -0.098
    no_two_limit_down = not bool((ld & ld.shift(1)).tail(24).any())

    pct_chg = float(c.iloc[idx] / c.iloc[idx - 1] - 1)
    amplitude = float((h.iloc[idx] - l.iloc[idx]) / c.iloc[idx - 1])
    rise_from_60_low = float(c.iloc[idx] / l.tail(60).min() - 1)
    retreat_from_60_high = float(c.iloc[idx] / h.tail(60).max() - 1)
    turnover_up_wave, up_wave_gain = calc_turnover_up_wave(df, active_capital)

    last_j = float(j.iloc[idx])
    last_wl = float(wl.iloc[idx])
    last_yl = float(yl.iloc[idx])
    close_gt_65 = bool(c.iloc[idx] > r65.iloc[idx])
    near_yellow = bool(abs(c.iloc[idx] / last_yl - 1) <= 0.06) if last_yl else False
    near_white = bool(abs(c.iloc[idx] / last_wl - 1) <= 0.04) if last_wl else False
    if near_yellow:
        near_support = "靠近黄线"
    elif near_white:
        near_support = "靠近白线"
    elif c.iloc[idx] > last_yl:
        near_support = "黄线上方但距离偏远"
    else:
        near_support = "黄线下方"

    n_shape = bool(c.iloc[idx] > last_yl and rise_from_60_low >= 0.12 and retreat_from_60_high <= -0.03)
    key_k_recent = bool((key_k | sp | plry).tail(28).any())
    plry_count_28 = int(plry.tail(28).sum())
    small_body = bool(abs(c.iloc[idx] / o.iloc[idx] - 1) <= 0.025 and amplitude <= 0.055)
    long_consolidation = bool((h.tail(15).max() / l.tail(15).min() - 1) <= 0.18)
    high_box = bool(retreat_from_60_high > -0.12 and rise_from_60_low > 0.18)
    red_fat_green_thin = bool((v.tail(21)[real_yang.tail(21)].mean() or 0) >= (v.tail(21)[real_yin.tail(21)].mean() or 0))
    strong_trend = bool(wl.iloc[idx] > yl.iloc[idx] and wl.iloc[idx] > wl.iloc[idx - 5] and yl.iloc[idx] >= yl.iloc[idx - 5])
    far_above_yellow = bool(c.iloc[idx] / last_yl - 1 > 0.08) if last_yl else False
    messy = bool(amplitude > 0.08 or ((h.tail(8) - l.tail(8)) / c.shift(1).tail(8)).mean() > 0.065)
    big_yin_risk = bool(((c < c.shift(1)) & (c <= o) & (v > v.rolling(20).mean() * 1.5)).tail(10).any())

    formula_items = [
        (last_j <= 13, f"J<=13({last_j:.1f})"),
        (bool(wl.iloc[idx] > yl.iloc[idx]), "白线>黄线"),
        (bool(c.iloc[idx] > yl.iloc[idx]), "收盘>黄线"),
        (yang_yin_ok.iloc[idx].item() if hasattr(yang_yin_ok.iloc[idx], "item") else bool(yang_yin_ok.iloc[idx]), "14/21日阳量强于阴量"),
        (key_k_recent, "28日内有关键K/倍量柱"),
        (shrink_ok, "当前缩量/地量"),
        (liquidity_ok, f"28日均额>{0.005:.3f}亿"),
        (mv_ok, "市值>50亿"),
        (no_high_open_big_yin, "无高位开盘放量阴线"),
        (no_maxvol_yin, "无28日天量阴线"),
        (no_two_limit_down, "24日无两连跌停"),
    ]
    formula_satisfied, formula_missing = bool_text(formula_items)

    z_items = [
        (n_shape, "N型/上涨后回调"),
        (key_k_recent, "左侧有异动或关键K"),
        (shrink_ok, "右侧缩量"),
        (near_yellow or near_white, near_support),
        (small_body, "B1日波动温和"),
        (turnover_up_wave is None or turnover_up_wave <= 0.40, "建仓波换手未明显过热"),
        (up_wave_gain is None or up_wave_gain <= 0.45, "建仓波涨幅未明显过高"),
    ]
    z_satisfied, z_missing = bool_text(z_items)

    risk_flags: list[str] = []
    if info.get("IsSTGP") == "1":
        risk_flags.append("ST")
    if info.get("IsQuitGP") == "1":
        risk_flags.append("退市风险")
    if messy:
        risk_flags.append("K线/呼吸偏乱")
    if big_yin_risk:
        risk_flags.append("近期放量阴线")
    if far_above_yellow:
        risk_flags.append("离黄线偏远")
    if turnover_up_wave is not None and turnover_up_wave > 0.40:
        risk_flags.append(f"建仓波换手偏高({turnover_up_wave:.0%})")
    if up_wave_gain is not None and up_wave_gain > 0.45:
        risk_flags.append(f"建仓波涨幅偏高({up_wave_gain:.0%})")

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

    score = 0
    score += 10 if last_j <= 13 else 0
    score += 8 if wl.iloc[idx] > yl.iloc[idx] else -10
    score += 8 if c.iloc[idx] > yl.iloc[idx] else -12
    score += 8 if yang_yin_ok.iloc[idx] else 0
    score += 10 if key_k_recent else -6
    score += 10 if shrink_ok else -8
    score += 10 if n_shape else -10
    score += 8 if near_yellow or near_white else -4
    score += 6 if small_body else -4
    score += 4 if no_high_open_big_yin and no_maxvol_yin else -8
    score += 4 if turnover_up_wave is None or turnover_up_wave <= 0.40 else -8
    score += 4 if up_wave_gain is None or up_wave_gain <= 0.45 else -6
    if info.get("IsSTGP") == "1" or info.get("IsQuitGP") == "1":
        score -= 30

    strict_b1 = bool(last_j <= 13 and wl.iloc[idx] > yl.iloc[idx] and c.iloc[idx] > yl.iloc[idx] and shrink_ok)
    hard_risk = bool(info.get("IsSTGP") == "1" or info.get("IsQuitGP") == "1" or messy or (turnover_up_wave is not None and turnover_up_wave > 0.8))
    structure_watch = bool((not strict_b1) and score >= 45 and wl.iloc[idx] > yl.iloc[idx] and c.iloc[idx] > yl.iloc[idx] and n_shape)

    if strict_b1 and score >= 62 and not hard_risk:
        category = "严格B1候选"
        priority = "A"
        action = "候选：严格 B1 成立，只等次日量比/分时确认，计划内小仓试错"
    elif strict_b1:
        category = "严格B1低质"
        priority = "C"
        action = "暂不做：当日 B1 条件成立，但图形质量或风险项不达标"
    elif structure_watch and score >= 62:
        category = "结构观察A"
        priority = "A"
        action = "观察：结构像历史强图，但最新 J 值不在 B1 低位，不能按当日 B1 买"
    elif structure_watch:
        category = "结构观察B"
        priority = "B"
        action = "观察：有部分结构条件，需要重新等 J 低位或次日强确认"
    else:
        category = "淘汰"
        priority = "C"
        action = "淘汰/暂不做：公式入池不等于可交易"

    stop_candidates = [float(l.iloc[idx])]
    if last_yl and c.iloc[idx] > last_yl:
        stop_candidates.append(last_yl * 0.985)
    if last_wl and c.iloc[idx] > last_wl:
        stop_candidates.append(last_wl * 0.985)
    stop_loss = min(stop_candidates)

    return StockResult(
        code=code,
        name=name,
        industry=str(info.get("rs_hyname", "")),
        category=category,
        latest_date=latest_date,
        tdx_formula_b1_date=formula_probe.get(code, {}).get("date", ""),
        tdx_formula_b1_value=formula_probe.get(code, {}).get("value", ""),
        close=round(float(c.iloc[idx]), 3),
        pct_chg=round(pct_chg, 4),
        amplitude=round(amplitude, 4),
        j_value=round(last_j, 2),
        wl=round(last_wl, 3),
        yl=round(last_yl, 3),
        wl_gt_yl=bool(wl.iloc[idx] > yl.iloc[idx]),
        close_gt_yl=bool(c.iloc[idx] > yl.iloc[idx]),
        close_gt_65=close_gt_65,
        yang_yin_ok=bool(yang_yin_ok.iloc[idx]),
        key_k_recent=key_k_recent,
        plry_count_28=plry_count_28,
        shrink_ok=shrink_ok,
        liquidity_ok=liquidity_ok,
        mv_ok=mv_ok,
        no_high_open_big_yin=no_high_open_big_yin,
        no_maxvol_yin=no_maxvol_yin,
        no_two_limit_down=no_two_limit_down,
        avg_amount_28_yi=round(avg_amount_28_yi, 3),
        market_cap_yi=round(market_cap_yi, 2) if not math.isnan(market_cap_yi) else math.nan,
        rise_from_60_low=round(rise_from_60_low, 4),
        retreat_from_60_high=round(retreat_from_60_high, 4),
        turnover_up_wave=round(turnover_up_wave, 4) if turnover_up_wave is not None else None,
        up_wave_gain=round(up_wave_gain, 4) if up_wave_gain is not None else None,
        near_support=near_support,
        stop_loss=round(stop_loss, 3),
        formula_satisfied=formula_satisfied,
        formula_missing=formula_missing,
        z_satisfied=z_satisfied,
        z_missing=z_missing,
        historical_like=hist,
        risk_flags="；".join(risk_flags) if risk_flags else "暂无硬风险，但仍需次日确认",
        action=action,
        score=int(score),
        priority=priority,
    )


def summarize_formula_result(res: dict[str, Any], stocks: list[str]) -> dict[str, Any]:
    hits: list[dict[str, str]] = []
    zeros = 0
    nulls = 0
    for code in stocks:
        xg = (res.get(code, {}) or {}).get("XG") or []
        latest = xg[-1] if xg else {}
        value = latest.get("Value")
        date = latest.get("Date")
        if value in (None, ""):
            nulls += 1
        elif str(value) in ("0", "0.0"):
            zeros += 1
        else:
            hits.append({"code": code, "date": str(date or ""), "value": str(value)})
    return {
        "stock_count": len(stocks),
        "error_id": str(res.get("ErrorId", "")),
        "hit_count": len(hits),
        "zero_count": zeros,
        "null_count": nulls,
        "hits": hits,
    }


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


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


def refresh_daily_kline(tq: Any, stocks: list[str], batch_size: int, enabled: bool) -> dict[str, Any]:
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
    if not stocks:
        return {
            "enabled": True,
            "period": "1d",
            "stock_count": 0,
            "started_at": now_iso(),
            "finished_at": now_iso(),
            "ok": False,
            "message": "empty stock list",
            "batches": [],
        }

    requested_batch_size = max(1, batch_size)
    safe_batch_size = min(requested_batch_size, MAX_REFRESH_BATCH_SIZE)
    batches = iter_batches(stocks, safe_batch_size)
    summary: dict[str, Any] = {
        "enabled": True,
        "period": "1d",
        "stock_count": len(stocks),
        "requested_batch_size": requested_batch_size,
        "batch_size": safe_batch_size,
        "max_batch_size": MAX_REFRESH_BATCH_SIZE,
        "batch_count": len(batches),
        "started_at": now_iso(),
        "batches": [],
    }
    if safe_batch_size < requested_batch_size:
        summary["message"] = f"refresh_kline allows at most {MAX_REFRESH_BATCH_SIZE} stocks per request; batch size clamped"
    for index, batch in enumerate(batches, start=1):
        batch_info: dict[str, Any] = {
            "batch": index,
            "count": len(batch),
            "first": batch[0],
            "last": batch[-1],
            "started_at": now_iso(),
        }
        try:
            raw = tq.refresh_kline(stock_list=batch, period="1d")
            parsed = parse_tdx_json(raw)
            error_id = parsed.get("ErrorId")
            batch_info.update(
                {
                    "finished_at": now_iso(),
                    "ok": str(error_id) == "0",
                    "error_id": "" if error_id is None else str(error_id),
                    "error": str(parsed.get("Error", "")),
                    "raw": parsed.get("raw", raw),
                }
            )
        except Exception as exc:
            batch_info.update({"finished_at": now_iso(), "ok": False, "error": repr(exc)})
        summary["batches"].append(batch_info)

    ok_count = sum(1 for batch in summary["batches"] if batch.get("ok"))
    summary["ok_batch_count"] = ok_count
    summary["failed_batch_count"] = len(summary["batches"]) - ok_count
    summary["ok"] = bool(summary["batches"]) and ok_count == len(summary["batches"])
    summary["finished_at"] = now_iso()
    return summary


def format_refresh_summary(refresh_status: dict[str, Any]) -> str:
    if not refresh_status.get("enabled"):
        return "跳过自动刷新（--skip-refresh）"
    batch_count = refresh_status.get("batch_count", len(refresh_status.get("batches", [])))
    ok_count = refresh_status.get("ok_batch_count", 0)
    stock_count = refresh_status.get("stock_count", 0)
    if refresh_status.get("ok"):
        status = "成功"
    else:
        status = "有失败，需查看 tdx_refresh_status.json"
    return f"{status}；1d K线 {stock_count} 只，批次 {ok_count}/{batch_count}"


def load_tdx_data(
    count: int,
    refresh: bool,
    refresh_batch_size: int,
) -> tuple[
    list[str],
    dict[str, dict[str, Any]],
    dict[str, pd.DataFrame],
    dict[str, dict[str, str]],
    dict[str, Any],
    dict[str, Any],
]:
    from tqcenter import tq

    try:
        tq.initialize(str(DEFAULT_TQ_INIT_PATH))
        all_stocks = tq.get_stock_list(market="5")
        refresh_status = refresh_daily_kline(tq, all_stocks, refresh_batch_size, enabled=refresh)
        pool = tq.get_stock_list_in_sector("B1", block_type=1)
        infos: dict[str, dict[str, Any]] = {}
        for code in pool:
            infos[code] = tq.get_stock_info(code)
        data = tq.get_market_data(
            field_list=["Open", "High", "Low", "Close", "Volume", "Amount"],
            stock_list=pool,
            period="1d",
            count=count,
            dividend_type="front",
        )
        formula_probe: dict[str, dict[str, str]] = {}
        formula_all_summary: dict[str, Any] = {}
        try:
            formula_res = tq.formula_process_mul_xg(
                formula_name="B1",
                return_count=1,
                return_date=True,
                stock_list=pool,
                stock_period="1d",
                count=5,
            )
            for code in pool:
                xg = (formula_res.get(code, {}) or {}).get("XG") or []
                latest = xg[-1] if xg else {}
                value = latest.get("Value")
                formula_probe[code] = {
                    "date": str(latest.get("Date", "")),
                    "value": "" if value is None else str(value),
                }
        except Exception as exc:
            formula_probe["_error"] = {"date": "", "value": repr(exc)}
        try:
            formula_all_res = tq.formula_process_mul_xg(
                formula_name="B1",
                return_count=1,
                return_date=True,
                stock_list=all_stocks,
                stock_period="1d",
                count=1,
            )
            formula_all_summary = summarize_formula_result(formula_all_res, all_stocks)
        except Exception as exc:
            formula_all_summary = {"error": repr(exc), "stock_count": 0, "hit_count": 0, "hits": []}
        return pool, infos, data, formula_probe, formula_all_summary, refresh_status
    finally:
        try:
            tq.close()
        except Exception:
            pass


def write_outputs(
    results: list[StockResult],
    out_dir: Path,
    pool: list[str],
    formula_all_summary: dict[str, Any],
    refresh_status: dict[str, Any],
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = [asdict(r) for r in sorted(results, key=lambda x: (-x.score, x.code))]

    with (out_dir / "b1_screening_results.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
        if rows:
            writer.writeheader()
            writer.writerows(rows)

    (out_dir / "b1_screening_results.json").write_text(
        json.dumps({"pool_size": len(pool), "result_size": len(rows), "results": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    strict = [r for r in rows if r["category"] == "严格B1候选"]
    strict_low = [r for r in rows if r["category"] == "严格B1低质"]
    structure_a = [r for r in rows if r["category"] == "结构观察A"]
    structure_b = [r for r in rows if r["category"] == "结构观察B"]
    formula_positive = [r for r in rows if r["tdx_formula_b1_value"] not in ("", "0", "0.0")]
    formula_date = rows[0]["tdx_formula_b1_date"] if rows else ""
    lines = [
        "# B1 二次细选报告",
        "",
        f"- 数据源：通达信自定义板块 `B1`，共 {len(pool)} 只；成功分析 {len(rows)} 只。",
        f"- 盘后日线自动刷新：{format_refresh_summary(refresh_status)}。",
        f"- 最新交易日：{rows[0]['latest_date'] if rows else '未知'}。",
        f"- 通达信公式 `B1` 全市场复核：{formula_all_summary.get('stock_count', 0)} 只中命中 {formula_all_summary.get('hit_count', 0)} 只。",
        f"- 通达信公式 `B1` 复核：{formula_date or '未知日期'} 在当前板块内命中 {len(formula_positive)} 只。",
        "- 关键边界：自定义板块 `B1` 不等同于最新交易日公式重新选股结果；本报告把二者分开处理。",
        "- 解释口径：通达信公式负责初筛；本报告用本地日线复算关键条件，并叠加 z 哥 B1 完美图/建仓波语义评分。",
        "",
        "## 严格 B1 候选",
        "",
    ]
    if strict:
        lines.append("| 代码 | 名称 | 行业 | 分数 | 满足条件 | 不满足/风险 | 历史相似 | 动作 |")
        lines.append("| --- | --- | --- | ---: | --- | --- | --- | --- |")
        for r in strict:
            lines.append(
                f"| {r['code']} | {r['name']} | {r['industry']} | {r['score']} | {r['z_satisfied']} | {r['z_missing']}；{r['risk_flags']} | {r['historical_like']} | {r['action']} |"
            )
    else:
        lines.append("本轮没有高质量严格 B1 候选。")

    lines.extend(["", "## 严格 B1 低质", ""])
    if strict_low:
        lines.append("| 代码 | 名称 | 行业 | 分数 | 满足条件 | 不满足/风险 | 历史相似 | 动作 |")
        lines.append("| --- | --- | --- | ---: | --- | --- | --- | --- |")
        for r in strict_low:
            lines.append(
                f"| {r['code']} | {r['name']} | {r['industry']} | {r['score']} | {r['z_satisfied']} | {r['z_missing']}；{r['risk_flags']} | {r['historical_like']} | {r['action']} |"
            )
    else:
        lines.append("本轮没有严格 B1 但质量不足的个股。")

    lines.extend(["", "## 结构观察 A", ""])
    if structure_a:
        lines.append("| 代码 | 名称 | 行业 | 分数 | 满足条件 | 不满足/风险 | 历史相似 |")
        lines.append("| --- | --- | --- | ---: | --- | --- | --- |")
        for r in structure_a:
            lines.append(
                f"| {r['code']} | {r['name']} | {r['industry']} | {r['score']} | {r['z_satisfied']} | {r['z_missing']}；{r['risk_flags']} | {r['historical_like']} |"
            )
    else:
        lines.append("本轮没有结构观察 A。")

    lines.extend(["", "## 结构观察 B", ""])
    if structure_b:
        lines.append("| 代码 | 名称 | 行业 | 分数 | 满足条件 | 不满足/风险 | 历史相似 |")
        lines.append("| --- | --- | --- | ---: | --- | --- | --- |")
        for r in structure_b[:20]:
            lines.append(
                f"| {r['code']} | {r['name']} | {r['industry']} | {r['score']} | {r['z_satisfied']} | {r['z_missing']}；{r['risk_flags']} | {r['historical_like']} |"
            )
    else:
        lines.append("本轮没有结构观察 B。")

    lines.extend(["", "## 全量条件表", ""])
    lines.append("| 代码 | 名称 | 分类 | 优先级 | 分数 | TDX公式B1 | 公式满足 | 公式未满足 | z 哥条件满足 | z 哥条件缺口 | 止损参考 |")
    lines.append("| --- | --- | --- | --- | ---: | --- | --- | --- | --- | --- | ---: |")
    for r in rows:
        lines.append(
            f"| {r['code']} | {r['name']} | {r['category']} | {r['priority']} | {r['score']} | {r['tdx_formula_b1_value'] or '空'} | {r['formula_satisfied']} | {r['formula_missing']} | {r['z_satisfied']} | {r['z_missing']} | {r['stop_loss']} |"
        )

    (out_dir / "b1_screening_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Read TDX B1 sector and produce explainable B1 screening report.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--count", type=int, default=180)
    parser.add_argument("--skip-refresh", action="store_true", help="Skip automatic 1d K-line refresh before screening.")
    parser.add_argument("--refresh-batch-size", type=int, default=DEFAULT_REFRESH_BATCH_SIZE)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    pool, infos, data, formula_probe, formula_all_summary, refresh_status = load_tdx_data(
        args.count,
        refresh=not args.skip_refresh,
        refresh_batch_size=args.refresh_batch_size,
    )
    (args.out_dir / "tdx_refresh_status.json").write_text(
        json.dumps(refresh_status, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (args.out_dir / "tdx_formula_b1_probe.json").write_text(
        json.dumps(formula_probe, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (args.out_dir / "tdx_formula_b1_all_market_summary.json").write_text(
        json.dumps(formula_all_summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    results: list[StockResult] = []
    for code in pool:
        info = infos.get(code, {})
        name = str(info.get("Name", ""))
        result = analyze_one(code, name, info, data, formula_probe)
        if result:
            results.append(result)

    write_outputs(results, args.out_dir, pool, formula_all_summary, refresh_status)
    print(
        json.dumps(
            {
                "pool_size": len(pool),
                "result_size": len(results),
                "refresh_ok": refresh_status.get("ok"),
                "out_dir": str(args.out_dir),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
