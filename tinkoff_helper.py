#!/usr/bin/env python3 -I
"""T-Invest API v2 helper — portfolio, candles, search. Uses REST directly."""

import os
import sys
import json
from datetime import datetime, timedelta, timezone

import requests
import pandas as pd

TOKEN = os.environ.get("TINKOFF_TOKEN", "")
BASE = "https://invest-public-api.tbank.ru/rest"


def api(service, method, body=None):
    """Call T-Invest API v2 REST endpoint."""
    if not TOKEN:
        print("ERROR: TINKOFF_TOKEN not set. Export it first:")
        print('  set TINKOFF_TOKEN=your_token   (Windows)')
        print('  export TINKOFF_TOKEN=your_token (Mac/Linux)')
        sys.exit(1)
    url = f"{BASE}/tinkoff.public.invest.api.contract.v1.{service}/{method}"
    resp = requests.post(url, headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    }, json=body or {})
    if resp.status_code != 200:
        print(f"API error {resp.status_code}: {resp.text[:500]}")
        sys.exit(1)
    return resp.json()


def money_value(mv):
    """Convert MoneyValue/Quotation {units, nano} to float."""
    if not mv:
        return 0.0
    units = int(mv.get("units", 0))
    nano = int(mv.get("nano", 0))
    return units + nano / 1_000_000_000


# ── Accounts ──────────────────────────────────────────────────────

def get_account_id():
    """Get the first active account ID."""
    data = api("UsersService", "GetAccounts")
    accounts = data.get("accounts", [])
    for a in accounts:
        if a.get("status") == "ACCOUNT_STATUS_OPEN":
            return a["id"]
    if accounts:
        return accounts[0]["id"]
    print("No accounts found.")
    sys.exit(1)


# ── Portfolio ──────────────────────────────────────────────────────

