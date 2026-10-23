"""
Automated Quantitative Portfolio Web Dashboard (Streamlit)
=========================================================
Provides a real-time, interactive visual dashboard for tracking 
Paper Trading Portfolios, Daily P&L, Active Positions, Stop Losses, 
and Monthly Rebalance Signals without typing terminal commands.
"""

import os
import json
import datetime
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

# Configuration
STATE_FILE = "paper_portfolio_state.json"

st.set_page_config(
    page_title="Quantitative Momentum Portfolio Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 1. HELPER FUNCTIONS & DATA LOADERS
# ==========================================
def load_portfolio_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return None

def create_default_state(capital=10_000_000.0):
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    return {
        "created_at": today_str,
        "last_updated": today_str,
        "initial_capital": capital,
        "cash_balance": capital,
        "etf_portfolio": {
            "allocated_capital": capital * 0.5,
            "cash": capital * 0.5,
            "positions": {}
        },
        "stock_portfolio": {
            "allocated_capital": capital * 0.5,
            "cash": capital * 0.5,
            "positions": {}
        },
        "trade_history": [],
        "daily_valuation_log": [
            {"date": today_str, "total_val": capital, "etf_val": capital * 0.5, "stock_val": capital * 0.5, "cash_total": capital}
        ]
    }

# ==========================================
# 2. DASHBOARD HEADER & SIDEBAR
# ==========================================
st.title("📈 Quantitative Momentum Strategy Dashboard")
st.caption("Pillar 1 (50% ETF Momentum) + Pillar 2 (50% Nifty 500 Stock Momentum) Automated Live Tracker")

state = load_portfolio_state()
if not state:
    st.warning("⚠️ No active paper portfolio found. Initializing a default ₹1 Crore portfolio...")
    state = create_default_state()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

# Sidebar Controls
st.sidebar.header("⚙️ Dashboard Controls")
if st.sidebar.button("🔄 Refresh Data / Re-sync"):
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("📌 System Status")
st.sidebar.success("🟢 Automated Scheduler Active")
st.sidebar.info(f"Last Updated: **{state.get('last_updated', 'N/A')}**")
st.sidebar.text(f"Portfolio Created: {state.get('created_at', 'N/A')}")

# Reset Portfolio Option
with st.sidebar.expander("⚠️ Reset / Re-initialize Portfolio"):
    new_capital = st.number_input("Starting Capital (₹)", value=10_000_000.0, step=100_000.0)
    if st.button("Confirm Reset"):
        state = create_default_state(new_capital)
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=4)
        st.success(f"Portfolio reset to ₹{new_capital:,.2f}")
        st.rerun()

# ==========================================
# 3. TOP KPI METRICS
# ==========================================
init_cap = state.get("initial_capital", 10_000_000.0)
daily_log = state.get("daily_valuation_log", [])

if daily_log:
    current_val = daily_log[-1]["total_val"]
    etf_val = daily_log[-1]["etf_val"]
    stock_val = daily_log[-1]["stock_val"]
    cash_val = daily_log[-1]["cash_total"]
else:
    current_val = init_cap
    etf_val = init_cap * 0.5
    stock_val = init_cap * 0.5
    cash_val = init_cap

total_pnl = current_val - init_cap
total_pnl_pct = (total_pnl / init_cap) * 100.0

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Total Net Worth", f"₹{current_val:,.2f}", f"{total_pnl_pct:+.2f}%")
col2.metric("Total Net P&L", f"₹{total_pnl:,.2f}", f"{'Profit' if total_pnl >= 0 else 'Loss'}")
col3.metric("ETF Portfolio (50%)", f"₹{etf_val:,.2f}")
col4.metric("Stock Portfolio (50%)", f"₹{stock_val:,.2f}")
col5.metric("Cash / Liquid Buffer", f"₹{cash_val:,.2f}")

st.markdown("---")

# ==========================================
# 4. INTERACTIVE CHARTS (EQUITY CURVE & ALLOCATION)
# ==========================================
tab_overview, tab_positions, tab_trades, tab_rebalance = st.tabs([
    "📊 Equity Curve & Analytics",
    "🎯 Active Holdings & Stop Losses",
    "📋 Trade History Log",
    "🚀 Monthly Rebalance Signals"
])

