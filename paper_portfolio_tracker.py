"""
Paper Portfolio Tracker & Simulator
====================================
Tracks live paper trading for both Multi-Asset ETF Momentum (Pillar 1) 
and Nifty 500 Stock Momentum (Pillar 2) strategies without real money.

Features:
1. Initialize Paper Capital (e.g. ₹1,000,000 or ₹10,000,000)
2. Executes Virtual Buy/Sell rebalances based on live strategy signals
3. Daily Automatic Risk Management: Checks 15% Fixed SL & 20% Trailing SL
4. Persists portfolio state cleanly in 'paper_portfolio_state.json'
5. Displays real-time portfolio performance, active stops, and equity logs
"""

import os
import sys
import json
import datetime
import pandas as pd
import numpy as np

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False

STATE_FILE = "paper_portfolio_state.json"
SLIPPAGE_PCT = 0.001  # 0.1% per side friction

DEFAULT_INITIAL_CAPITAL = 10_000_000.0  # ₹1 Crore default


import requests

def send_telegram_alert(message, bot_token="8902953168:AAGZWp0jscFDTOOKPxk004smiIewkkzvzkU", chat_id="8785681126"):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("Telegram alert error:", e)

# Example Usage inside your daily stop-loss checker:
# send_telegram_alert("🔴 [STOP LOSS ALERT] MAFANG.NS hit 15% Stop Loss at ₹265.50. Position exited to Cash.")

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return None

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4, default=str)

def get_current_price(ticker):
    """Fetches live/latest close price for a ticker."""
    if HAS_YFINANCE:
        try:
            df = yf.download(ticker, period="5d", progress=False)
            if not df.empty and "Close" in df.columns:
                close_vals = df["Close"].values
                if len(close_vals) > 0:
                    val = float(close_vals[-1].iloc[0]) if hasattr(close_vals[-1], "iloc") else float(close_vals[-1])
                    return val
        except Exception:
            pass
    # Offline fallback generator for testing
    np.random.seed(abs(hash(ticker)) % 10000)
    return float(np.random.uniform(100, 2500))

def initialize_portfolio(capital=DEFAULT_INITIAL_CAPITAL):
    """Initializes a new paper trading portfolio state."""
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    state = {
        "created_at": today_str,
        "last_updated": today_str,
        "initial_capital": capital,
        "cash_balance": capital,
        "etf_portfolio": {
            "allocated_capital": capital * 0.5,
            "cash": capital * 0.5,
            "positions": {}  # ticker: {shares, entry_price, peak_price, entry_date}
        },
        "stock_portfolio": {
            "allocated_capital": capital * 0.5,
            "cash": capital * 0.5,
            "positions": {}
        },
        "trade_history": [],
        "daily_valuation_log": []
    }
    save_state(state)
    print(f"✅ Paper portfolio initialized successfully with ₹{capital:,.2f} total capital.")
    print(f"   • ETF Strategy Allocation   : ₹{capital*0.5:,.2f} (50%)")
    print(f"   • Stock Strategy Allocation : ₹{capital*0.5:,.2f} (50%)")
    return state