def portfolio():
    """Show all positions in the portfolio."""
    account_id = get_account_id()
    data = api("OperationsService", "GetPortfolio", {
        "accountId": account_id,
        "currency": "RUB",
    })
    positions = data.get("positions", [])

    if not positions:
        print("Portfolio is empty.")
        return

    rows = []
    for p in positions:
        avg = money_value(p.get("averagePositionPrice"))
        current = money_value(p.get("currentPrice"))
        expected = money_value(p.get("expectedYield"))
        qty = money_value(p.get("quantity"))
        itype = p.get("instrumentType", "")
        figi = p.get("figi", "")
        currency = p.get("averagePositionPrice", {}).get("currency", "")

        pnl_pct = (expected / (avg * qty) * 100) if (avg and qty) else 0

        rows.append({
            "FIGI": figi,
            "Type": itype,
            "Qty": qty,
            "Avg Price": round(avg, 2),
            "Current": round(current, 2),
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


# ── Search ─────────────────────────────────────────────────────────

def search(query):
    """Search for an instrument by ticker or name."""
    data = api("InstrumentsService", "FindInstrument", {
        "query": query,
        "instrumentKind": "INSTRUMENT_TYPE_UNSPECIFIED",
        "apiTradeAvailableFlag": True,
    })
    instruments = data.get("instruments", [])

    if not instruments:
        print(f"Nothing found for '{query}'")
        return

    rows = []
    for i in instruments:
        rows.append({
            "FIGI": i.get("figi", ""),
            "Ticker": i.get("ticker", ""),
            "Name": i.get("name", "")[:30],
            "Type": i.get("instrumentType", ""),
            "ClassCode": i.get("classCode", ""),
        })
    df = pd.DataFrame(rows)
    print(df.to_string(index=False))


# ── Candles & Technical Analysis ───────────────────────────────────

INTERVAL_MAP = {
    "1min": "CANDLE_INTERVAL_1_MIN",
    "5min": "CANDLE_INTERVAL_5_MIN",
    "15min": "CANDLE_INTERVAL_15_MIN",
    "hour": "CANDLE_INTERVAL_HOUR",
    "day": "CANDLE_INTERVAL_DAY",
    "week": "CANDLE_INTERVAL_WEEK",
    "month": "CANDLE_INTERVAL_MONTH",
}


def candles(figi, days=30, interval="day"):
    """Fetch candles and compute basic TA indicators."""
    now = datetime.now(timezone.utc)
    from_ = now - timedelta(days=days)

    candle_interval = INTERVAL_MAP.get(interval, "CANDLE_INTERVAL_DAY")

    data = api("MarketDataService", "GetCandles", {
        "figi": figi,
        "from": from_.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "to": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "interval": candle_interval,
    })
    candle_list = data.get("candles", [])

    if not candle_list:
        print("No candles returned.")
        return

    rows = []
    for c in candle_list:
        rows.append({
            "time": c.get("time", "")[:16],
            "open": money_value(c.get("open")),
            "high": money_value(c.get("high")),
            "low": money_value(c.get("low")),
            "close": money_value(c.get("close")),
            "volume": c.get("volume", 0),
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
        print("!! RSI > 70 -- overbought zone")
    elif last["RSI_14"] and last["RSI_14"] < 30:
        print("!! RSI < 30 -- oversold zone")

    if last["MACD"] > last["Signal"]:
        print(">> MACD above signal -- bullish momentum")
    else:
        print("<< MACD below signal -- bearish momentum")

    if last["close"] > last["SMA_20"]:
        print(">> Price above SMA(20) -- uptrend")
    else:
        print("<< Price below SMA(20) -- downtrend")


# ── Orderbook ──────────────────────────────────────────────────────

def orderbook(figi, depth=10):
    """Show the order book for an instrument."""
    data = api("MarketDataService", "GetOrderBook", {
        "figi": figi,
        "depth": depth,
    })

    print(f"FIGI: {figi}")
    print(f"Last price: {money_value(data.get('lastPrice'))}")
    print(f"Close price: {money_value(data.get('closePrice'))}")
    print()

    asks = data.get("asks", [])
    bids = data.get("bids", [])

    print("--- ASKS (sell) ---")
    for a in reversed(asks[:depth]):
        print(f"  {money_value(a.get('price')):>12.2f}  x {a.get('quantity', 0)}")

    print("--- --- ---")

    print("--- BIDS (buy) ---")
    for b in bids[:depth]:
        print(f"  {money_value(b.get('price')):>12.2f}  x {b.get('quantity', 0)}")


# ── Operations ─────────────────────────────────────────────────────

def operations(figi=None, days=30):
    """Show recent operations (trades)."""
    account_id = get_account_id()
    now = datetime.now(timezone.utc)
    from_ = now - timedelta(days=days)

    body = {
        "accountId": account_id,
        "from": from_.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "to": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if figi:
        body["figi"] = figi

    data = api("OperationsService", "GetOperations", body)
    ops = data.get("operations", [])

    if not ops:
        print("No operations found.")
        return

    rows = []
    for op in ops:
        rows.append({
            "Date": op.get("date", "")[:16],
            "Type": op.get("operationType", ""),
            "FIGI": op.get("figi", ""),
            "Qty": op.get("quantity", ""),
            "Price": money_value(op.get("price")),
            "Total": money_value(op.get("payment")),
            "CCY": op.get("currency", ""),
            "State": op.get("state", ""),
        })

    df = pd.DataFrame(rows)
    print(df.to_string(index=False))


# ── CLI ────────────────────────────────────────────────────────────

USAGE = """
Usage: python tinkoff_helper.py <command> [args]

Commands:
  portfolio              -- show all positions
  search <query>         -- search instrument by ticker/name
  candles <figi> [days] [interval] -- candles + TA (intervals: 1min,5min,15min,hour,day,week,month)
  orderbook <figi> [depth]        -- order book
  operations [figi] [days]        -- recent trades/operations
"""

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(USAGE)
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "portfolio":
        portfolio()
    elif cmd == "search":
        if len(sys.argv) < 3:
            print("Usage: search <query>")
            sys.exit(1)
        search(sys.argv[2])
    elif cmd == "candles":
        if len(sys.argv) < 3:
            print("Usage: candles <figi> [days] [interval]")
            sys.exit(1)
        figi = sys.argv[2]
        days = int(sys.argv[3]) if len(sys.argv) > 3 else 30
        interval = sys.argv[4] if len(sys.argv) > 4 else "day"
        candles(figi, days, interval)
    elif cmd == "orderbook":
        if len(sys.argv) < 3:
            print("Usage: orderbook <figi> [depth]")
            sys.exit(1)
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