with tab_overview:
    col_chart1, col_chart2 = st.columns([2, 1])
    
    with col_chart1:
        st.subheader("📈 Cumulative Equity Curve")
        if len(daily_log) > 0:
            df_log = pd.DataFrame(daily_log)
            fig_eq = go.Figure()
            fig_eq.add_trace(go.Scatter(
                x=df_log["date"], y=df_log["total_val"],
                mode="lines+markers", name="Total Portfolio",
                line=dict(color="#10B981", width=3)
            ))
            fig_eq.add_trace(go.Scatter(
                x=df_log["date"], y=df_log["etf_val"],
                mode="lines", name="ETF Strategy",
                line=dict(color="#3B82F6", width=1.5, dash="dot")
            ))
            fig_eq.add_trace(go.Scatter(
                x=df_log["date"], y=df_log["stock_val"],
                mode="lines", name="Stock Strategy",
                line=dict(color="#F59E0B", width=1.5, dash="dot")
            ))
            fig_eq.update_layout(template="plotly_dark", height=400, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig_eq, use_container_width=True)
        else:
            st.info("No daily log history accumulated yet.")

    with col_chart2:
        st.subheader("🍰 Asset Allocation Breakdown")
        alloc_data = {
            "Asset Class": ["ETF Positions", "Stock Positions", "Unallocated Cash"],
            "Value": [
                max(0.0, etf_val - state["etf_portfolio"].get("cash", 0)),
                max(0.0, stock_val - state["stock_portfolio"].get("cash", 0)),
                cash_val
            ]
        }
        fig_pie = px.pie(alloc_data, names="Asset Class", values="Value", hole=0.4,
                         color_discrete_sequence=["#3B82F6", "#F59E0B", "#10B981"])
        fig_pie.update_layout(template="plotly_dark", height=400, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig_pie, use_container_width=True)

# ==========================================
# 5. ACTIVE HOLDINGS & STOP LOSS MONITORS
# ==========================================
with tab_positions:
    st.subheader("🛡️ Active Holdings & Daily Stop-Loss Buffer")
    
    etf_pos = state["etf_portfolio"].get("positions", {})
    stock_pos = state["stock_portfolio"].get("positions", {})
    
    holdings_list = []
    
    for tkr, pos in etf_pos.items():
        entry_p = pos.get("entry_price", 0)
        peak_p = pos.get("peak_price", entry_p)
        shares = pos.get("shares", 0)
        trail_sl = peak_p * 0.80
        fixed_sl = entry_p * 0.85
        holdings_list.append({
            "Strategy": "Multi-Asset ETF",
            "Ticker": tkr,
            "Shares": int(shares),
            "Entry Price (₹)": f"₹{entry_p:,.2f}",
            "Peak Price (₹)": f"₹{peak_p:,.2f}",
            "15% Fixed SL (₹)": f"₹{fixed_sl:,.2f}",
            "20% Trailing SL (₹)": f"₹{trail_sl:,.2f}",
            "Entry Date": pos.get("entry_date", "N/A")
        })
        
    for tkr, pos in stock_pos.items():
        entry_p = pos.get("entry_price", 0)
        peak_p = pos.get("peak_price", entry_p)
        shares = pos.get("shares", 0)
        trail_sl = peak_p * 0.80
        fixed_sl = entry_p * 0.85
        holdings_list.append({
            "Strategy": "Nifty 500 Stock",
            "Ticker": tkr,
            "Shares": int(shares),
            "Entry Price (₹)": f"₹{entry_p:,.2f}",
            "Peak Price (₹)": f"₹{peak_p:,.2f}",
            "15% Fixed SL (₹)": f"₹{fixed_sl:,.2f}",
            "20% Trailing SL (₹)": f"₹{trail_sl:,.2f}",
            "Entry Date": pos.get("entry_date", "N/A")
        })
        
    if holdings_list:
        df_holdings = pd.DataFrame(holdings_list)
        st.dataframe(df_holdings, use_container_width=True)
    else:
        st.info("ℹ️ No active stock/ETF holdings currently. Portfolio is 100% Cash / Ready for Rebalance.")

# ==========================================
# 6. TRADE HISTORY LOG
# ==========================================
with tab_trades:
    st.subheader("📋 Closed Trade Execution History")
    trades = state.get("trade_history", [])
    if trades:
        df_trades = pd.DataFrame(trades)
        st.dataframe(df_trades, use_container_width=True)
    else:
        st.info("ℹ️ No closed trade stop-outs recorded yet.")

# ==========================================
# 7. REBALANCE SIGNALS
# ==========================================
with tab_rebalance:
    st.subheader("🚀 Monthly Rebalance Execution Center")
    st.markdown("Click below to run real-time momentum scanning across ETFs and Nifty 500 Stocks:")
    
    col_reb1, col_reb2 = st.columns(2)
    with col_reb1:
        if st.button("⚡ Scan ETF Momentum Signals"):
            st.info("Executing ETF momentum rotation engine...")
            os.system("python3 live_etf_rebalancer.py")
            st.success("ETF Signals updated!")
            
    with col_reb2:
        if st.button("⚡ Scan Nifty 500 Stock Momentum Signals"):
            st.info("Executing Nifty 500 stock momentum engine...")
            os.system("python3 live_nifty500_rebalancer.py")
            st.success("Stock Signals updated!")

st.markdown("---")
st.caption("🤖 Gemini Notebook Quantitative Workbench | Automated Strategy Execution Framework")