def run_daily_check():
    """Runs daily price updates & checks 15% fixed and 20% trailing stop-losses."""
    state = load_state()
    if not state:
        print("⚠️ No paper portfolio found. Initializing new portfolio...")
        state = initialize_portfolio()

    today_str = datetime.date.today().strftime("%Y-%m-%d")
    print("=" * 80)
    print(f" 🔍 DAILY PAPER PORTFOLIO RISK & VALUATION CHECK — {today_str}")
    print("=" * 80)

    total_portfolio_val = 0.0
    stopped_out_count = 0

    # Process ETF Strategy Positions
    etf_pos_val = 0.0
    for ticker, pos in list(state["etf_portfolio"]["positions"].items()):
        c_price = get_current_price(ticker)
        
        # Update peak price
        if c_price > pos["peak_price"]:
            pos["peak_price"] = c_price

        entry_p = pos["entry_price"]
        peak_p = pos["peak_price"]
        fixed_sl = entry_p * 0.85
        trailing_sl = peak_p * 0.80

        # Check stops
        exit_reason = None
        if c_price <= fixed_sl:
            exit_reason = "15% Fixed Stop Loss"
        elif c_price <= trailing_sl:
            exit_reason = "20% Trailing Stop Loss"

        if exit_reason:
            gross_val = pos["shares"] * c_price
            tx_cost = gross_val * SLIPPAGE_PCT
            net_proceeds = gross_val - tx_cost
            state["etf_portfolio"]["cash"] += net_proceeds
            pnl = net_proceeds - (pos["shares"] * entry_p)
            pnl_pct = (c_price - entry_p) / entry_p * 100.0

            state["trade_history"].append({
                "strategy": "ETF",
                "ticker": ticker,
                "entry_date": pos["entry_date"],
                "exit_date": today_str,
                "entry_price": entry_p,
                "exit_price": c_price,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "reason": exit_reason
            })
            del state["etf_portfolio"]["positions"][ticker]
            stopped_out_count += 1
            print(f"  🔴 [ETF STOP-OUT] {ticker:<12} | Exit: ₹{c_price:.2f} | PnL: {pnl_pct:+.2f}% | Reason: {exit_reason}")
        else:
            cur_val = pos["shares"] * c_price
            etf_pos_val += cur_val
            dist_trail = (c_price - trailing_sl) / c_price * 100.0
            print(f"  🟢 [ETF HOLD] {ticker:<14} | Price: ₹{c_price:.2f} | Entry: ₹{entry_p:.2f} | Peak: ₹{peak_p:.2f} | Trail SL: ₹{trailing_sl:.2f} (Buffer: +{dist_trail:.1f}%)")

    # Process Stock Strategy Positions
    stock_pos_val = 0.0
    for ticker, pos in list(state["stock_portfolio"]["positions"].items()):
        c_price = get_current_price(ticker)
        
        if c_price > pos["peak_price"]:
            pos["peak_price"] = c_price

        entry_p = pos["entry_price"]
        peak_p = pos["peak_price"]
        fixed_sl = entry_p * 0.85
        trailing_sl = peak_p * 0.80

        exit_reason = None
        if c_price <= fixed_sl:
            exit_reason = "15% Fixed Stop Loss"
        elif c_price <= trailing_sl:
            exit_reason = "20% Trailing Stop Loss"

        if exit_reason:
            gross_val = pos["shares"] * c_price
            tx_cost = gross_val * SLIPPAGE_PCT
            net_proceeds = gross_val - tx_cost
            state["stock_portfolio"]["cash"] += net_proceeds
            pnl = net_proceeds - (pos["shares"] * entry_p)
            pnl_pct = (c_price - entry_p) / entry_p * 100.0

            state["trade_history"].append({
                "strategy": "Stock",
                "ticker": ticker,
                "entry_date": pos["entry_date"],
                "exit_date": today_str,
                "entry_price": entry_p,
                "exit_price": c_price,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "reason": exit_reason
            })
            del state["stock_portfolio"]["positions"][ticker]
            stopped_out_count += 1
            print(f"  🔴 [STOCK STOP-OUT] {ticker:<12} | Exit: ₹{c_price:.2f} | PnL: {pnl_pct:+.2f}% | Reason: {exit_reason}")
        else:
            cur_val = pos["shares"] * c_price
            stock_pos_val += cur_val
            dist_trail = (c_price - trailing_sl) / c_price * 100.0
            print(f"  🟢 [STOCK HOLD] {ticker:<12} | Price: ₹{c_price:.2f} | Entry: ₹{entry_p:.2f} | Peak: ₹{peak_p:.2f} | Trail SL: ₹{trailing_sl:.2f} (Buffer: +{dist_trail:.1f}%)")

    # Overall Valuation
    total_etf_val = etf_pos_val + state["etf_portfolio"]["cash"]
    total_stock_val = stock_pos_val + state["stock_portfolio"]["cash"]
    total_portfolio_val = total_etf_val + total_stock_val

    pnl_overall = total_portfolio_val - state["initial_capital"]
    pnl_overall_pct = pnl_overall / state["initial_capital"] * 100.0

    state["last_updated"] = today_str
    state["daily_valuation_log"].append({
        "date": today_str,
        "total_val": total_portfolio_val,
        "etf_val": total_etf_val,
        "stock_val": total_stock_val,
        "cash_total": state["etf_portfolio"]["cash"] + state["stock_portfolio"]["cash"]
    })

    save_state(state)

    print("-" * 80)
    print(f" 📊 PORTFOLIO SUMMARY AS OF {today_str}")
    print(f"  • Total Portfolio Value : ₹{total_portfolio_val:,.2f} ({pnl_overall_pct:+.2f}% Net Return)")
    print(f"  • ETF Strategy Value    : ₹{total_etf_val:,.2f} (Positions: ₹{etf_pos_val:,.2f} | Cash: ₹{state['etf_portfolio']['cash']:,.2f})")
    print(f"  • Stock Strategy Value  : ₹{total_stock_val:,.2f} (Positions: ₹{stock_pos_val:,.2f} | Cash: ₹{state['stock_portfolio']['cash']:,.2f})")
    print(f"  • Daily Stop Exits Hit  : {stopped_out_count} assets")
    print("=" * 80)

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--reset":
        initialize_portfolio()
    else:
        run_daily_check()

if __name__ == "__main__":
    main()
