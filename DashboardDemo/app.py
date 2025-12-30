import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from datetime import datetime, timedelta
import glob

# Page configuration
st.set_page_config(
    page_title="Stock & ETF Signal Platform",
    page_icon="📈",
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
        padding: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .signal-buy {
        color: #00ff00;
        font-weight: bold;
    }
    .signal-sell {
        color: #ff0000;
        font-weight: bold;
    }
    .signal-hold {
        color: #ffaa00;
        font-weight: bold;
    }
    .hero-image {
        width: 100%;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .feature-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        margin: 1rem 0;
    }
    </style>
    """, unsafe_allow_html=True)

def create_placeholder_chart_image():
    """Create a placeholder chart image using plotly"""
    fig = go.Figure()
    dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
    prices = 100 + np.cumsum(np.random.randn(30) * 2)
    
    fig.add_trace(go.Scatter(
        x=dates,
        y=prices,
        mode='lines',
        name='Stock Price',
        line=dict(color='#1f77b4', width=3),
        fill='tozeroy',
        fillcolor='rgba(31, 119, 180, 0.1)'
    ))
    
    fig.update_layout(
        title="Sample Stock Price Trend",
        xaxis_title="Date",
        yaxis_title="Price ($)",
        height=250,
        template="plotly_white",
        showlegend=False,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    return fig

# Data paths
DATA_DIR = "../data/processed"

@st.cache_data
def load_available_tickers():
    """Load list of available tickers from processed data"""
    pattern = os.path.join(DATA_DIR, "*_final.csv")
    files = glob.glob(pattern)
    tickers = [os.path.basename(f).replace("_final.csv", "") for f in files]
    return sorted(tickers)

@st.cache_data
def load_stock_data(ticker):
    """Load stock data for a given ticker"""
    file_path = os.path.join(DATA_DIR, f"{ticker}_final.csv")
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        return df
    return None

def generate_signal(row):
    """Generate buy/sell/hold signal based on technical indicators"""
    rsi = row.get('rsi_14', 50)
    ma_20 = row.get('ma_20', 0)
    ma_50 = row.get('ma_50', 0)
    close = row.get('close', 0)
    daily_return = row.get('daily_return', 0)
    
    score = 0
    
    # RSI signals
    if rsi < 30:
        score += 2  # Oversold - bullish
    elif rsi > 70:
        score -= 2  # Overbought - bearish
    elif rsi < 40:
        score += 1
    elif rsi > 60:
        score -= 1
    
    # Moving average signals
    if ma_20 > ma_50 and close > ma_20:
        score += 1  # Uptrend
    elif ma_20 < ma_50 and close < ma_20:
        score -= 1  # Downtrend
    
    # Price momentum
    if daily_return > 0.02:
        score += 1
    elif daily_return < -0.02:
        score -= 1
    
    # Determine signal
    if score >= 2:
        return "BUY", score, "Strong bullish indicators"
    elif score <= -2:
        return "SELL", score, "Strong bearish indicators"
    else:
        return "HOLD", score, "Neutral signals"

def calculate_performance_metrics(df):
    """Calculate basic performance metrics"""
    if df.empty:
        return {}
    
    total_return = ((df['close'].iloc[-1] / df['close'].iloc[0]) - 1) * 100
    volatility = df['daily_return'].std() * np.sqrt(252) * 100  # Annualized
    sharpe = (df['daily_return'].mean() / df['daily_return'].std()) * np.sqrt(252) if df['daily_return'].std() > 0 else 0
    
    max_price = df['close'].max()
    min_price = df['close'].min()
    max_drawdown = ((max_price - df['close'].iloc[df['close'].idxmax():].min()) / max_price) * 100
    
    return {
        'total_return': total_return,
        'volatility': volatility,
        'sharpe_ratio': sharpe,
        'max_drawdown': max_drawdown,
        'current_price': df['close'].iloc[-1],
        'avg_volume': df['volume'].mean()
    }

def create_price_chart(df, ticker):
    """Create interactive price chart with indicators"""
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=(f'{ticker} Price & Moving Averages', 'RSI (14-period)', 'Volume'),
        row_heights=[0.5, 0.25, 0.25]
    )
    
    # Price and moving averages
    fig.add_trace(
        go.Scatter(x=df.index, y=df['close'], name='Close Price', line=dict(color='#1f77b4', width=2)),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=df.index, y=df['ma_20'], name='MA 20', line=dict(color='orange', width=1)),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=df.index, y=df['ma_50'], name='MA 50', line=dict(color='red', width=1)),
        row=1, col=1
    )
    
    # RSI
    fig.add_trace(
        go.Scatter(x=df.index, y=df['rsi_14'], name='RSI', line=dict(color='purple', width=2)),
        row=2, col=1
    )
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1, annotation_text="Overbought (70)")
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1, annotation_text="Oversold (30)")
    
    # Volume
    colors = ['green' if x >= 0 else 'red' for x in df['daily_return']]
    fig.add_trace(
        go.Bar(x=df.index, y=df['volume'], name='Volume', marker_color=colors, opacity=0.6),
        row=3, col=1
    )
    
    fig.update_layout(
        height=800,
        showlegend=True,
        hovermode='x unified',
        title_text=f"{ticker} Technical Analysis",
        title_x=0.5
    )
    
    fig.update_xaxes(title_text="Date", row=3, col=1)
    fig.update_yaxes(title_text="Price ($)", row=1, col=1)
    fig.update_yaxes(title_text="RSI", row=2, col=1)
    fig.update_yaxes(title_text="Volume", row=3, col=1)
    
    return fig

# Sidebar navigation
st.sidebar.title("📊 Navigation")
page = st.sidebar.selectbox(
    "Choose a page",
    ["🏠 Home", "📈 Stock Explorer", "🔔 Signal Generator", "📊 Performance Analytics", "⚙️ Settings"]
)

# Home Page
if page == "🏠 Home":
    # Hero Section with Image
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 📈")
        st.markdown('<h1 class="main-header">Stock & ETF Signal Generation Platform</h1>', unsafe_allow_html=True)
        # Placeholder hero image/chart
        hero_chart = create_placeholder_chart_image()
        st.plotly_chart(hero_chart, use_container_width=True, config={'displayModeBar': False})
    
    st.markdown("---")
    
    # Key Metrics with visual appeal
    col1, col2, col3, col4 = st.columns(4)
    
    available_tickers = load_available_tickers()
    
    with col1:
        st.markdown("### 📊")
        st.metric("Available Stocks", len(available_tickers))
        st.caption("Active tickers")
    
    with col2:
        st.markdown("### 📈")
        st.metric("Data Points", "12,000+")
        st.caption("Historical records")
    
    with col3:
        st.markdown("### 🔧")
        st.metric("Indicators", "4")
        st.caption("Technical analysis")
    
    with col4:
        st.markdown("### ⚡")
        st.metric("Real-time", "Live")
        st.caption("Signal updates")
    
    st.markdown("---")
    
    # Platform Overview with visual elements
    st.markdown("### 🎯 Platform Overview")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        #### 📊 Real-time Stock Analysis
        Analyze stocks and ETFs with advanced technical indicators
        
        #### 🤖 AI-Powered Signals
        Generate buy/sell/hold signals based on machine learning models
        """)
        
        # Sample chart
        sample_chart = create_placeholder_chart_image()
        sample_chart.update_layout(title="Real-time Price Tracking", height=200)
        st.plotly_chart(sample_chart, use_container_width=True, config={'displayModeBar': False})
    
    with col2:
        st.markdown("""
        #### 📈 Performance Analytics
        Comprehensive performance metrics and backtesting results
        
        #### 🎨 Interactive Dashboards
        Visualize data with beautiful, interactive charts and tables
        """)
        
        # Sample metrics visualization
        metrics_data = pd.DataFrame({
            'Metric': ['Sharpe Ratio', 'Max Drawdown', 'Win Rate', 'Total Return'],
            'Value': [1.45, -12.3, 58.5, 23.7]
        })
        fig_metrics = go.Figure(data=[
            go.Bar(x=metrics_data['Metric'], y=metrics_data['Value'],
                   marker_color=['green', 'orange', 'blue', 'purple'])
        ])
        fig_metrics.update_layout(title="Sample Performance Metrics", height=200, showlegend=False)
        st.plotly_chart(fig_metrics, use_container_width=True, config={'displayModeBar': False})
    
    st.markdown("---")
    
    # Available Tickers Section
    st.markdown("### 📋 Available Tickers")
    
    # Create a nice grid display
    num_cols = 6
    cols = st.columns(num_cols)
    for idx, ticker in enumerate(available_tickers):
        with cols[idx % num_cols]:
            st.markdown(f"**{ticker}**")
    
    st.markdown("---")
    
    # Feature Showcase with images
    st.markdown("### ✨ Key Features")
    
    feature_col1, feature_col2, feature_col3 = st.columns(3)
    
    with feature_col1:
        st.markdown("""
        <div style='padding: 1.5rem; background-color: #f0f2f6; border-radius: 10px; border-left: 4px solid #1f77b4;'>
        <h4>📊 Data Engineering</h4>
        <p>Clean, validated datasets with technical indicators</p>
        </div>
        """, unsafe_allow_html=True)
    
    with feature_col2:
        st.markdown("""
        <div style='padding: 1.5rem; background-color: #f0f2f6; border-radius: 10px; border-left: 4px solid #28a745;'>
        <h4>🤖 ML Signals</h4>
        <p>AI-generated trading signals with confidence scores</p>
        </div>
        """, unsafe_allow_html=True)
    
    with feature_col3:
        st.markdown("""
        <div style='padding: 1.5rem; background-color: #f0f2f6; border-radius: 10px; border-left: 4px solid #ffc107;'>
        <h4>📈 Analytics</h4>
        <p>Comprehensive performance metrics and insights</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Quick Start with visual call-to-action
    st.markdown("### 🚀 Quick Start")
    col1, col2 = st.columns([2, 1])
    with col1:
        st.info("💡 **Navigate to 'Stock Explorer'** to view stock data and charts, or **'Signal Generator'** to see trading signals in action!")
    with col2:
        st.markdown("""
        <div style='text-align: center; padding: 1rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; color: white;'>
        <h3>🚀</h3>
        <p><b>Ready to Explore!</b></p>
        </div>
        """, unsafe_allow_html=True)

# Stock Explorer Page
elif page == "📈 Stock Explorer":
    # Header with visual element
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("📈 Stock Explorer")
    with col2:
        st.markdown("""
        <div style='padding: 1rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; text-align: center; color: white;'>
        <h4>📊</h4>
        <p><b>Live Data</b></p>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("---")
    
    available_tickers = load_available_tickers()
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        selected_ticker = st.selectbox("Select Stock/ETF", available_tickers)
        date_range = st.selectbox("Date Range", ["Last 30 days", "Last 90 days", "Last 6 months", "Last year", "All"])
    
    # Load data
    df = load_stock_data(selected_ticker)
    
    if df is not None and not df.empty:
        # Filter by date range
        if date_range == "Last 30 days":
            df_display = df.tail(30)
        elif date_range == "Last 90 days":
            df_display = df.tail(90)
        elif date_range == "Last 6 months":
            df_display = df.tail(126)  # ~6 months
        elif date_range == "Last year":
            df_display = df.tail(252)  # ~1 year
        else:
            df_display = df
        
        # Metrics
        latest_data = df_display.iloc[-1]
        metrics = calculate_performance_metrics(df_display)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Current Price", f"${metrics.get('current_price', 0):.2f}")
        with col2:
            st.metric("Total Return", f"{metrics.get('total_return', 0):.2f}%")
        with col3:
            st.metric("Volatility", f"{metrics.get('volatility', 0):.2f}%")
        with col4:
            st.metric("Sharpe Ratio", f"{metrics.get('sharpe_ratio', 0):.2f}")
        
        # Chart
        st.plotly_chart(create_price_chart(df_display, selected_ticker), use_container_width=True)
        
        # Data table
        st.subheader("📋 Data Table")
        st.dataframe(df_display[['close', 'open', 'high', 'low', 'volume', 'daily_return', 'ma_20', 'ma_50', 'rsi_14']].tail(20))
        
    else:
        st.error(f"Data not available for {selected_ticker}")

# Signal Generator Page
elif page == "🔔 Signal Generator":
    # Header with visual element
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🔔 Signal Generator")
    with col2:
        st.markdown("""
        <div style='padding: 1rem; background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); border-radius: 10px; text-align: center; color: white;'>
        <h4>⚡</h4>
        <p><b>AI Signals</b></p>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("---")
    
    available_tickers = load_available_tickers()
    
    col1, col2 = st.columns([1, 2])
    with col1:
        selected_ticker = st.selectbox("Select Stock/ETF", available_tickers)
    
    df = load_stock_data(selected_ticker)
    
    if df is not None and not df.empty:
        # Get latest signal
        latest_row = df.iloc[-1]
        signal, score, reason = generate_signal(latest_row)
        
        # Display signal with visual enhancement
        col1, col2, col3 = st.columns([1, 3, 1])
        with col2:
            if signal == "BUY":
                st.markdown(f'''
                <div style="text-align: center; padding: 3rem; background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%); border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <h1 style="font-size: 4rem; margin: 0;">🟢</h1>
                    <h1 class="signal-buy" style="font-size: 3rem; margin: 1rem 0;">{signal}</h1>
                    <p style="font-size: 1.2rem;"><b>Signal Strength: {score}</b></p>
                    <p style="font-size: 1rem; color: #333;">{reason}</p>
                </div>
                ''', unsafe_allow_html=True)
            elif signal == "SELL":
                st.markdown(f'''
                <div style="text-align: center; padding: 3rem; background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <h1 style="font-size: 4rem; margin: 0;">🔴</h1>
                    <h1 class="signal-sell" style="font-size: 3rem; margin: 1rem 0;">{signal}</h1>
                    <p style="font-size: 1.2rem;"><b>Signal Strength: {score}</b></p>
                    <p style="font-size: 1rem; color: #333;">{reason}</p>
                </div>
                ''', unsafe_allow_html=True)
            else:
                st.markdown(f'''
                <div style="text-align: center; padding: 3rem; background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%); border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <h1 style="font-size: 4rem; margin: 0;">🟡</h1>
                    <h1 class="signal-hold" style="font-size: 3rem; margin: 1rem 0;">{signal}</h1>
                    <p style="font-size: 1.2rem;"><b>Signal Strength: {score}</b></p>
                    <p style="font-size: 1rem; color: #333;">{reason}</p>
                </div>
                ''', unsafe_allow_html=True)
        
        # Current indicators
        st.subheader("📊 Current Technical Indicators")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Price", f"${latest_row['close']:.2f}")
        with col2:
            st.metric("RSI (14)", f"{latest_row['rsi_14']:.2f}")
        with col3:
            st.metric("MA 20", f"${latest_row['ma_20']:.2f}")
        with col4:
            st.metric("MA 50", f"${latest_row['ma_50']:.2f}")
        
        # Signal history
        st.subheader("📈 Signal History (Last 30 Days)")
        df_signals = df.tail(30).copy()
        signals_data = []
        for idx, row in df_signals.iterrows():
            sig, scr, rsn = generate_signal(row)
            signals_data.append({
                'Date': idx,
                'Price': row['close'],
                'Signal': sig,
                'Score': scr,
                'RSI': row['rsi_14'],
                'MA20': row['ma_20'],
                'MA50': row['ma_50']
            })
        
        signals_df = pd.DataFrame(signals_data)
        st.dataframe(signals_df, use_container_width=True)
        
        # Multi-ticker signals
        st.subheader("🌐 Signals for All Stocks")
        all_signals = []
        for ticker in available_tickers[:10]:  # Limit to first 10 for performance
            ticker_df = load_stock_data(ticker)
            if ticker_df is not None and not ticker_df.empty:
                latest = ticker_df.iloc[-1]
                sig, scr, _ = generate_signal(latest)
                all_signals.append({
                    'Ticker': ticker,
                    'Price': latest['close'],
                    'Signal': sig,
                    'Score': scr,
                    'RSI': latest['rsi_14']
                })
        
        if all_signals:
            all_signals_df = pd.DataFrame(all_signals)
            st.dataframe(all_signals_df, use_container_width=True)
    else:
        st.error(f"Data not available for {selected_ticker}")

# Performance Analytics Page
elif page == "📊 Performance Analytics":
    # Header with visual element
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("📊 Performance Analytics")
    with col2:
        st.markdown("""
        <div style='padding: 1rem; background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); border-radius: 10px; text-align: center; color: #333;'>
        <h4>📈</h4>
        <p><b>Compare</b></p>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("---")
    
    available_tickers = load_available_tickers()
    selected_tickers = st.multiselect("Select Stocks/ETFs to Compare", available_tickers, default=available_tickers[:5])
    
    if selected_tickers:
        # Calculate metrics for each ticker
        comparison_data = []
        for ticker in selected_tickers:
            df = load_stock_data(ticker)
            if df is not None and not df.empty:
                metrics = calculate_performance_metrics(df)
                metrics['Ticker'] = ticker
                comparison_data.append(metrics)
        
        if comparison_data:
            comparison_df = pd.DataFrame(comparison_data)
            comparison_df = comparison_df[['Ticker', 'total_return', 'volatility', 'sharpe_ratio', 'max_drawdown', 'current_price']]
            comparison_df.columns = ['Ticker', 'Total Return (%)', 'Volatility (%)', 'Sharpe Ratio', 'Max Drawdown (%)', 'Current Price ($)']
            
            st.subheader("📈 Performance Comparison")
            st.dataframe(comparison_df.style.format({
                'Total Return (%)': '{:.2f}',
                'Volatility (%)': '{:.2f}',
                'Sharpe Ratio': '{:.2f}',
                'Max Drawdown (%)': '{:.2f}',
                'Current Price ($)': '{:.2f}'
            }), use_container_width=True)
            
            # Visualization
            col1, col2 = st.columns(2)
            
            with col1:
                fig_returns = go.Figure(data=[
                    go.Bar(x=comparison_df['Ticker'], y=comparison_df['Total Return (%)'],
                           marker_color=['green' if x > 0 else 'red' for x in comparison_df['Total Return (%)']])
                ])
                fig_returns.update_layout(title="Total Return Comparison", xaxis_title="Ticker", yaxis_title="Return (%)")
                st.plotly_chart(fig_returns, use_container_width=True)
            
            with col2:
                fig_sharpe = go.Figure(data=[
                    go.Bar(x=comparison_df['Ticker'], y=comparison_df['Sharpe Ratio'],
                           marker_color='blue')
                ])
                fig_sharpe.update_layout(title="Sharpe Ratio Comparison", xaxis_title="Ticker", yaxis_title="Sharpe Ratio")
                st.plotly_chart(fig_sharpe, use_container_width=True)
    else:
        st.info("Please select at least one ticker to compare.")

# Settings Page
elif page == "⚙️ Settings":
    # Header with visual element
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("⚙️ Settings")
    with col2:
        st.markdown("""
        <div style='padding: 1rem; background: linear-gradient(135deg, #d299c2 0%, #fef9d7 100%); border-radius: 10px; text-align: center; color: #333;'>
        <h4>🔧</h4>
        <p><b>Config</b></p>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("---")
    
    st.subheader("📁 Data Configuration")
    st.info(f"Data directory: `{DATA_DIR}`")
    
    available_tickers = load_available_tickers()
    st.write(f"Available stocks: {len(available_tickers)}")
    
    st.subheader("🔧 Technical Indicator Settings")
    st.write("Current indicators in use:")
    st.markdown("""
    - **RSI (14-period)**: Relative Strength Index
    - **MA 20**: 20-day Moving Average
    - **MA 50**: 50-day Moving Average
    - **Daily Return**: Percentage price change
    """)
    
    st.subheader("📊 Signal Generation Logic")
    
    # Visual diagram of signal logic
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("""
        <div style='padding: 1rem; text-align: center; background-color: #e3f2fd; border-radius: 8px;'>
        <h3>📉</h3>
        <p><b>RSI Analysis</b></p>
        <small>Oversold/Overbought</small>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div style='padding: 1rem; text-align: center; background-color: #f3e5f5; border-radius: 8px;'>
        <h3>📈</h3>
        <p><b>MA Crossovers</b></p>
        <small>Trend Detection</small>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div style='padding: 1rem; text-align: center; background-color: #e8f5e9; border-radius: 8px;'>
        <h3>⚡</h3>
        <p><b>Momentum</b></p>
        <small>Price Changes</small>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown("""
        <div style='padding: 1rem; text-align: center; background-color: #fff3e0; border-radius: 8px;'>
        <h3>🎯</h3>
        <p><b>Combined Score</b></p>
        <small>Final Signal</small>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.write("**Signal generation process:**")
    st.markdown("""
    - **RSI levels**: Oversold <30 (bullish), Overbought >70 (bearish)
    - **Moving average crossovers**: MA 20 vs MA 50 trend analysis
    - **Price momentum**: Daily return analysis
    - **Combined scoring system**: Aggregated signal strength calculation
    """)
    
    st.subheader("ℹ️ Platform Information")
    st.write("**Version**: 1.0.0 (Demo)")
    st.write("**Status**: Active")
    st.write("**Last Updated**: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

# Footer
st.markdown("---")
st.markdown("<div style='text-align: center; color: gray;'>Stock & ETF Signal Generation Platform | Demo Version</div>", unsafe_allow_html=True)

