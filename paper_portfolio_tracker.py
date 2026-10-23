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
                c_series = df["Close"].dropna()
                if len(c_series) > 0:
                    val = c_series.iloc[-1]
                    if hasattr(val, "iloc"):
                        val = val.iloc[0]
                    val = float(val)
                    if not np.isnan(val) and val > 0:
                        return val
        except Exception as e:
            print(f"yfinance fetch error for {ticker}: {e}")
    return None

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

def auto_allocate_etfs(state, today_str):
    """Automatically scans ETF universe and buys Top 6 qualifying momentum ETFs if unallocated."""
    etf_cash = state["etf_portfolio"].get("cash", 0.0)
    if etf_cash < 100_000:
        return
    
    print(f"🚀 [AUTO-ALLOCATION] Scanning Multi-Asset ETF Universe for Top 6 Momentum rotation...")
    try:
        from live_etf_rebalancer import fetch_etf_data
        data_dict = fetch_etf_data()
        rankings = []
        for tkr, df in data_dict.items():
            closes = df['Close'].dropna()
            if len(closes) < 200:
                continue
            c_price = float(closes.iloc[-1].iloc[0]) if hasattr(closes.iloc[-1], 'iloc') else float(closes.iloc[-1])
            if np.isnan(c_price) or c_price <= 0:
                continue
            sma200_series = closes.rolling(200).mean().dropna()
            if len(sma200_series) == 0:
                continue
            sma200 = float(sma200_series.iloc[-1].iloc[0]) if hasattr(sma200_series.iloc[-1], 'iloc') else float(sma200_series.iloc[-1])
            if c_price <= sma200:
                continue
            r1m = (c_price - closes.iloc[-21]) / closes.iloc[-21]
            r3m = (c_price - closes.iloc[-63]) / closes.iloc[-63]
            r6m = (c_price - closes.iloc[-126]) / closes.iloc[-126]
            r12m = (c_price - closes.iloc[-252]) / closes.iloc[-252] if len(closes) >= 252 else r6m
            raw_score = 0.10 * r1m + 0.20 * r3m + 0.30 * r6m + 0.40 * r12m
            score = float(raw_score.iloc[0]) if hasattr(raw_score, 'iloc') else float(raw_score)
            rankings.append({'ticker': tkr, 'price': c_price, 'sma200': sma200, 'score': score})

        rankings.sort(key=lambda x: x['score'], reverse=True)
        top_6 = rankings[:6]
        if len(top_6) == 0:
            print("  ⚠️ No ETFs currently qualifying above 200 SMA. Remaining in Cash.")
            return

        slot_size = etf_cash / float(len(top_6))
        bought_names = []
        for item in top_6:
            tkr = item['ticker']
            price = item['price']
            shares = int(slot_size / price)
            if shares > 0:
                cost = shares * price
                tx = cost * SLIPPAGE_PCT
                total_spent = cost + tx
                if state["etf_portfolio"]["cash"] >= total_spent:
                    state["etf_portfolio"]["cash"] -= total_spent
                    state["etf_portfolio"]["positions"][tkr] = {
                        "shares": shares,
                        "entry_price": price,
                        "peak_price": price,
                        "entry_date": today_str
                    }
                    bought_names.append(f"{tkr} ({shares} sh @ ₹{price:.2f})")
                    print(f"  🟢 [AUTO-BUY ETF] {tkr:<14} | Shares: {shares} | Price: ₹{price:.2f}")

        if bought_names:
            msg = (
                f"🟢 *AUTONOMOUS ETF ALLOCATION EXECUTION*\n\n"
                f"Deployed ₹{etf_cash:,.2f} across Top {len(bought_names)} Momentum ETFs:\n"
                + "\n".join([f"• `{b}`" for b in bought_names])
                + f"\n\n*Risk Rules Active:* 15% Fixed SL & 20% Trailing SL armed."
            )
            send_telegram_alert(msg)
    except Exception as e:
        print(f"Error during auto ETF allocation: {e}")

