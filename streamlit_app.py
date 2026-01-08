"""
Real-Time Market Data MLOps Monitor
====================================
Enterprise-grade Streamlit dashboard for monitoring data pipeline health,
detecting drift, and demonstrating closed-loop MLOps system.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import numpy as np

from dashboard_utils import (
    fetch_system_health,
    fetch_pipeline_metrics,
    fetch_data_quality,
    fetch_drift_detection,
    fetch_stock_data,
    get_status_emoji,
    format_timestamp,
    format_metric_value
)
from config_loader import get_config

# ============================================
# Page Configuration
# ============================================
st.set_page_config(
    page_title="MLOps Monitor",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# Custom CSS - Dark Mode Bloomberg Style
# ============================================
st.markdown("""
<style>
    /* Main background */
    .stApp {
        background-color: #0E1117;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #FAFAFA;
        font-weight: 600;
    }
    
    /* Metric cards */
    [data-testid="stMetricValue"] {
        font-size: 28px;
        font-weight: 700;
    }
    
    /* Status indicators */
    .status-healthy {
        color: #00FF41;
        font-weight: bold;
        font-size: 18px;
    }
    
    .status-unhealthy {
        color: #FF073A;
        font-weight: bold;
        font-size: 18px;
    }
    
    .status-warning {
        color: #FFA500;
        font-weight: bold;
        font-size: 18px;
    }
    
    /* Info boxes */
    .info-box {
        background-color: #1E1E1E;
        padding: 20px;
        border-radius: 10px;
        border-left: 4px solid #00FF41;
        margin: 10px 0;
    }
    
    .warning-box {
        background-color: #1E1E1E;
        padding: 20px;
        border-radius: 10px;
        border-left: 4px solid #FF073A;
        margin: 10px 0;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #1E1E1E;
    }
    
    /* Buttons */
    .stButton>button {
        background-color: #00FF41;
        color: #0E1117;
        font-weight: bold;
        border: none;
        padding: 10px 24px;
        border-radius: 5px;
    }
    
    .stButton>button:hover {
        background-color: #00CC33;
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# Load Configuration
# ============================================
config = get_config()
dashboard_config = config.get('dashboard', {})
drift_config = dashboard_config.get('drift_detection', {})
health_thresholds = dashboard_config.get('health_thresholds', {})

# ============================================
# Sidebar - Filters and Controls
# ============================================
st.sidebar.header("🎛️ Control Panel")

# Manual refresh button
if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")

# Stock selector
available_tickers = config.get('tickers', ['INFY.NS', 'TCS.NS'])
selected_ticker = st.sidebar.selectbox(
    "📈 Select Stock",
    available_tickers,
    index=0 if dashboard_config.get('default_ticker', 'INFY.NS') in available_tickers else 0
)

# Custom date range selector
st.sidebar.subheader("📅 Date Range")
col1, col2 = st.sidebar.columns(2)

default_start = dashboard_config.get('default_start_date', '2024-01-01')
default_end = dashboard_config.get('default_end_date', 'today')

# Parse default dates
if default_end.lower() in ['today', 'now', 'current']:
    default_end_date = datetime.now().date()
else:
    default_end_date = datetime.strptime(default_end, '%Y-%m-%d').date()

default_start_date = datetime.strptime(default_start, '%Y-%m-%d').date()

start_date = col1.date_input(
    "Start",
    value=default_start_date,
    max_value=datetime.now().date()
)

end_date = col2.date_input(
    "End",
    value=default_end_date,
    max_value=datetime.now().date()
)

# Drift detection configuration
st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Drift Detection")
baseline_window = st.sidebar.slider(
    "Baseline Window (days)",
    min_value=14,
    max_value=90,
    value=drift_config.get('baseline_window', 30)
)
current_window = st.sidebar.slider(
    "Current Window (days)",
    min_value=3,
    max_value=30,
    value=drift_config.get('current_window', 7)
)

st.sidebar.markdown("---")
st.sidebar.caption("💡 **Tip**: Use the refresh button to update all metrics")

# ============================================
# Main Dashboard
# ============================================

# Title and header
st.markdown("<h1 style='text-align: center;'>🚀 Real-Time Market Data MLOps Monitor</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #888;'>Enterprise-grade observability for financial data pipelines</p>", unsafe_allow_html=True)

st.markdown("---")

# ============================================
# 1. System Health Header
# ============================================
st.subheader("⚡ System Health Status")

# Fetch system health
health_data = fetch_system_health()
pipeline_metrics = fetch_pipeline_metrics()
quality_data = fetch_data_quality(selected_ticker)
drift_data = fetch_drift_detection(selected_ticker, baseline_window, current_window)

# Create three columns for status indicators
col1, col2, col3, col4 = st.columns(4)

# Data Freshness
with col1:
    freshness_status = health_data.get('data_freshness', {}).get('status', 'unknown')
    freshness_hours = health_data.get('data_freshness', {}).get('hours_since_update', 0)
    
    if freshness_status == 'fresh':
        st.markdown(f"<div class='status-healthy'>{get_status_emoji(freshness_status)} Data Freshness</div>", unsafe_allow_html=True)
        st.caption(f"Updated {freshness_hours:.1f}h ago")
    elif freshness_status == 'acceptable':
        st.markdown(f"<div class='status-warning'>{get_status_emoji(freshness_status)} Data Freshness</div>", unsafe_allow_html=True)
        st.caption(f"Updated {freshness_hours:.1f}h ago")
    else:
        st.markdown(f"<div class='status-unhealthy'>{get_status_emoji(freshness_status)} Data Freshness</div>", unsafe_allow_html=True)
        st.caption("Data is stale")

# Data Quality
with col2:
    quality_score = quality_data.get('quality_score', 0)
    quality_threshold = health_thresholds.get('quality_score_min', 80)
    
    if quality_score >= quality_threshold:
        st.markdown(f"<div class='status-healthy'>✅ Data Quality</div>", unsafe_allow_html=True)
        st.caption(f"Score: {quality_score:.1f}/100")
    elif quality_score >= 50:
        st.markdown(f"<div class='status-warning'>⚠️ Data Quality</div>", unsafe_allow_html=True)
        st.caption(f"Score: {quality_score:.1f}/100")
    else:
        st.markdown(f"<div class='status-unhealthy'>🚨 Data Quality</div>", unsafe_allow_html=True)
        st.caption(f"Score: {quality_score:.1f}/100")

# Drift Status
with col3:
    drift_status = drift_data.get('drift_status', 'unknown')
    z_score = drift_data.get('z_score', 0)
    
    if drift_status == 'normal':
        st.markdown(f"<div class='status-healthy'>{get_status_emoji(drift_status)} Drift Status</div>", unsafe_allow_html=True)
        st.caption(f"Z-score: {z_score:.2f}")
    else:
        st.markdown(f"<div class='status-unhealthy'>{get_status_emoji(drift_status)} Drift Detected</div>", unsafe_allow_html=True)
        st.caption(f"Z-score: {z_score:.2f}")

# Last Execution
with col4:
    last_exec = pipeline_metrics.get('last_execution')
    if last_exec:
        st.markdown(f"<div class='status-healthy'>⏱️ Last Execution</div>", unsafe_allow_html=True)
        st.caption(format_timestamp(last_exec))
    else:
        st.markdown(f"<div class='status-warning'>⏱️ Last Execution</div>", unsafe_allow_html=True)
        st.caption("No recent execution")

st.markdown("---")

# ============================================
# 2. Live Market & Feature Engineering Visualization
# ============================================
st.subheader(f"📊 Live Market Data & Feature Engineering - {selected_ticker}")

# Fetch stock data
stock_response = fetch_stock_data(
    selected_ticker,
    start_date.strftime('%Y-%m-%d'),
    end_date.strftime('%Y-%m-%d')
)

if 'error' not in stock_response and stock_response.get('data'):
    df = pd.DataFrame(stock_response['data'])
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
    # Create dual-axis chart
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3],
        subplot_titles=('Stock Price & RSI Indicator', 'RSI (Relative Strength Index)')
    )
    
    # Price line
    fig.add_trace(
        go.Scatter(
            x=df['date'],
            y=df['close'],
            name='Close Price',
            line=dict(color='#00FF41', width=2),
            hovertemplate='<b>Date</b>: %{x}<br><b>Price</b>: ₹%{y:.2f}<extra></extra>'
        ),
        row=1, col=1
    )
    
    # RSI indicator
    fig.add_trace(
        go.Scatter(
            x=df['date'],
            y=df['rsi_14'],
            name='RSI (14)',
            line=dict(color='#FFA500', width=2),
            hovertemplate='<b>Date</b>: %{x}<br><b>RSI</b>: %{y:.2f}<extra></extra>'
        ),
        row=2, col=1
    )
    
    # RSI reference lines
    fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5, row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=2, col=1)
    
    # Update layout
    fig.update_layout(
        height=600,
        plot_bgcolor='#0E1117',
        paper_bgcolor='#0E1117',
        font=dict(color='#FAFAFA'),
        hovermode='x unified',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    fig.update_xaxes(
        gridcolor='#2E2E2E',
        showgrid=True,
        title_text="Date",
        row=2, col=1
    )
    
    fig.update_yaxes(
        gridcolor='#2E2E2E',
        showgrid=True,
        title_text="Price (₹)",
        row=1, col=1
    )
    
    fig.update_yaxes(
        gridcolor='#2E2E2E',
        showgrid=True,
        title_text="RSI",
        row=2, col=1
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Info box
    st.markdown("""
    <div class='info-box'>
        <strong>💡 Feature Engineering for ML Models</strong><br>
        These engineered features (RSI, moving averages, volatility) are directly consumed by downstream ML models 
        for price prediction and trading signal generation. Real-time validation ensures model input quality.
    </div>
    """, unsafe_allow_html=True)
else:
    st.warning(f"⚠️ No data available for {selected_ticker} in the selected date range.")

st.markdown("---")

# ============================================
# 3. Data Engineering Metrics Panel
# ============================================
st.subheader("⚙️ Data Engineering Metrics")

col1, col2, col3 = st.columns(3)

with col1:
    latency = pipeline_metrics.get('latency_seconds', 0)
    latency_threshold = health_thresholds.get('latency_max_seconds', 5)
    delta_color = "normal" if latency <= latency_threshold else "inverse"
    st.metric(
        "Pipeline Latency",
        f"{latency:.2f}s",
        delta=f"{'✓' if latency <= latency_threshold else '⚠'} Target: <{latency_threshold}s",
        delta_color=delta_color
    )

with col2:
    throughput = pipeline_metrics.get('throughput_rows_per_second', 0)
    st.metric(
        "Throughput",
        f"{throughput:.2f} rows/s",
        delta="Real-time processing"
    )

with col3:
    total_rows = pipeline_metrics.get('total_rows_ingested', 0)
    st.metric(
        "Total Rows Ingested",
        f"{total_rows:,}",
        delta=f"{pipeline_metrics.get('tickers_processed', 0)} tickers"
    )

col4, col5, col6 = st.columns(3)

with col4:
    null_pct = quality_data.get('null_percentage', 0)
    delta_color = "normal" if null_pct < 1 else "inverse"
    st.metric(
        "Null Percentage",
        f"{null_pct:.2f}%",
        delta=f"{'✓' if null_pct < 1 else '⚠'} Target: <1%",
        delta_color=delta_color
    )

with col5:
    quality_score = quality_data.get('quality_score', 0)
    delta_color = "normal" if quality_score >= 80 else "inverse"
    st.metric(
        "Data Quality Score",
        f"{quality_score:.1f}/100",
        delta=f"{'✓' if quality_score >= 80 else '⚠'} Target: >80",
        delta_color=delta_color
    )

with col6:
    schema_status = quality_data.get('schema_validation', 'unknown')
    st.metric(
        "Schema Validation",
        f"{get_status_emoji(schema_status)} {schema_status.upper()}",
        delta="OHLC integrity check"
    )

st.markdown("---")

# ============================================
# 4. Drift Detection Panel (PRIMARY FEATURE)
# ============================================
st.subheader("🔍 Statistical Drift Detection")

if 'error' not in drift_data:
    # Drift status banner
    drift_status = drift_data.get('drift_status', 'unknown')
    z_score = drift_data.get('z_score', 0)
    
    if drift_status == 'normal':
        st.markdown(f"""
        <div class='info-box'>
            <h3 style='margin-top: 0;'>{get_status_emoji('normal')} Market Behavior Normal</h3>
            <p>Statistical analysis shows no significant drift in market behavior. 
            ML models can operate with confidence.</p>
            <p><strong>Z-Score:</strong> {z_score:.3f} (Threshold: {drift_config.get('z_score_threshold', 2.0)})</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class='warning-box'>
            <h3 style='margin-top: 0;'>{get_status_emoji('detected')} Statistical Drift Detected</h3>
            <p>Market behavior has shifted significantly from baseline. This indicates potential ML model 
            performance degradation and may require model recalibration.</p>
            <p><strong>Z-Score:</strong> {z_score:.3f} (Threshold: {drift_config.get('z_score_threshold', 2.0)})</p>
            <p><strong>Confidence:</strong> {drift_data.get('confidence_level', 'unknown').upper()}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Statistical comparison
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**📊 Baseline Statistics** (30-day window)")
        baseline_stats = drift_data.get('baseline_stats', {})
        st.write(f"- **Mean Return:** {baseline_stats.get('mean_return', 0):.4f}")
        st.write(f"- **Std Return:** {baseline_stats.get('std_return', 0):.4f}")
        st.write(f"- **Mean RSI:** {baseline_stats.get('mean_rsi', 0):.2f}")
        st.write(f"- **Std RSI:** {baseline_stats.get('std_rsi', 0):.2f}")
    
    with col2:
        st.markdown("**📈 Current Statistics** (7-day window)")
        current_stats = drift_data.get('current_stats', {})
        st.write(f"- **Mean Return:** {current_stats.get('mean_return', 0):.4f}")
        st.write(f"- **Mean RSI:** {current_stats.get('mean_rsi', 0):.2f}")
        st.write(f"- **Z-Score (Return):** {drift_data.get('z_score_return', 0):.3f}")
        st.write(f"- **Z-Score (RSI):** {drift_data.get('z_score_rsi', 0):.3f}")
    
    # Distribution visualization
    st.markdown("**📉 Distribution Comparison**")
    
    distribution_data = drift_data.get('distribution_data', {})
    baseline_returns = distribution_data.get('baseline', {}).get('returns', [])
    current_returns = distribution_data.get('current', {}).get('returns', [])
    
    if baseline_returns and current_returns:
        fig_dist = go.Figure()
        
        # Baseline histogram
        fig_dist.add_trace(go.Histogram(
            x=baseline_returns,
            name='Baseline (30d)',
            opacity=0.7,
            marker_color='#00FF41',
            nbinsx=30
        ))
        
        # Current histogram
        fig_dist.add_trace(go.Histogram(
            x=current_returns,
            name='Current (7d)',
            opacity=0.7,
            marker_color='#FF073A' if drift_status == 'detected' else '#FFA500',
            nbinsx=30
        ))
        
        fig_dist.update_layout(
            barmode='overlay',
            title='Daily Returns Distribution',
            xaxis_title='Daily Return',
            yaxis_title='Frequency',
            plot_bgcolor='#0E1117',
            paper_bgcolor='#0E1117',
            font=dict(color='#FAFAFA'),
            height=400
        )
        
        fig_dist.update_xaxes(gridcolor='#2E2E2E', showgrid=True)
        fig_dist.update_yaxes(gridcolor='#2E2E2E', showgrid=True)
        
        st.plotly_chart(fig_dist, use_container_width=True)
    
    # Explanation
    st.info("""
    **🔄 What is Drift Detection?**
    
    Drift detection monitors statistical changes in market data that could impact ML model performance. 
    When market behavior shifts (regime change, volatility spike, etc.), models trained on historical 
    data may become less accurate. This system enables proactive model recalibration before performance degrades.
    """)
else:
    st.error(f"⚠️ Drift detection failed: {drift_data.get('error', 'Unknown error')}")

st.markdown("---")

# ============================================
# 5. MLOps Feedback Loop Explanation
# ============================================
st.subheader("🔄 Closed-Loop MLOps System")

st.markdown("""
<div class='info-box'>
    <h3 style='margin-top: 0;'>Enterprise MLOps Architecture</h3>
    <p>This system demonstrates a production-grade closed-loop MLOps pipeline:</p>
    <ul>
        <li><strong>Continuous Data Validation:</strong> Real-time OHLC validation, null checks, and schema enforcement</li>
        <li><strong>Feature Engineering Monitoring:</strong> Track RSI, moving averages, and volatility calculations</li>
        <li><strong>Statistical Drift Detection:</strong> Z-score analysis to identify market regime changes</li>
        <li><strong>Proactive Model Recalibration:</strong> Alerts trigger model retraining workflows</li>
        <li><strong>End-to-End Observability:</strong> Pipeline latency, throughput, and quality metrics</li>
    </ul>
    <p><strong>Result:</strong> A self-monitoring system that closes the loop between data engineering 
    and machine learning, ensuring model reliability in production.</p>
</div>
""", unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<p style='text-align: center; color: #666; font-size: 12px;'>
    Real-Time Market Data MLOps Monitor | Built with Streamlit & FastAPI | 
    Data Source: Supabase | Last Updated: {}</p>
""".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), unsafe_allow_html=True)
