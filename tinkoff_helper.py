#!/usr/bin/env python3 -I
"""Tinkoff Invest API helper — portfolio analysis, candles, search."""

import os
import sys
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import tinvest
import pandas as pd

TOKEN = os.environ.get("TINKOFF_TOKEN", "")


CA_BUNDLE = os.environ.get("REQUESTS_CA_BUNDLE", "/root/.ccr/ca-bundle.crt")


def get_client():
    if not TOKEN:
        print("ERROR: TINKOFF_TOKEN not set. Export it first:")
        print('  export TINKOFF_TOKEN="your_token_here"')
        sys.exit(1)
    client = tinvest.SyncClient(TOKEN)
    if os.path.exists(CA_BUNDLE):
        client._session.verify = CA_BUNDLE
    return client


# ── Portfolio ──────────────────────────────────────────────────────

def portfolio():
    """Show all positions in the portfolio."""
    client = get_client()
    resp = client.get_portfolio()
    positions = resp.payload.positions

    if not positions:
        print("Portfolio is empty.")
        return

    rows = []
    for p in positions:
        avg = float(p.average_position_price.value) if p.average_position_price else 0
        expected = float(p.expected_yield.value) if p.expected_yield else 0
        currency = p.average_position_price.currency.value if p.average_position_price else ""
        lots = p.lots
        name = p.name
        ticker = p.ticker
        itype = p.instrument_type.value
        balance = float(p.balance)
        current_price = avg + (expected / balance) if balance else avg

        pnl_pct = (expected / (avg * balance) * 100) if (avg and balance) else 0

        rows.append({
            "Ticker": ticker,
            "Name": name[:25],
            "Type": itype,
            "Lots": lots,
            "Qty": balance,
            "Avg Price": round(avg, 2),
            "Current": round(current_price, 2),
            "P&L": round(expected, 2),
            "P&L %": round(pnl_pct, 2),
            "CCY": currency,
        })

    df = pd.DataFrame(rows)
    print(df.to_string(index=False))

    total_by_ccy = df.groupby("CCY")["P&L"].sum()
    print("\n--- Total P&L by currency ---")
    for ccy, total in total_by_ccy.items():
        print(f"  {ccy}: {total:+.2f}")


def portfolio_currencies():
    """Show cash balances."""
    client = get_client()
    resp = client.get_portfolio_currencies()
    rows = []
    for c in resp.payload.currencies:
        rows.append({
            "Currency": c.currency.value,
            "Balance": float(c.balance),
            "Blocked": float(c.blocked) if c.blocked else 0,
        })
    df = pd.DataFrame(rows)
    print(df.to_string(index=False))


# ── Search ─────────────────────────────────────────────────────────

def search(query):
    """Search for an instrument by ticker or name."""
    client = get_client()
    resp = client.get_market_search_by_ticker(query)
    instruments = resp.payload.instruments

    if not instruments:
        print(f"Nothing found for '{query}'")
        return

    rows = []
    for i in instruments:
        rows.append({
            "FIGI": i.figi,
            "Ticker": i.ticker,
            "Name": i.name[:30],
            "Type": i.type.value if i.type else "",
            "Currency": i.currency.value if i.currency else "",
            "Lot": i.lot,
            "Min Qty": i.min_quantity if hasattr(i, "min_quantity") else "",
        })
    df = pd.DataFrame(rows)
    print(df.to_string(index=False))


# ── Candles & Technical Analysis ───────────────────────────────────

