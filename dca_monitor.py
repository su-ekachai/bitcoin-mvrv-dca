"""Daily Bitcoin MVRV/STH-MVRV DCA signal monitor. Stdlib only."""

from __future__ import annotations

import html
import http.client
import json
import logging
import math
import os
import sys
import time
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import cast

MVRV_TIERS: tuple[tuple[float, float, str], ...] = (
    (1.0, 2.0, "very_cheap"),
    (1.5, 1.5, "cheap"),
    (2.0, 1.0, "normal"),
    (2.5, 0.5, "expensive"),
    (math.inf, 0.0, "very_expensive"),
)
STH_TIERS: tuple[tuple[float, float], ...] = ((0.9, 1.5), (1.0, 1.25), (1.1, 1.0), (math.inf, 0.5))

TIER_LABELS = {
    "very_cheap": "STRONG BUY",
    "cheap": "BUY MORE",
    "normal": "DCA NORMAL",
    "expensive": "REDUCE",
    "very_expensive": "STOP",
}
TIER_COLORS = {
    "very_cheap": 0x1E8449,
    "cheap": 0x2ECC71,
    "normal": 0x3498DB,
    "expensive": 0xE67E22,
    "very_expensive": 0xE74C3C,
}
ERROR_COLOR = 0x95A5A6
MVRV_ZONE = {
    "very_cheap": "very cheap zone",
    "cheap": "cheap zone",
    "normal": "normal zone",
    "expensive": "expensive zone",
    "very_expensive": "very expensive zone",
}


@dataclass(frozen=True)
class Signal:
    mvrv: float
    sth_mvrv: float
    mvrv_tier: str
    mvrv_mult: float
    sth_mult: float
    multiplier: float
    stop: bool


def classify(mvrv: float, sth_mvrv: float) -> Signal:
    mvrv_mult, mvrv_tier = next((m, t) for ub, m, t in MVRV_TIERS if mvrv < ub)
    sth_mult = next(m for ub, m in STH_TIERS if sth_mvrv < ub)
    stop = mvrv_mult == 0.0
    return Signal(
        mvrv=mvrv,
        sth_mvrv=sth_mvrv,
        mvrv_tier=mvrv_tier,
        mvrv_mult=mvrv_mult,
        sth_mult=sth_mult,
        multiplier=0.0 if stop else mvrv_mult * sth_mult,
        stop=stop,
    )


@dataclass(frozen=True)
class MarketData:
    mvrv_history: list[float]
    mvrv: float
    prev_mvrv: float
    sth_mvrv: float
    prev_sth: float
    price: float
    data_date: str


def percentile(history: list[float], value: float) -> float:
    return 100.0 * sum(1 for v in history if v <= value) / len(history)


def _series(raw: list[dict], key: str) -> list[float]:
    return [float(r[key]) for r in raw]


@dataclass(frozen=True)
class Context:
    data_date: str
    price: float
    base_amount: float
    currency: str
    amount: float
    mvrv_percentile: float
    tier_changed: bool
    prev_tier: str


def _sth_zone(sth: float) -> str:
    if sth < 0.9:
        return "strong buy zone"
    if sth < 1.0:
        return "confirms buy"
    if sth < 1.1:
        return "neutral"
    return "caution"


def _headline(signal: Signal, ctx: Context) -> str:
    label = TIER_LABELS[signal.mvrv_tier]
    if signal.stop:
        return f"{label} — no buy today (0× base)"
    return f"{label} — {ctx.amount:,.2f} {ctx.currency} today ({signal.multiplier:.2f}× base)"


def _reasons(signal: Signal) -> str:
    zone = MVRV_ZONE[signal.mvrv_tier]
    return (
        f"MVRV {signal.mvrv:.2f} · {zone} → ×{signal.mvrv_mult:g}\n"
        f"STH-MVRV {signal.sth_mvrv:.2f} · {_sth_zone(signal.sth_mvrv)} → ×{signal.sth_mult:g}"
    )


