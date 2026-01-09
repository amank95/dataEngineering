"""
Data Engineering Pipeline Dashboard
=====================================
Streamlit dashboard to showcase pipeline health, data quality, and analytics.

Usage:
    streamlit run dashboard.py

Features:
- Real-time pipeline health monitoring
- Data quality metrics
- Feature engineering validation
- API connectivity status
- Interactive data exploration
"""

import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import os
import threading
import time
from typing import Any, Dict, Optional
from dotenv import load_dotenv

try:
    from supabase import create_client, Client  # type: ignore
except ImportError:  # pragma: no cover
    create_client = None
    Client = None

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Data Engineering Pipeline Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .status-good {
        color: #28a745;
        font-weight: bold;
    }
    .status-warning {
        color: #ffc107;
        font-weight: bold;
    }
    .status-error {
        color: #dc3545;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# API Configuration
API_BASE_URL = os.getenv('API_BASE_URL', 'http://127.0.0.1:8000')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

_SUPABASE_CLIENT = None


def get_supabase_client():
    """Lazily create a Supabase client for dashboard-only reads."""
    global _SUPABASE_CLIENT
    if _SUPABASE_CLIENT is not None:
        return _SUPABASE_CLIENT

    if not create_client or not SUPABASE_URL or not SUPABASE_KEY:
        return None

    try:
        _SUPABASE_CLIENT = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        _SUPABASE_CLIENT = None
    return _SUPABASE_CLIENT

# In-memory live buffers (thread-safe) for real-time monitor.
# Background threads write here; Streamlit UI copies into st.session_state.
LIVE_BUFFERS: dict[str, list[dict]] = {}
LIVE_BUFFERS_LOCK = threading.Lock()

# Helper Functions
@st.cache_data(ttl=60)
def check_api_health():
    """Check if API is running and healthy."""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            return True, response.json()
        return False, None
    except Exception as e:
        return False, str(e)


@st.cache_data(ttl=60)
def get_model_health_status(window_hours: int = 24) -> Optional[Dict[str, Any]]:
    """
    Fetch high-level model health from the model_health_alerts table via Supabase.
    Returns None if Supabase is not configured.
    """
    client = get_supabase_client()
    if not client:
        return None

    try:
        since = (datetime.utcnow() - timedelta(hours=window_hours)).isoformat()
        resp = client.table("model_health_alerts") \
            .select("id,ticker,feature,p_value,detected_at") \
            .gte("detected_at", since) \
            .limit(50) \
            .order("detected_at", desc=True) \
            .execute()
        alerts = resp.data or []
        has_drift = len(alerts) > 0
        return {
            "status": "drifted" if has_drift else "stable",
            "has_drift": has_drift,
            "recent_alerts": len(alerts),
            "latest_alert": alerts[0] if alerts else None,
        }
    except Exception as exc:
        st.warning(f"Model health status unavailable: {exc}")
        return None

@st.cache_data(ttl=300)
def get_latest_data(limit=10):
    """Fetch latest data from API."""
    try:
        response = requests.get(f"{API_BASE_URL}/supabase/latest?limit={limit}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return pd.DataFrame(data.get('data', []))
        return None
    except Exception as e:
        st.error(f"Error fetching latest data: {e}")
        return None

@st.cache_data(ttl=300)
def get_ticker_data(ticker, days=30):
    """Fetch recent data for a specific ticker."""
    try:
        response = requests.get(f"{API_BASE_URL}/supabase/recent/{ticker}?days={days}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return pd.DataFrame(data.get('data', []))
        return None
    except Exception as e:
        st.error(f"Error fetching ticker data: {e}")
        return None

@st.cache_data(ttl=300)
def get_ticker_stats(ticker, start_date, end_date):
    """Get statistical summary for a ticker."""
    try:
        response = requests.get(
            f"{API_BASE_URL}/supabase/stats/{ticker}",
            params={"start_date": start_date, "end_date": end_date},
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get('stats', {})
        return None
    except Exception as e:
        st.error(f"Error fetching stats: {e}")
        return None

def run_pipeline():
    """Trigger pipeline execution."""
    try:
        with st.spinner("Running pipeline... This may take several minutes."):
            response = requests.post(f"{API_BASE_URL}/run-pipeline", timeout=600)
            if response.status_code == 200:
                return True, response.json()
            return False, response.text
    except Exception as e:
        return False, str(e)


def fetch_latest_price(ticker: str) -> float:
    """
    Fetch latest traded price (LTP) for a ticker for live monitoring.
    Uses high-frequency HTTP polling to the existing API and falls back to
    recent historical data if needed.
    """
    try:
        resp = requests.get(
            f"{API_BASE_URL}/supabase/recent/{ticker}",
            params={"days": 1},
            timeout=3,
        )
        if resp.status_code == 200:
            payload = resp.json()
            data = payload.get("data") or []
            if data:
                return float(data[-1].get("close"))
    except Exception:
        pass

    # Fallback to last point from standard ticker endpoint
    try:
        df = get_ticker_data(ticker, days=1)
        if df is not None and not df.empty and 'close' in df.columns:
            return float(df['close'].iloc[-1])
    except Exception:
        pass

    return float(100.0)


class LiveMonitor:
    """
    Background monitor that streams LTP for a single ticker into LIVE_BUFFERS.
    Does not touch Streamlit APIs, so it cannot block the main app or pipeline.
    """

    def __init__(self, ticker: str, interval: float = 1.0, buffer_size: int = 100):
        self.ticker = ticker
        self.interval = float(max(0.2, interval))
        self.buffer_size = max(10, int(buffer_size))
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self) -> None:
        if self.is_running:
            return
        self._stop_event.clear()
        self._running = True
        with LIVE_BUFFERS_LOCK:
            LIVE_BUFFERS.setdefault(self.ticker, [])
        self._thread = threading.Thread(
            target=self._run_loop, name=f"LiveMonitor-{self.ticker}", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running and self._thread is not None and self._thread.is_alive()

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                price = fetch_latest_price(self.ticker)
                ts = datetime.utcnow().isoformat()
                with LIVE_BUFFERS_LOCK:
                    buf = list(LIVE_BUFFERS.get(self.ticker, []))
                    buf.append({"ts": ts, "price": float(price)})
                    LIVE_BUFFERS[self.ticker] = buf[-self.buffer_size:]
            except Exception:
                pass
            time.sleep(self.interval)


@st.fragment
def live_monitor_fragment(ticker: str, buffer_key: str):
    """
    Live-updating section showing a large LTP metric and last 100 ticks.
    Uses st.session_state as the primary buffer for the UI.
    """
    refresh_interval = float(st.session_state.get("live_refresh_interval", 1.0))

    st.subheader(f"📡 Live Monitor — {ticker}")

    # Copy from global buffer into session_state
    with LIVE_BUFFERS_LOCK:
        raw_buf = list(LIVE_BUFFERS.get(ticker, []))
    st.session_state[buffer_key] = raw_buf
    buffer = raw_buf

    if not buffer:
        st.info("Waiting for live price ticks...")
    else:
        df_live = pd.DataFrame(buffer[-100:])
        if not df_live.empty:
            df_live["ts"] = pd.to_datetime(df_live["ts"])
            df_live.sort_values("ts", inplace=True)

            last_price = float(df_live["price"].iloc[-1])
            prev_price = float(df_live["price"].iloc[-2]) if len(df_live) > 1 else None
            delta = f"{(last_price - prev_price):+.2f}" if prev_price is not None else None

            c1, c2 = st.columns([1, 3])
            with c1:
                st.metric("LTP (₹)", f"{last_price:,.2f}", delta)
            with c2:
                fig = go.Figure()
                fig.add_trace(
                    go.Scatter(
                        x=df_live["ts"],
                        y=df_live["price"],
                        mode="lines+markers",
                        name="LTP",
                        line=dict(color="#1f77b4", width=2),
                    )
                )
                fig.update_layout(
                    height=260,
                    margin=dict(l=10, r=10, t=10, b=40),
                    xaxis_title="Time",
                    yaxis_title="Price (₹)",
                    template="plotly_dark",
                )
                st.plotly_chart(fig, use_container_width=True)

    st.caption(f"Last refresh: {datetime.now().strftime('%H:%M:%S')}")

    # Lightweight auto-refresh of this fragment only
    time.sleep(max(0.5, refresh_interval))
    try:
        st.experimental_rerun()
    except Exception:
        pass

# Main Dashboard
def main():
    # Header
    st.markdown('<h1 class="main-header">📊 Data Engineering Pipeline Dashboard</h1>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        st.markdown(f"**API Endpoint:** `{API_BASE_URL}`")
        
        # API Health Check
        is_healthy, health_data = check_api_health()
        if is_healthy:
            st.success("✅ API Connected")
            if health_data:
                st.json(health_data)
        else:
            st.error("❌ API Disconnected")
            st.warning("Make sure the API is running: `python run_all.py --start-api`")
            st.stop()
        
        st.divider()
        
        # Pipeline Control
        st.header("🔄 Pipeline Control")
        if st.button("▶️ Run Pipeline", use_container_width=True):
            success, result = run_pipeline()
            if success:
                st.success("Pipeline completed successfully!")
                st.json(result)
                st.cache_data.clear()
            else:
                st.error(f"Pipeline failed: {result}")
        
        st.divider()
        
        # Refresh Control
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    # Main Content
    tabs = st.tabs(["📈 Overview", "🔍 Data Explorer", "📊 Analytics", "🎯 Data Quality"])
    
    # Tab 1: Overview
    with tabs[0]:
        st.header("Pipeline Health & Status")
        
        # Metrics Row
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                label="API Status",
                value="Healthy" if is_healthy else "Down",
                delta="Connected" if is_healthy else "Disconnected"
            )
        
        with col2:
            parquet_exists = health_data.get('parquet_file_exists', False) if health_data else False
            st.metric(
                label="Parquet File",
                value="Available" if parquet_exists else "Missing",
                delta="Ready" if parquet_exists else "Run Pipeline"
            )
        
        with col3:
            supabase_enabled = health_data.get('supabase_enabled', False) if health_data else False
            st.metric(
                label="Supabase",
                value="Enabled" if supabase_enabled else "Disabled",
                delta="Connected" if supabase_enabled else "Not Configured"
            )
        
        with col4:
            has_data = health_data.get('supabase_has_data', False) if health_data else False
            st.metric(
                label="Data Status",
                value="Populated" if has_data else "Empty",
                delta="Ready" if has_data else "Sync Required"
            )

        # Model health metric (based on model_health_alerts Supabase table)
        model_health = get_model_health_status()
        with col5:
            if model_health is None:
                st.metric("Model Health", "Unknown", delta="No Supabase")
            else:
                status = model_health.get("status", "stable")
                has_drift = model_health.get("has_drift", False)
                label = "Stable" if not has_drift else "Drift Detected"
                delta = "Green" if not has_drift else "Red"
                st.metric("Model Health", label, delta=delta)
        
        st.divider()
        
        # Latest Data Preview
        st.subheader("📋 Latest Data Snapshot")
        latest_df = get_latest_data(limit=20)
        
        if latest_df is not None and not latest_df.empty:
            st.dataframe(
                latest_df[['ticker', 'date', 'close', 'daily_return', 'rsi_14', 'updated_at']],
                use_container_width=True,
                hide_index=True
            )
            
            # Quick Stats
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Tickers", len(latest_df['ticker'].unique()))
            with col2:
                avg_return = latest_df['daily_return'].mean()
                st.metric("Avg Daily Return", f"{avg_return:.4f}%")
            with col3:
                avg_rsi = latest_df['rsi_14'].mean()
                st.metric("Avg RSI", f"{avg_rsi:.2f}")
        else:
            st.warning("No data available. Run the pipeline to populate data.")
    
    # Tab 2: Data Explorer
    with tabs[1]:
        st.header("🔍 Interactive Data Explorer")
        
        # Ticker Selection
        col1, col2 = st.columns([1, 1])
        
        with col1:
            ticker = st.text_input("Enter Ticker Symbol", value="RELIANCE.NS", help="Example: RELIANCE.NS, TCS.NS")
        
        with col2:
            days = st.slider("Days of History", min_value=7, max_value=365, value=60)
        
        if ticker:
            ticker_df = get_ticker_data(ticker, days)
            
            if ticker_df is not None and not ticker_df.empty:
                # Price Chart with optional smoothing
                st.subheader(f"📈 {ticker} - Price History")

                # Smoothing controls (client-side only, does not touch API or ETL)
                with st.expander("🎛 Chart Smoothing Options", expanded=False):
                    smoothing_type = st.selectbox(
                        "Smoothing Type",
                        ["None", "Simple Moving Average (SMA)", "Exponential Moving Average (EMA)"],
                        index=2,  # Default to EMA for a more \"pro\" look
                        help="Applies a client-side smoothing line on top of the raw close prices."
                    )
                    window = st.slider(
                        "Smoothing Window (periods)",
                        min_value=3,
                        max_value=min(60, len(ticker_df)),
                        value=min(20, max(3, len(ticker_df) // 4)),
                        help="Number of recent points to smooth over. This only affects the overlay line."
                    )

                # Ensure data is sorted by date
                ticker_df_sorted = ticker_df.sort_values("date").reset_index(drop=True)

                # Base price line
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=ticker_df_sorted['date'],
                    y=ticker_df_sorted['close'],
                    mode='lines',
                    name='Close Price',
                    line=dict(color='#1f77b4', width=1.8)
                ))

                # Optional smoothing overlays (computed in-memory for the current view only)
                if smoothing_type == "Simple Moving Average (SMA)" and len(ticker_df_sorted) >= window:
                    sma = ticker_df_sorted['close'].rolling(window=window, min_periods=1).mean()
                    fig.add_trace(go.Scatter(
                        x=ticker_df_sorted['date'],
                        y=sma,
                        mode='lines',
                        name=f"SMA ({window})",
                        line=dict(color='#ff7f0e', width=2.2)
                    ))
                elif smoothing_type == "Exponential Moving Average (EMA)" and len(ticker_df_sorted) >= window:
                    ema = ticker_df_sorted['close'].ewm(span=window, adjust=False).mean()
                    fig.add_trace(go.Scatter(
                        x=ticker_df_sorted['date'],
                        y=ema,
                        mode='lines',
                        name=f"EMA ({window})",
                        line=dict(color='#2ca02c', width=2.2)
                    ))

                fig.update_layout(
                    title=f"{ticker} Closing Price",
                    xaxis_title="Date",
                    yaxis_title="Price (₹)",
                    hovermode='x unified',
                    template='plotly_white'
                )

                st.plotly_chart(fig, use_container_width=True)

                # Live Monitor section (auto-start background thread)
                st.markdown("---")
                st.subheader("📡 Live Ticker Monitor (Last 100 ticks)")

                # Set refresh interval and keep in session_state
                refresh_interval = st.slider(
                    "Live refresh interval (seconds)",
                    min_value=0.5,
                    max_value=5.0,
                    value=float(st.session_state.get("live_refresh_interval", 1.0)),
                    step=0.5,
                    key="live_refresh_slider_main",
                )
                st.session_state["live_refresh_interval"] = float(refresh_interval)

                # Initialize and auto-start per-ticker LiveMonitor
                if "live_monitors" not in st.session_state:
                    st.session_state["live_monitors"] = {}
                monitors = st.session_state["live_monitors"]
                if ticker not in monitors:
                    monitors[ticker] = LiveMonitor(ticker, interval=refresh_interval)
                monitor: LiveMonitor = monitors[ticker]
                monitor.interval = float(refresh_interval)
                if not monitor.is_running:
                    monitor.start()

                buffer_key = f"live_buffer_{ticker}"
                live_monitor_fragment(ticker, buffer_key)

                # Technical Indicators
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📊 RSI Indicator")
                    fig_rsi = go.Figure()
                    fig_rsi.add_trace(go.Scatter(
                        x=ticker_df['date'],
                        y=ticker_df['rsi_14'],
                        mode='lines',
                        name='RSI',
                        line=dict(color='#ff7f0e', width=2)
                    ))
                    fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought")
                    fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold")
                    fig_rsi.update_layout(
                        xaxis_title="Date",
                        yaxis_title="RSI",
                        template='plotly_white'
                    )
                    st.plotly_chart(fig_rsi, use_container_width=True)
                
                with col2:
                    st.subheader("📉 Daily Returns")
                    fig_returns = go.Figure()
                    fig_returns.add_trace(go.Bar(
                        x=ticker_df['date'],
                        y=ticker_df['daily_return'],
                        name='Daily Return',
                        marker_color=ticker_df['daily_return'].apply(lambda x: 'green' if x > 0 else 'red')
                    ))
                    fig_returns.update_layout(
                        xaxis_title="Date",
                        yaxis_title="Return (%)",
                        template='plotly_white'
                    )
                    st.plotly_chart(fig_returns, use_container_width=True)
                
                # Raw Data Table
                with st.expander("📄 View Raw Data"):
                    st.dataframe(ticker_df, use_container_width=True, hide_index=True)
            else:
                st.warning(f"No data found for ticker: {ticker}")
    
    # Tab 3: Analytics
    with tabs[2]:
        st.header("📊 Advanced Analytics")
        
        # Date Range Selection
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            ticker_analytics = st.text_input("Ticker for Analytics", value="RELIANCE.NS", key="analytics_ticker")
        
        with col2:
            start_date = st.date_input("Start Date", value=datetime.now() - timedelta(days=90))
        
        with col3:
            end_date = st.date_input("End Date", value=datetime.now())
        
        if ticker_analytics and start_date and end_date:
            stats = get_ticker_stats(ticker_analytics, str(start_date), str(end_date))
            
            if stats:
                st.subheader(f"📈 Statistical Summary: {ticker_analytics}")
                
                # Metrics Grid
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Trading Days", stats.get('total_days', 'N/A'))
                
                with col2:
                    avg_return = stats.get('avg_return', 0)
                    st.metric("Avg Daily Return", f"{avg_return:.4f}%", delta=f"{'Positive' if avg_return > 0 else 'Negative'}")
                
                with col3:
                    std_return = stats.get('std_return', 0)
                    st.metric("Volatility (Std Dev)", f"{std_return:.4f}%")
                
                with col4:
                    price_change = stats.get('price_change_pct', 0)
                    st.metric("Price Change", f"{price_change:.2f}%", delta=f"{'Up' if price_change > 0 else 'Down'}")
                
                # Additional Metrics
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Avg RSI", f"{stats.get('avg_rsi', 0):.2f}")
                
                with col2:
                    avg_volume = stats.get('avg_volume', 0)
                    st.metric("Avg Volume", f"{avg_volume:,.0f}")
                
                with col3:
                    sharpe_approx = avg_return / std_return if std_return > 0 else 0
                    st.metric("Sharpe Ratio (Approx)", f"{sharpe_approx:.2f}")
            else:
                st.warning("Unable to fetch statistics. Check ticker symbol and date range.")
    
    # Tab 4: Data Quality
    with tabs[3]:
        st.header("🎯 Data Quality Metrics")
        
        latest_df = get_latest_data(limit=100)
        
        if latest_df is not None and not latest_df.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📊 Completeness Check")
                
                # Calculate null percentages
                null_counts = latest_df.isnull().sum()
                total_rows = len(latest_df)
                
                completeness_data = pd.DataFrame({
                    'Column': null_counts.index,
                    'Null Count': null_counts.values,
                    'Completeness %': ((total_rows - null_counts.values) / total_rows * 100).round(2)
                })
                
                st.dataframe(completeness_data, use_container_width=True, hide_index=True)
                
                # Overall Quality Score
                avg_completeness = completeness_data['Completeness %'].mean()
                st.metric("Overall Data Quality Score", f"{avg_completeness:.2f}%")
            
            with col2:
                st.subheader("📈 Data Freshness")
                
                if 'updated_at' in latest_df.columns:
                    latest_df['updated_at'] = pd.to_datetime(latest_df['updated_at'])
                    most_recent = latest_df['updated_at'].max()
                    oldest = latest_df['updated_at'].min()
                    
                    st.metric("Most Recent Update", most_recent.strftime("%Y-%m-%d %H:%M:%S"))
                    st.metric("Oldest Record", oldest.strftime("%Y-%m-%d %H:%M:%S"))
                    
                    # Freshness indicator
                    time_diff = datetime.now() - most_recent.replace(tzinfo=None)
                    hours_old = time_diff.total_seconds() / 3600
                    
                    if hours_old < 24:
                        st.success(f"✅ Data is fresh ({hours_old:.1f} hours old)")
                    elif hours_old < 72:
                        st.warning(f"⚠️ Data is moderately stale ({hours_old:.1f} hours old)")
                    else:
                        st.error(f"❌ Data is stale ({hours_old:.1f} hours old)")
                else:
                    st.info("Timestamp information not available")
            
            # Data Distribution
            st.subheader("📊 Feature Distribution Analysis")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if 'daily_return' in latest_df.columns:
                    fig_dist = px.histogram(
                        latest_df,
                        x='daily_return',
                        nbins=30,
                        title='Daily Return Distribution',
                        labels={'daily_return': 'Daily Return (%)'}
                    )
                    st.plotly_chart(fig_dist, use_container_width=True)
            
            with col2:
                if 'rsi_14' in latest_df.columns:
                    fig_rsi_dist = px.histogram(
                        latest_df,
                        x='rsi_14',
                        nbins=20,
                        title='RSI Distribution',
                        labels={'rsi_14': 'RSI Value'}
                    )
                    st.plotly_chart(fig_rsi_dist, use_container_width=True)
        else:
            st.warning("No data available for quality analysis.")
    
    # Footer
    st.divider()
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 1rem;'>
        <p>Data Engineering Pipeline Dashboard | Built with Streamlit</p>
        <p>API Status: <span class='status-good'>●</span> Connected</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