def candles(figi, days=30, interval="day"):
    """Fetch candles and compute basic TA indicators."""
    client = get_client()

    interval_map = {
        "1min": tinvest.CandleResolution.min1,
        "5min": tinvest.CandleResolution.min5,
        "15min": tinvest.CandleResolution.min15,
        "30min": tinvest.CandleResolution.min30,
        "hour": tinvest.CandleResolution.hour,
        "day": tinvest.CandleResolution.day,
        "week": tinvest.CandleResolution.week,
        "month": tinvest.CandleResolution.month,
    }

    res = interval_map.get(interval, tinvest.CandleResolution.day)
    now = datetime.now(timezone.utc)
    from_ = now - timedelta(days=days)

    resp = client.get_market_candles(figi, from_, now, res)
    candle_list = resp.payload.candles

    if not candle_list:
        print("No candles returned.")
        return

    rows = []
    for c in candle_list:
        rows.append({
            "time": c.time.strftime("%Y-%m-%d %H:%M"),
            "open": float(c.o),
            "high": float(c.h),
            "low": float(c.l),
            "close": float(c.c),
            "volume": c.v,
        })

    df = pd.DataFrame(rows)

    df["SMA_10"] = df["close"].rolling(10).mean().round(2)
    df["SMA_20"] = df["close"].rolling(20).mean().round(2)
    df["EMA_12"] = df["close"].ewm(span=12).mean().round(2)
    df["EMA_26"] = df["close"].ewm(span=26).mean().round(2)
    df["MACD"] = (df["EMA_12"] - df["EMA_26"]).round(2)
    df["Signal"] = df["MACD"].ewm(span=9).mean().round(2)

    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = (-delta.clip(upper=0))
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    df["RSI_14"] = (100 - (100 / (1 + rs))).round(2)

    print(df.tail(20).to_string(index=False))

    last = df.iloc[-1]
    print(f"\n--- Summary ---")
    print(f"Last close:  {last['close']}")
    print(f"SMA(10):     {last['SMA_10']}")
    print(f"SMA(20):     {last['SMA_20']}")
    print(f"RSI(14):     {last['RSI_14']}")
    print(f"MACD:        {last['MACD']}")
    print(f"Signal:      {last['Signal']}")

    if last["RSI_14"] and last["RSI_14"] > 70:
        print("⚠ RSI > 70 — overbought zone")
    elif last["RSI_14"] and last["RSI_14"] < 30:
        print("⚠ RSI < 30 — oversold zone")

    if last["MACD"] > last["Signal"]:
        print("↑ MACD above signal — bullish momentum")
    else:
        print("↓ MACD below signal — bearish momentum")

    if last["close"] > last["SMA_20"]:
        print("↑ Price above SMA(20) — uptrend")
    else:
        print("↓ Price below SMA(20) — downtrend")


# ── Orderbook ──────────────────────────────────────────────────────

def orderbook(figi, depth=10):
    """Show the order book for an instrument."""
    client = get_client()
    resp = client.get_market_orderbook(figi, depth)
    ob = resp.payload

    print(f"FIGI: {figi}")
    print(f"Last price: {ob.last_price}")
    print(f"Close price: {ob.close_price}")
    print(f"Trade status: {ob.trade_status.value}")
    print()

    print("--- ASKS (sell) ---")
    for a in reversed(ob.asks[:depth]):
        print(f"  {float(a.price):>12.2f}  x {a.quantity}")

    print("--- --- ---")

    print("--- BIDS (buy) ---")
    for b in ob.bids[:depth]:
        print(f"  {float(b.price):>12.2f}  x {b.quantity}")


# ── Operations ─────────────────────────────────────────────────────

def operations(figi=None, days=30):
    """Show recent operations (trades)."""
    client = get_client()
    now = datetime.now(timezone.utc)
    from_ = now - timedelta(days=days)

    resp = client.get_operations(from_, now, figi)
    ops = resp.payload.operations

    if not ops:
        print("No operations found.")
        return

    rows = []
    for op in ops:
        rows.append({
            "Date": op.date.strftime("%Y-%m-%d %H:%M") if op.date else "",
            "Type": op.operation_type.value if op.operation_type else "",
            "Ticker": op.figi or "",
            "Qty": op.quantity or "",
            "Price": float(op.price) if op.price else "",
            "Total": float(op.payment) if op.payment else "",
            "CCY": op.currency.value if op.currency else "",
            "Status": op.status.value if op.status else "",
        })

    df = pd.DataFrame(rows)
    print(df.to_string(index=False))


# ── CLI ────────────────────────────────────────────────────────────

USAGE = """
Usage: python tinkoff_helper.py <command> [args]

Commands:
  portfolio              — show all positions
  cash                   — show cash balances
  search <ticker>        — search instrument by ticker
  candles <figi> [days] [interval] — candles + TA indicators
  orderbook <figi> [depth]        — order book
  operations [figi] [days]        — recent trades/operations
"""

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(USAGE)
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "portfolio":
        portfolio()
    elif cmd == "cash":
        portfolio_currencies()
    elif cmd == "search":
        search(sys.argv[2])
    elif cmd == "candles":
        figi = sys.argv[2]
        days = int(sys.argv[3]) if len(sys.argv) > 3 else 30
        interval = sys.argv[4] if len(sys.argv) > 4 else "day"
        candles(figi, days, interval)
    elif cmd == "orderbook":
        figi = sys.argv[2]
        depth = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        orderbook(figi, depth)
    elif cmd == "operations":
        figi = sys.argv[2] if len(sys.argv) > 2 else None
        days = int(sys.argv[3]) if len(sys.argv) > 3 else 30
        operations(figi, days)
    else:
        print(f"Unknown command: {cmd}")
        print(USAGE)