def build_discord(signal: Signal, ctx: Context) -> dict:
    tier_change = f"from {ctx.prev_tier}" if ctx.tier_changed else "—"
    return {
        "embeds": [
            {
                "title": _headline(signal, ctx),
                "description": _reasons(signal),
                "color": TIER_COLORS[signal.mvrv_tier],
                "fields": [
                    {"name": "BTC Price", "value": f"${ctx.price:,.0f}", "inline": True},
                    {
                        "name": "MVRV 4y pctile",
                        "value": f"{ctx.mvrv_percentile:.0f}%",
                        "inline": True,
                    },
                    {"name": "Tier change", "value": tier_change, "inline": True},
                ],
                "footer": {"text": f"Data {ctx.data_date} · bitcoin-data.com"},
            }
        ]
    }


def build_telegram(signal: Signal, ctx: Context) -> str:
    label = TIER_LABELS[signal.mvrv_tier]
    if signal.stop:
        head = f"<b>{label} — no buy today</b> (0× base)"
    else:
        head = (
            f"<b>{label} — {ctx.amount:,.2f} {ctx.currency} today</b>"
            f" ({signal.multiplier:.2f}× base)"
        )
    mvrv_zone = MVRV_ZONE[signal.mvrv_tier]
    sth_zone = _sth_zone(signal.sth_mvrv)
    lines = [
        head,
        "",
        f"MVRV <code>{signal.mvrv:.2f}</code> {mvrv_zone} → ×{signal.mvrv_mult:g}",
        f"STH-MVRV <code>{signal.sth_mvrv:.2f}</code> {sth_zone} → ×{signal.sth_mult:g}",
        f"Price <code>${ctx.price:,.0f}</code> · MVRV 4y-pctile {ctx.mvrv_percentile:.0f}%",
    ]
    if ctx.tier_changed:
        lines.append(f"Tier change: from {ctx.prev_tier}")
    lines += ["", f"<i>Data {ctx.data_date} · bitcoin-data.com</i>"]
    return "\n".join(lines)


_ERROR_RECOVERY = "No signal today; the job will retry tomorrow. Check https://bitcoin-data.com."


def build_error_discord(reason: str) -> dict:
    reason = reason[:600]
    return {
        "embeds": [
            {
                "title": "DATA ERROR — no signal today",
                "description": f"{reason}\n{_ERROR_RECOVERY}",
                "color": ERROR_COLOR,
            }
        ]
    }


def build_error_telegram(reason: str) -> str:
    reason = reason[:600]
    return f"<b>DATA ERROR — no signal today</b>\n{html.escape(reason)}\n{_ERROR_RECOVERY}"


def sheet_row(signal: Signal, ctx: Context) -> dict:
    return {
        "date": ctx.data_date,
        "price": ctx.price,
        "mvrv": signal.mvrv,
        "sth_mvrv": signal.sth_mvrv,
        "tier": TIER_LABELS[signal.mvrv_tier],
        "multiplier": signal.multiplier,
        "amount": ctx.amount,
    }


log = logging.getLogger("mvrv-dca")

RETRY_WAITS: tuple[int, int, int] = (2, 8, 30)


def http_json(url: str, payload: dict | None = None, timeout: int = 30) -> object:
    req = urllib.request.Request(url, headers={"User-Agent": "mvrv-dca-monitor"})
    if payload is not None:
        req.data = json.dumps(payload).encode()
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
    return json.loads(body) if body else None


def fetch_with_retry(url: str, sleep: Callable[[float], None] = time.sleep) -> object:
    last_err: Exception | None = None
    for attempt in range(4):
        try:
            return http_json(url)
        except (OSError, http.client.HTTPException, ValueError) as e:
            last_err = e
            if attempt < 3:
                wait = RETRY_WAITS[attempt]
                log.warning("fetch attempt %d/4 failed: %s — retry in %ds", attempt + 1, e, wait)
                sleep(wait)
    raise RuntimeError(f"fetch failed after 4 attempts: {url}") from last_err


API = "https://bitcoin-data.com/v1"