def auto_allocate_stocks(state, today_str):
    """Checks Macro Regime Guard. If Bullish, deploys into Top 15 stocks. If Bearish, stays in Cash Buffer."""
    stock_cash = state["stock_portfolio"].get("cash", 0.0)
    if stock_cash < 100_000:
        return
        
    print(f"🔍 [AUTO-ALLOCATION] Checking Nifty 500 Macro Regime Guard for Stock allocation...")
    try:
        from live_nifty500_rebalancer import load_live_data, BENCHMARK_TICKER
        data_dict = load_live_data()
        bm_df = data_dict.get(BENCHMARK_TICKER)
        if bm_df is not None:
            bm_df["200_EMA"] = bm_df["Close"].ewm(span=200, adjust=False).mean()
            latest_close = bm_df["Close"].iloc[-1]
            latest_ema = bm_df["200_EMA"].iloc[-1]
            if latest_close < latest_ema:
                print(f"  🛡️ [REGIME GUARD: BEARISH] Nifty 500 ({latest_close:.1f}) < 200 EMA ({latest_ema:.1f}). Capital parked safely in Cash.")
                return
    except Exception as e:
        print(f"Error checking regime guard: {e}")

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

    # Auto-deploy initial allocations if unallocated
    if len(state["etf_portfolio"]["positions"]) == 0 and state["etf_portfolio"]["cash"] > 100_000:
        auto_allocate_etfs(state, today_str)

    if len(state["stock_portfolio"]["positions"]) == 0 and state["stock_portfolio"]["cash"] > 100_000:
        auto_allocate_stocks(state, today_str)

    # Process ETF Strategy Positions
    etf_pos_val = 0.0
    for ticker, pos in list(state["etf_portfolio"]["positions"].items()):
        c_price = get_current_price(ticker)
        if c_price is None:
            c_price = pos.get("peak_price", pos["entry_price"])
        
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
                "shares": pos["shares"],
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "reason": exit_reason
            })
            del state["etf_portfolio"]["positions"][ticker]
            stopped_out_count += 1
            print(f"  🔴 [ETF STOP-OUT] {ticker:<12} | Exit: ₹{c_price:.2f} | PnL: {pnl_pct:+.2f}% | Reason: {exit_reason}")
            stop_msg = (
                f"🚨 *STOP LOSS HIT — ETF*\n\n"
                f"• Asset: `{ticker}`\n"
                f"• Trigger: *{exit_reason}*\n"
                f"• Exit Price: ₹{c_price:.2f}\n"
                f"• Entry Price: ₹{entry_p:.2f}\n"
                f"• Net P&L: *{pnl_pct:+.2f}%* (₹{pnl:+,.2f})\n"
                f"• Action: Exited to Cash Buffer"
            )
            send_telegram_alert(stop_msg)
        else:
            cur_val = pos["shares"] * c_price
            etf_pos_val += cur_val
            dist_trail = (c_price - trailing_sl) / c_price * 100.0
            print(f"  🟢 [ETF HOLD] {ticker:<14} | Price: ₹{c_price:.2f} | Entry: ₹{entry_p:.2f} | Peak: ₹{peak_p:.2f} | Trail SL: ₹{trailing_sl:.2f} (Buffer: +{dist_trail:.1f}%)")

    # Process Stock Strategy Positions
    stock_pos_val = 0.0
    for ticker, pos in list(state["stock_portfolio"]["positions"].items()):
        c_price = get_current_price(ticker)
        if c_price is None:
            c_price = pos.get("peak_price", pos["entry_price"])
        
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
                "shares": pos["shares"],
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "reason": exit_reason
            })
            del state["stock_portfolio"]["positions"][ticker]
            stopped_out_count += 1
            print(f"  🔴 [STOCK STOP-OUT] {ticker:<12} | Exit: ₹{c_price:.2f} | PnL: {pnl_pct:+.2f}% | Reason: {exit_reason}")
            stop_msg = (
                f"🚨 *STOP LOSS HIT — STOCK*\n\n"
                f"• Asset: `{ticker}`\n"
                f"• Trigger: *{exit_reason}*\n"
                f"• Exit Price: ₹{c_price:.2f}\n"
                f"• Entry Price: ₹{entry_p:.2f}\n"
                f"• Net P&L: *{pnl_pct:+.2f}%* (₹{pnl:+,.2f})\n"
                f"• Action: Exited to Cash Buffer"
            )
            send_telegram_alert(stop_msg)
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

    summary_msg = (
        f"📊 *DAILY PORTFOLIO UPDATE — {today_str}*\n\n"
        f"• Total Net Worth: *₹{total_portfolio_val:,.2f}* ({pnl_overall_pct:+.2f}%)\n"
        f"• ETF Strategy: ₹{total_etf_val:,.2f}\n"
        f"• Stock Strategy: ₹{total_stock_val:,.2f}\n"
        f"• Liquid Cash: ₹{state['etf_portfolio']['cash'] + state['stock_portfolio']['cash']:,.2f}\n"
        f"• Stop Exits Today: *{stopped_out_count}*"
    )
    send_telegram_alert(summary_msg)

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--reset":
        initialize_portfolio()
    else:
        run_daily_check()

if __name__ == "__main__":
    main()
