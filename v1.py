import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time

# --- 頁面配置 ---
st.set_page_config(page_title="多時段實時監控儀表板", layout="wide")
st.title("📈 多時段股票異動監控系統")

# --- 側邊欄參數 ---
symbol = st.sidebar.text_input("輸入股票代碼", "AAPL").upper()
intervals = ["1m", "5m", "15m", "30m"]
ema_fast = st.sidebar.slider("快速 EMA", 5, 20, 9)
ema_slow = st.sidebar.slider("慢速 EMA", 21, 50, 21)

def fetch_multi_data(ticker):
    """獲取多個時間頻率的數據"""
    results = {}
    for inter in intervals:
        # 1m 數據最多只能拿最近 7 天，其他可以拿更多
        period = "1d" if inter == "1m" else "5d"
        data = yf.download(ticker, period=period, interval=inter, progress=False)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        results[inter] = data
    return results

def calculate_metrics(df):
    """計算異動指標與前10名平均值"""
    if len(df) < 12:
        return None
    
    # 1. 計算價格與成交量變化率 (%)
    df['Price_Chg'] = df['Close'].pct_change() * 100
    df['Vol_Chg'] = df['Volume'].pct_change() * 100
    
    # 2. 獲取當前實時數據 (最後一行)
    curr_price_chg = df['Price_Chg'].iloc[-1]
    curr_vol_chg = df['Vol_Chg'].iloc[-1]
    
    # 3. 計算前 10 個週期的平均升跌幅 (不含當前這根)
    # 取絕對值平均，這樣可以看出「波動強度」的對比
    avg_10_price = df['Price_Chg'].iloc[-11:-1].abs().mean()
    avg_10_vol = df['Vol_Chg'].iloc[-11:-1].abs().mean()
    
    # 4. 指標計算 (EMA)
    df['EMA_F'] = df['Close'].ewm(span=ema_fast).mean()
    df['EMA_S'] = df['Close'].ewm(span=ema_slow).mean()
    
    return {
        "curr_p_chg": curr_price_chg,
        "curr_v_chg": curr_vol_chg,
        "avg_p_chg": avg_10_price,
        "avg_v_chg": avg_10_vol,
        "last_close": df['Close'].iloc[-1],
        "trend": "Bull" if df['EMA_F'].iloc[-1] > df['EMA_S'].iloc[-1] else "Bear"
    }

# --- 主循環 ---
placeholder = st.empty()

while True:
    with placeholder.container():
        all_data = fetch_multi_data(symbol)
        
        # --- Top Section: 異動監控 Dashboard ---
        st.subheader("🚀 實時異動監控 (當前 vs 前10名平均波動)")
        cols = st.columns(len(intervals))
        
        for i, inter in enumerate(intervals):
            df_inter = all_data[inter]
            metrics = calculate_metrics(df_inter)
            
            with cols[i]:
                if metrics:
                    st.markdown(f"### {inter}")
                    # 價格異動
                    p_diff = metrics['curr_p_chg'] - metrics['avg_p_chg']
                    st.metric(
                        label="價格升跌幅",
                        value=f"{metrics['curr_p_chg']:.2f}%",
                        delta=f"vs 平均 {metrics['avg_p_chg']:.2f}%",
                        delta_color="normal"
                    )
                    # 成交量異動
                    v_diff = metrics['curr_v_chg'] - metrics['avg_v_chg']
                    st.metric(
                        label="成交量異動",
                        value=f"{metrics['curr_v_chg']:.1f}%",
                        delta=f"vs 平均 {metrics['avg_v_chg']:.1f}%",
                        delta_color="inverse" # 成交量放大通常是警告
                    )
                    
                    status = "🔥 劇烈波動" if abs(metrics['curr_p_chg']) > metrics['avg_p_chg'] * 2 else "😴 平穩"
                    st.write(f"狀態: {status}")
                else:
                    st.write(f"{inter} 數據加載中...")

        st.divider()

        # --- Middle Section: 主圖表 (以 5m 為主) ---
        main_df = all_data["5m"]
        if not main_df.empty:
            st.subheader(f"{symbol} 核心走勢 (5m)")
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=main_df.index, open=main_df['Open'], high=main_df['High'],
                low=main_df['Low'], close=main_df['Close'], name="K線"
            ))
            
            # 加上 EMA
            main_df['EMA_F'] = main_df['Close'].ewm(span=ema_fast).mean()
            fig.add_trace(go.Scatter(x=main_df.index, y=main_df['EMA_F'], name="快速EMA", line=dict(color='orange')))
            
            fig.update_layout(height=500, xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=30, b=10))
            
            # --- 關鍵修改處：加入唯一的 key ---
            # 使用時間戳確保每次刷新時 ID 都是唯一的
            st.plotly_chart(fig, use_container_width=True, key=f"chart_{symbol}_{int(time.time())}")

        # --- Bottom Section: 數據明細 ---
        with st.expander("查看 1m 原始數據明細"):
            st.dataframe(all_data["1m"].tail(10), use_container_width=True)

        # 倒計時刷新
        st.caption(f"最後更新時間: {datetime.now().strftime('%H:%M:%S')} | 每 60 秒刷新一次")
        time.sleep(60)