def fetch_indicators(fetch: Callable[[str], object] = fetch_with_retry) -> MarketData:
    mvrv_raw_obj = fetch(f"{API}/mvrv")
    sth_raw_obj = fetch(f"{API}/sth-mvrv")
    price_raw_obj = fetch(f"{API}/btc-price")
    if not (
        isinstance(mvrv_raw_obj, list)
        and isinstance(sth_raw_obj, list)
        and isinstance(price_raw_obj, list)
    ):
        raise ValueError(f"unexpected API response shape from {API}")
    mvrv_raw = cast(list[dict], mvrv_raw_obj)
    sth_raw = cast(list[dict], sth_raw_obj)
    price_raw = cast(list[dict], price_raw_obj)
    mvrv_hist = _series(mvrv_raw, "mvrv")
    sth_hist = _series(sth_raw, "sthMvrv")
    if len(mvrv_hist) < 2 or len(sth_hist) < 2:
        raise ValueError("history too short")
    return MarketData(
        mvrv_history=mvrv_hist,
        mvrv=mvrv_hist[-1],
        prev_mvrv=mvrv_hist[-2],
        sth_mvrv=sth_hist[-1],
        prev_sth=sth_hist[-2],
        price=float(price_raw[-1]["btcPrice"]),
        data_date=str(mvrv_raw[-1]["d"]),
    )


def send_discord(webhook_url: str, payload: dict) -> None:
    http_json(webhook_url, payload)


def send_telegram(token: str, chat_id: str, text: str) -> None:
    http_json(
        f"https://api.telegram.org/bot{token}/sendMessage",
        {"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
    )


def send_sheet(url: str, row: dict) -> None:
    http_json(url, row)


def notify_all(
    env: Mapping[str, str],
    discord_payload: dict,
    telegram_text: str,
    row: dict | None,
) -> list[str]:
    targets: list[tuple[str, Callable[[], None]]] = []
    if url := env.get("DISCORD_WEBHOOK_URL"):
        targets.append(("discord", lambda: send_discord(url, discord_payload)))
    else:
        log.info("discord not configured, skipping")
    token, chat_id = env.get("TELEGRAM_BOT_TOKEN"), env.get("TELEGRAM_CHAT_ID")
    if token and chat_id:
        targets.append(("telegram", lambda: send_telegram(token, chat_id, telegram_text)))
    else:
        log.info("telegram not configured, skipping")
    sheet_url = env.get("SHEETS_WEBHOOK_URL")
    if sheet_url and row is not None:
        targets.append(("sheets", lambda: send_sheet(sheet_url, row)))
    elif sheet_url:
        log.info("no row for sheets on this run, skipping")
    else:
        log.info("sheets not configured, skipping")

    if not targets:
        log.warning("no notification channels configured")
        return []

    sent: list[str] = []
    for name, send in targets:
        try:
            send()
            sent.append(name)
        except Exception:
            log.exception("%s send failed", name)
    if not sent:
        raise RuntimeError("all channels failed")
    return sent


def main() -> int:
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    env = os.environ
    base = float(env.get("BASE_AMOUNT") or "10")
    currency = env.get("CURRENCY") or "USD"
    t0 = time.monotonic()

    try:
        data = fetch_indicators()
    except Exception as e:
        log.exception("data fetch failed")
        reason = f"Could not fetch indicators: {e}"
        try:
            notify_all(env, build_error_discord(reason), build_error_telegram(reason), None)
        except Exception:
            log.exception("error alert delivery failed")
        return 1

    signal = classify(data.mvrv, data.sth_mvrv)
    prev = classify(data.prev_mvrv, data.prev_sth)
    ctx = Context(
        data_date=data.data_date,
        price=data.price,
        base_amount=base,
        currency=currency,
        amount=round(base * signal.multiplier, 2),
        mvrv_percentile=percentile(data.mvrv_history, data.mvrv),
        tier_changed=prev.mvrv_tier != signal.mvrv_tier,
        prev_tier=TIER_LABELS[prev.mvrv_tier],
    )
    log.info(
        "fetch: mvrv=%.2f sth=%.2f price=%.0f data_date=%s",
        data.mvrv,
        data.sth_mvrv,
        data.price,
        data.data_date,
    )

    try:
        sent = notify_all(
            env, build_discord(signal, ctx), build_telegram(signal, ctx), sheet_row(signal, ctx)
        )
    except Exception:
        log.exception("notification delivery failed")
        return 1

    log.info(
        "run complete: tier=%s amount=%.2f channels=%s duration=%.1fs",
        signal.mvrv_tier,
        ctx.amount,
        ",".join(sent) or "none",
        time.monotonic() - t0,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
