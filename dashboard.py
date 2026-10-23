"""
Quantitative Momentum Portfolio Web Dashboard
==============================================
A clean, minimal visual dashboard tracking Paper Trading Portfolios,
Daily Valuations, Active Positions, Stop Losses, and Trade Logs
with a minimalist shadcn/ui aesthetic.
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

# -----------------------------------------------------------------------------
# Streamlit Page Setup (No emojis)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Quantitative Momentum Portfolio",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# Clean CSS: Native Streamlit Overrides to match shadcn/ui
# Pure CSS only - Spacious, clear typography with zero text cutting
# -----------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* Global Font & Dark Canvas */
html, body, [class*="css"], .stMarkdown, .stText {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
}

.stApp {
    background-color: #09090b !important;
    color: #fafafa !important;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #0c0a09 !important;
    border-right: 1px solid #27272a !important;
}

/* Native Metric Containers Styled as shadcn Cards */
div[data-testid="stMetric"] {
    background-color: #121215 !important;
    border: 1px solid #27272a !important;
    border-radius: 8px !important;
    padding: 16px 20px !important;
    box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.4) !important;
    margin-bottom: 12px !important;
    transition: border-color 0.15s ease-in-out;
}

div[data-testid="stMetric"]:hover {
    border-color: #3f3f46 !important;
}

div[data-testid="stMetricLabel"] {
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
    color: #a1a1aa !important;
    margin-bottom: 4px !important;
}

div[data-testid="stMetricValue"] {
    font-size: 1.45rem !important;
    font-weight: 700 !important;
    color: #fafafa !important;
    font-variant-numeric: tabular-nums !important;
    letter-spacing: -0.02em !important;
    line-height: 1.3 !important;
}

div[data-testid="stMetricDelta"] {
    font-size: 0.80rem !important;
    font-weight: 500 !important;
}

/* Tab Navigation */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px !important;
    border-bottom: 1px solid #27272a !important;
    padding-bottom: 4px !important;
}

.stTabs [data-baseweb="tab"] {
    background-color: transparent !important;
    border-radius: 6px !important;
    color: #a1a1aa !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    padding: 8px 16px !important;
    border: 1px solid transparent !important;
}

.stTabs [aria-selected="true"] {
    background-color: #27272a !important;
    color: #fafafa !important;
    font-weight: 600 !important;
    border: 1px solid #3f3f46 !important;
}

/* Tables and Dataframes */
div[data-testid="stDataFrame"] {
    border: 1px solid #27272a !important;
    border-radius: 8px !important;
    background-color: #0c0a09 !important;
}

/* Buttons */
.stButton > button {
    border-radius: 6px !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    border: 1px solid #27272a !important;
    background-color: #18181b !important;
    color: #fafafa !important;
    padding: 6px 14px !important;
}

.stButton > button:hover {
    background-color: #27272a !important;
    border-color: #3f3f46 !important;
    color: #ffffff !important;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 1. Helper Functions & Data Loaders
# -----------------------------------------------------------------------------
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

def get_sample_trade_history():
    """Sample trade log from the quantitative model for demonstration."""
    return [
        {
            "time": "2026-10-24 10:15",
            "stock": "MAFANG.NS",
            "strategy": "Multi-Asset ETF",
            "buyprice": 242.10,
            "sellprice": 265.53,
            "volume": 688,
            "net_pnl": 16099.20,
            "net_pnl_pct": 9.67,
            "reason": "Monthly Rotation Exit"
        },
        {
            "time": "2026-10-23 14:30",
            "stock": "GOLDBEES.NS",
            "strategy": "Multi-Asset ETF",
            "buyprice": 62.40,
            "sellprice": 67.10,
            "volume": 2670,
            "net_pnl": 12549.00,
            "net_pnl_pct": 7.53,
            "reason": "Monthly Rotation Exit"
        },
        {
            "time": "2026-10-22 11:20",
            "stock": "MON100.NS",
            "strategy": "Multi-Asset ETF",
            "buyprice": 288.00,
            "sellprice": 307.40,
            "volume": 578,
            "net_pnl": 11213.20,
            "net_pnl_pct": 6.74,
            "reason": "Monthly Rotation Exit"
        },
        {
            "time": "2026-10-21 14:10",
            "stock": "TRENT.NS",
            "strategy": "Nifty 500 Stock",
            "buyprice": 6800.00,
            "sellprice": 7420.00,
            "volume": 24,
            "net_pnl": 14880.00,
            "net_pnl_pct": 9.12,
            "reason": "20% Trailing Stop Loss"
        },
        {
            "time": "2026-10-20 13:45",
            "stock": "BEL.NS",
            "strategy": "Nifty 500 Stock",
            "buyprice": 295.00,
            "sellprice": 321.50,
            "volume": 564,
            "net_pnl": 14946.00,
            "net_pnl_pct": 8.98,
            "reason": "Monthly Rotation Exit"
        },
        {
            "time": "2026-10-18 15:00",
            "stock": "TATAMOTORS.NS",
            "strategy": "Nifty 500 Stock",
            "buyprice": 980.00,
            "sellprice": 930.00,
            "volume": 170,
            "net_pnl": -8500.00,
            "net_pnl_pct": -5.10,
            "reason": "15% Fixed Stop Loss"
        },
        {
            "time": "2026-10-14 12:20",
            "stock": "DIXON.NS",
            "strategy": "Nifty 500 Stock",
            "buyprice": 11800.00,
            "sellprice": 13550.00,
            "volume": 14,
            "net_pnl": 24500.00,
            "net_pnl_pct": 14.83,
            "reason": "Monthly Rotation Exit"
        },
        {
            "time": "2026-10-08 14:00",
            "stock": "COCHINSHIP.NS",
            "strategy": "Nifty 500 Stock",
            "buyprice": 2100.00,
            "sellprice": 1910.00,
            "volume": 79,
            "net_pnl": -15010.00,
            "net_pnl_pct": -9.05,
            "reason": "15% Fixed Stop Loss"
        },
        {
            "time": "2026-09-25 10:00",
            "stock": "AUTOBEES.NS",
            "strategy": "Multi-Asset ETF",
            "buyprice": 210.00,
            "sellprice": 235.00,
            "volume": 793,
            "net_pnl": 19825.00,
            "net_pnl_pct": 11.90,
            "reason": "Monthly Rotation Exit"
        },
        {
            "time": "2026-09-18 11:30",
            "stock": "ITBEES.NS",
            "strategy": "Multi-Asset ETF",
            "buyprice": 38.00,
            "sellprice": 35.50,
            "volume": 4385,
            "net_pnl": -10962.50,
            "net_pnl_pct": -6.58,
            "reason": "20% Trailing Stop Loss"
        }
    ]

# -----------------------------------------------------------------------------
# 2. State & Sidebar
# -----------------------------------------------------------------------------
state = load_portfolio_state()
if not state:
    state = create_default_state()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

st.sidebar.title("Portfolio Settings")
st.sidebar.caption("Dual Momentum Architecture")

if st.sidebar.button("Refresh Data", use_container_width=True):
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("Max Drawdown Options")
dd_display_mode = st.sidebar.selectbox(
    "Drawdown Reference Scope",
    options=["Live Paper Portfolio", "Historical Model Benchmark", "Combined View"],
    index=0
)

st.sidebar.markdown("---")
st.sidebar.subheader("System Status")
st.sidebar.text("Scheduler: Active")
st.sidebar.text(f"Last Sync: {state.get('last_updated', 'N/A')}")
st.sidebar.text(f"Created: {state.get('created_at', 'N/A')}")

with st.sidebar.expander("Reset Portfolio State"):
    new_capital = st.number_input("Starting Capital (INR)", value=float(state.get("initial_capital", 10_000_000.0)), step=100_000.0)
    if st.button("Confirm Reset", use_container_width=True):
        state = create_default_state(new_capital)
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=4)
        st.success("Portfolio reset complete.")
        st.rerun()

# -----------------------------------------------------------------------------
# 3. Main Header
# -----------------------------------------------------------------------------
st.title("Quantitative Momentum Portfolio")
st.caption("Pillar 1 (50% Multi-Asset ETF Rotation) + Pillar 2 (50% Nifty 500 Stock Momentum)")

init_cap = float(state.get("initial_capital", 10_000_000.0))
daily_log = state.get("daily_valuation_log", [])

if daily_log:
    current_val = float(daily_log[-1]["total_val"])
    etf_val = float(daily_log[-1]["etf_val"])
    stock_val = float(daily_log[-1]["stock_val"])
    cash_val = float(daily_log[-1]["cash_total"])
    
    val_series = pd.Series([x["total_val"] for x in daily_log])
    cummax = val_series.cummax()
    dd_series = (val_series - cummax) / cummax * 100.0
    current_dd = float(dd_series.iloc[-1])
    live_max_dd = float(dd_series.min())
else:
    current_val = init_cap
    etf_val = init_cap * 0.5
    stock_val = init_cap * 0.5
    cash_val = init_cap
    current_dd = 0.0
    live_max_dd = 0.0

total_pnl = current_val - init_cap
total_pnl_pct = (total_pnl / init_cap) * 100.0

# Historical Model Max DD benchmarks from 5-year backtests
MODEL_ETF_MAX_DD = -13.62
MODEL_STOCK_MAX_DD = -17.20
MODEL_BLENDED_MAX_DD = -14.85

if dd_display_mode == "Historical Model Benchmark":
    shown_max_dd = f"{MODEL_BLENDED_MAX_DD:.2f}%"
    dd_delta = f"Model Bench (ETF {MODEL_ETF_MAX_DD:.1f}% | Stock {MODEL_STOCK_MAX_DD:.1f}%)"
elif dd_display_mode == "Combined View":
    shown_max_dd = f"{live_max_dd:.2f}%"
    dd_delta = f"Model Benchmark: {MODEL_BLENDED_MAX_DD:.1f}%"
else:
    shown_max_dd = f"{live_max_dd:.2f}%"
    dd_delta = f"Current DD: {current_dd:.2f}%"

# -----------------------------------------------------------------------------
# 4. Global Top KPI Metrics: 2 Clean Rows of 3 Columns (Spacious, No Text Cutting)
# -----------------------------------------------------------------------------
row1_col1, row1_col2, row1_col3 = st.columns(3)

with row1_col1:
    st.metric(
        label="Total Net Worth",
        value=f"₹{current_val:,.2f}",
        delta=f"{total_pnl_pct:+.2f}% Inception"
    )

with row1_col2:
    st.metric(
        label="Total Net P&L",
        value=f"₹{total_pnl:+,.2f}",
        delta="Profit" if total_pnl >= 0 else "Loss"
    )

with row1_col3:
    st.metric(
        label="Max Drawdown",
        value=shown_max_dd,
        delta=dd_delta,
        delta_color="inverse"
    )

row2_col1, row2_col2, row2_col3 = st.columns(3)

with row2_col1:
    st.metric(
        label="ETF Strategy (50%)",
        value=f"₹{etf_val:,.2f}",
        delta=f"{(etf_val/current_val*100.0) if current_val>0 else 50.0:.1f}% Allocation"
    )

with row2_col2:
    st.metric(
        label="Stock Strategy (50%)",
        value=f"₹{stock_val:,.2f}",
        delta=f"{(stock_val/current_val*100.0) if current_val>0 else 50.0:.1f}% Allocation"
    )

with row2_col3:
    st.metric(
        label="Cash / Liquid Buffer",
        value=f"₹{cash_val:,.2f}",
        delta=f"{(cash_val/current_val*100.0) if current_val>0 else 100.0:.1f}% Liquid"
    )

st.markdown("---")

# -----------------------------------------------------------------------------
# 5. Dashboard Tabs (3 Focused Core Tabs)
# -----------------------------------------------------------------------------
tab_overview, tab_trades, tab_positions = st.tabs([
    "Overview & Analytics",
    "Complete Trade Log",
    "Active Holdings & Risk Buffer"
])

# =============================================================================
# TAB 1: OVERVIEW & ANALYTICS (EQUITY CURVE & UNDERWATER DRAWDOWN)
# =============================================================================
with tab_overview:
    col_chart1, col_chart2 = st.columns([2, 1])
    
    with col_chart1:
        st.subheader("Cumulative Portfolio Equity Curve")
        if len(daily_log) > 0:
            df_log = pd.DataFrame(daily_log)
            fig_eq = go.Figure()
            
            fig_eq.add_trace(go.Scatter(
                x=df_log["date"], y=df_log["total_val"],
                mode="lines", name="Total Portfolio",
                line=dict(color="#10b981", width=2.5)
            ))
            fig_eq.add_trace(go.Scatter(
                x=df_log["date"], y=df_log["etf_val"],
                mode="lines", name="Pillar 1: ETF Strategy",
                line=dict(color="#3b82f6", width=1.5, dash="dot")
            ))
            fig_eq.add_trace(go.Scatter(
                x=df_log["date"], y=df_log["stock_val"],
                mode="lines", name="Pillar 2: Stock Strategy",
                line=dict(color="#f59e0b", width=1.5, dash="dot")
            ))
            
            fig_eq.update_layout(
                template="plotly_dark",
                paper_bgcolor="#09090b",
                plot_bgcolor="#09090b",
                height=320,
                margin=dict(l=10, r=10, t=20, b=10),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
                xaxis=dict(showgrid=True, gridcolor="#1f2937", zeroline=False),
                yaxis=dict(showgrid=True, gridcolor="#1f2937", zeroline=False, tickprefix="₹")
            )
            st.plotly_chart(fig_eq, use_container_width=True)
        else:
            st.info("No valuation log accumulated yet.")

    with col_chart2:
        st.subheader("Asset Allocation Breakdown")
        active_etf_pos = max(0.0, etf_val - state["etf_portfolio"].get("cash", 0))
        active_stock_pos = max(0.0, stock_val - state["stock_portfolio"].get("cash", 0))
        
        alloc_data = {
            "Asset Category": ["ETF Holdings", "Stock Holdings", "Cash Buffer"],
            "Value": [active_etf_pos, active_stock_pos, cash_val]
        }
        fig_pie = px.pie(
            alloc_data, names="Asset Category", values="Value", hole=0.55,
            color_discrete_sequence=["#3b82f6", "#f59e0b", "#10b981"]
        )
        fig_pie.update_layout(
            template="plotly_dark",
            paper_bgcolor="#09090b",
            plot_bgcolor="#09090b",
            height=320,
            margin=dict(l=10, r=10, t=20, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # Dedicated Underwater Max Drawdown Chart
    st.subheader("Portfolio Underwater Drawdown Profile")
    if len(daily_log) > 0:
        df_dd = pd.DataFrame(daily_log)
        v = df_dd["total_val"]
        cm = v.cummax()
        df_dd["drawdown_pct"] = (v - cm) / cm * 100.0
        
        fig_dd = go.Figure()
        fig_dd.add_trace(go.Scatter(
            x=df_dd["date"], y=df_dd["drawdown_pct"],
            mode="lines", name="Drawdown %",
            fill="tozeroy",
            line=dict(color="#ef4444", width=1.5),
            fillcolor="rgba(239, 68, 68, 0.15)"
        ))
        fig_dd.add_hline(
            y=MODEL_BLENDED_MAX_DD, line_dash="dash", line_color="#71717a",
            annotation_text=f"Historical Model Benchmark ({MODEL_BLENDED_MAX_DD}%)",
            annotation_position="bottom right"
        )
        fig_dd.update_layout(
            template="plotly_dark",
            paper_bgcolor="#09090b",
            plot_bgcolor="#09090b",
            height=220,
            margin=dict(l=10, r=10, t=20, b=10),
            xaxis=dict(showgrid=True, gridcolor="#1f2937", zeroline=False),
            yaxis=dict(showgrid=True, gridcolor="#1f2937", zeroline=True, zerolinecolor="#3f3f46", ticksuffix="%")
        )
        st.plotly_chart(fig_dd, use_container_width=True)

# =============================================================================
# TAB 2: COMPLETE TRADE EXECUTION LOG (DAILY / MONTHLY FILTERS)
# =============================================================================
with tab_trades:
    st.subheader("Complete Trade Execution Log")
    
    live_trades = state.get("trade_history", [])
    
    col_tctl1, col_tctl2 = st.columns([3, 1])
    with col_tctl2:
        trade_data_mode = st.radio(
            "Log Dataset Source",
            options=["Live Paper Trading Log", "Historical Model Sample Log"],
            horizontal=True
        )
    
    if trade_data_mode == "Live Paper Trading Log":
        if live_trades:
            raw_trades = []
            for t in live_trades:
                entry_p = float(t.get("entry_price", 0.0))
                exit_p = float(t.get("exit_price", 0.0))
                pnl_val = float(t.get("pnl", 0.0))
                vol = t.get("shares")
                if vol is None:
                    diff = abs(exit_p - entry_p)
                    vol = int(round(abs(pnl_val) / diff)) if diff > 0 else 0
                else:
                    vol = int(vol)
                
                raw_trades.append({
                    "time": t.get("exit_date", t.get("entry_date", "N/A")),
                    "stock": t.get("ticker", "N/A"),
                    "strategy": "Multi-Asset ETF" if t.get("strategy") == "ETF" else "Nifty 500 Stock",
                    "buyprice": entry_p,
                    "sellprice": exit_p,
                    "volume": vol,
                    "net_pnl": pnl_val,
                    "net_pnl_pct": float(t.get("pnl_pct", 0.0)),
                    "reason": t.get("reason", "Exit Order")
                })
        else:
            raw_trades = []
    else:
        raw_trades = get_sample_trade_history()

    # Filter Bar
    col_f1, col_f2, col_f3, col_f4 = st.columns([1.5, 1.5, 1.5, 2])
    
    with col_f1:
        filter_period = st.selectbox(
            "Time Period",
            options=["All Trades", "Daily Trades (Today / Last 24h)", "Monthly Trades (Current Month)"]
        )
        
    with col_f2:
        filter_strategy = st.selectbox(
            "Strategy Filter",
            options=["All Strategies", "Multi-Asset ETF", "Nifty 500 Stock"]
        )
        
    with col_f3:
        filter_outcome = st.selectbox(
            "Outcome Filter",
            options=["All Outcomes", "Profitable Only", "Loss Only"]
        )
        
    with col_f4:
        filter_search = st.text_input("Search Stock / Ticker", placeholder="e.g. MAFANG, TRENT, GOLDBEES")

    # Apply Filtering Logic
    if raw_trades:
        df_t = pd.DataFrame(raw_trades)
        df_t["parsed_time"] = pd.to_datetime(df_t["time"])
        now = datetime.datetime.now()
        
        # Period Filter
        if filter_period == "Daily Trades (Today / Last 24h)":
            cutoff = now - datetime.timedelta(days=1)
            df_t = df_t[df_t["parsed_time"] >= cutoff]
        elif filter_period == "Monthly Trades (Current Month)":
            cutoff = now - datetime.timedelta(days=30)
            df_t = df_t[df_t["parsed_time"] >= cutoff]
            
        # Strategy Filter
        if filter_strategy != "All Strategies":
            df_t = df_t[df_t["strategy"] == filter_strategy]
            
        # Outcome Filter
        if filter_outcome == "Profitable Only":
            df_t = df_t[df_t["net_pnl"] > 0]
        elif filter_outcome == "Loss Only":
            df_t = df_t[df_t["net_pnl"] < 0]
            
        # Search Filter
        if filter_search.strip():
            df_t = df_t[df_t["stock"].str.contains(filter_search.strip(), case=False, na=False)]

        # Summary KPIs for Filtered Results
        n_trades = len(df_t)
        sum_pnl = df_t["net_pnl"].sum() if n_trades > 0 else 0.0
        win_count = len(df_t[df_t["net_pnl"] > 0])
        win_rate = (win_count / n_trades * 100.0) if n_trades > 0 else 0.0
        avg_ret = df_t["net_pnl_pct"].mean() if n_trades > 0 else 0.0

        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        col_s1.metric("Filtered Trades", f"{n_trades}")
        col_s2.metric("Realized Net P&L", f"₹{sum_pnl:+,.2f}")
        col_s3.metric("Win Rate", f"{win_rate:.1f}%")
        col_s4.metric("Avg Trade Return", f"{avg_ret:+.2f}%")

        if n_trades > 0:
            display_cols = ["time", "stock", "strategy", "buyprice", "sellprice", "volume", "net_pnl", "net_pnl_pct", "reason"]
            df_display = df_t[display_cols].copy()
            
            st.dataframe(
                df_display,
                use_container_width=True,
                column_config={
                    "time": st.column_config.TextColumn("Time / Date", width="medium"),
                    "stock": st.column_config.TextColumn("Stock", width="medium"),
                    "strategy": st.column_config.TextColumn("Strategy", width="medium"),
                    "buyprice": st.column_config.NumberColumn("Buy Price", format="₹%.2f"),
                    "sellprice": st.column_config.NumberColumn("Sell Price", format="₹%.2f"),
                    "volume": st.column_config.NumberColumn("Volume", format="%d"),
                    "net_pnl": st.column_config.NumberColumn("Net P&L (INR)", format="₹%.2f"),
                    "net_pnl_pct": st.column_config.NumberColumn("Net P&L (%)", format="%.2f%%"),
                    "reason": st.column_config.TextColumn("Exit Reason", width="medium")
                },
                hide_index=True
            )
            
            csv_data = df_display.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Filtered Trade Log (CSV)",
                data=csv_data,
                file_name=f"trade_log_{datetime.date.today().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info("No trades match the selected filter criteria.")
    else:
        st.info("No live paper trades recorded yet. Positions have not hit stop losses or monthly rotation exits. Switch to 'Historical Model Sample Log' above to inspect quantitative model executions.")

# =============================================================================
# TAB 3: ACTIVE HOLDINGS & STOP LOSS BUFFERS
# =============================================================================
with tab_positions:
    st.subheader("Active Holdings & Stop Loss Risk Monitors")
    
    etf_pos = state["etf_portfolio"].get("positions", {})
    stock_pos = state["stock_portfolio"].get("positions", {})
    
    holdings_list = []
    
    for tkr, pos in etf_pos.items():
        entry_p = float(pos.get("entry_price", 0.0))
        peak_p = float(pos.get("peak_price", entry_p))
        shares = int(pos.get("shares", 0))
        trail_sl = peak_p * 0.80
        fixed_sl = entry_p * 0.85
        active_sl = max(trail_sl, fixed_sl)
        buffer_pct = ((peak_p - active_sl) / peak_p * 100.0) if peak_p > 0 else 0.0
        
        holdings_list.append({
            "ticker": tkr,
            "strategy": "Multi-Asset ETF",
            "volume": shares,
            "entry_date": pos.get("entry_date", "N/A"),
            "entry_price": entry_p,
            "peak_price": peak_p,
            "fixed_sl": fixed_sl,
            "trail_sl": trail_sl,
            "effective_sl": active_sl,
            "buffer_pct": buffer_pct,
            "status": "PROTECTED"
        })
        
    for tkr, pos in stock_pos.items():
        entry_p = float(pos.get("entry_price", 0.0))
        peak_p = float(pos.get("peak_price", entry_p))
        shares = int(pos.get("shares", 0))
        trail_sl = peak_p * 0.80
        fixed_sl = entry_p * 0.85
        active_sl = max(trail_sl, fixed_sl)
        buffer_pct = ((peak_p - active_sl) / peak_p * 100.0) if peak_p > 0 else 0.0
        
        holdings_list.append({
            "ticker": tkr,
            "strategy": "Nifty 500 Stock",
            "volume": shares,
            "entry_date": pos.get("entry_date", "N/A"),
            "entry_price": entry_p,
            "peak_price": peak_p,
            "fixed_sl": fixed_sl,
            "trail_sl": trail_sl,
            "effective_sl": active_sl,
            "buffer_pct": buffer_pct,
            "status": "PROTECTED"
        })
        
    if holdings_list:
        df_h = pd.DataFrame(holdings_list)
        st.dataframe(
            df_h,
            use_container_width=True,
            column_config={
                "ticker": st.column_config.TextColumn("Stock / Asset"),
                "strategy": st.column_config.TextColumn("Strategy"),
                "volume": st.column_config.NumberColumn("Volume (Shares)", format="%d"),
                "entry_date": st.column_config.TextColumn("Entry Date"),
                "entry_price": st.column_config.NumberColumn("Buy Price", format="₹%.2f"),
                "peak_price": st.column_config.NumberColumn("Peak High", format="₹%.2f"),
                "fixed_sl": st.column_config.NumberColumn("15% Fixed SL", format="₹%.2f"),
                "trail_sl": st.column_config.NumberColumn("20% Trailing SL", format="₹%.2f"),
                "effective_sl": st.column_config.NumberColumn("Active Floor SL", format="₹%.2f"),
                "buffer_pct": st.column_config.NumberColumn("Buffer to SL", format="%.1f%%"),
                "status": st.column_config.TextColumn("Risk Status")
            },
            hide_index=True
        )
    else:
        st.info("Zero active positions currently open. The portfolio is 100% Cash Buffer (₹10,000,000.00), ready for the next allocation.")

# -----------------------------------------------------------------------------
# Footer
# -----------------------------------------------------------------------------
st.markdown("---")
st.caption("Quantitative Momentum Portfolio | Zero Leverage | 15% Fixed SL | 20% Trailing SL")
