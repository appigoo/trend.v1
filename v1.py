import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time

# --- 頁面配置 ---
st.set_page_config(page_title="多時段趨勢與異動監控", layout="wide")
st.title("📊 多時段實時趨勢與異動分析")

# --- 側邊欄參數 ---
symbol = st.sidebar.text_input("輸入股票代碼", "AAPL").upper()
intervals = ["1m", "5m", "15m", "30m"]
ema_fast_p = st.sidebar.slider("快速 EMA 週期", 5, 20, 9)
ema_slow_p = st.sidebar.slider("慢速 EMA 週期", 21, 50, 21)

def fetch_multi_data(ticker):
    results = {}
    for inter in intervals:
        period = "1d" if inter == "1m" else "5d"
        data = yf.download(ticker, period=period, interval=inter, progress=False)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        results[inter] = data
    return results

def full_analysis(df):
    """整合趨勢預測與異動計算"""
    if len(df) < ema_slow_p + 2:
        return None
    
    # --- 1. 計算技術指標 ---
    df['EMA_F'] = df['Close'].ewm(span=ema_fast_p, adjust=False).mean()
    df['EMA_S'] = df['Close'].ewm(span=ema_slow_p, adjust=False).mean()
    df['Price_Chg'] = df['Close'].pct_change() * 100
    df['Vol_Chg'] = df['Volume'].pct_change() * 100
    
    # --- 2. 趨勢與信號判斷 ---
    curr_f, prev_f = float(df['EMA_F'].iloc[-1]), float(df['EMA_F'].iloc[-2])
    curr_s, prev_s = float(df['EMA_S'].iloc[-1]), float(df['EMA_S'].iloc[-2])
    
    trend = "看漲 (Uptrend)" if curr_f > curr_s else "看跌 (Downtrend)"
    signal = "穩定"
    alert = None
    
    if prev_f <= prev_s and curr_f > curr_s:
        signal = "🚀 黃金交叉"
        alert = "趨勢反轉向上"
    elif prev_f >= prev_s and curr_f < curr_s:
        signal = "💀 死亡交叉"
        alert = "趨勢反轉向下"

    # --- 3. 異動基準計算 (前10名平均) ---
    avg_10_p = df['Price_Chg'].iloc[-11:-1].abs().mean()
    avg_10_v = df['Vol_Chg'].iloc[-11:-1].abs().mean()
    
    return {
        "trend": trend,
        "signal": signal,
        "alert": alert,
        "curr_p_chg": df['Price_Chg'].iloc[-1],
        "curr_v_chg": df['Vol_Chg'].iloc[-1],
        "avg_p_chg": avg_10_p,
        "avg_v_p": avg_10_v,
        "last_p": float(df['Close'].iloc[-1])
    }

# --- 主體循環 ---
placeholder = st.empty()

while True:
    with placeholder.container():
        all_data = fetch_multi_data(symbol)
        
        # --- 第一部分：多時段 Dashboard (含趨勢預測) ---
        st.subheader(f"🔍 {symbol} 多時段狀態監控")
        cols = st.columns(len(intervals))
        
        for i, inter in enumerate(intervals):
            res = full_analysis(all_data[inter])
            with cols[i]:
                if res:
                    st.markdown(f"### {inter}")
                    # 顯示趨勢與信號
                    st.info(f"**趨勢:** {res['trend']}")
                    if "交叉" in res['signal']:
                        st.warning(f"**信號:** {res['signal']}")
                    else:
                        st.write(f"狀態: {res['signal']}")
                    
                    # 顯示異動對比
                    st.metric("當前升跌", f"{res['curr_p_chg']:.2f}%", 
                              delta=f"vs 平均 {res['avg_p_chg']:.2f}%")
                    st.metric("成交量異動", f"{res['curr_v_chg']:.1f}%", 
                              delta=f"vs 平均 {res['avg_v_p']:.1f}%", delta_color="inverse")
                else:
                    st.write(f"{inter} 數據不足")

        # --- 第二部分：核心圖表 (5m) ---
        main_df = all_data["5m"]
        if not main_df.empty:
            st.divider()
            st.subheader(f"📈 核心走勢圖 (5m) - {symbol}")
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=main_df.index, open=main_df['Open'], high=main_df['High'], 
                                         low=main_df['Low'], close=main_df['Close'], name="K線"))
            fig.add_trace(go.Scatter(x=main_df.index, y=main_df['EMA_F'], name="快速EMA", line=dict(color='orange')))
            fig.add_trace(go.Scatter(x=main_df.index, y=main_df['EMA_S'], name="慢速EMA", line=dict(color='blue')))
            
            fig.update_layout(xaxis_rangeslider_visible=False, height=500, margin=dict(t=30, b=10))
            # 解決重複 ID 問題：加入動態 key
            st.plotly_chart(fig, use_container_width=True, key=f"main_chart_{int(time.time())}")

        st.caption(f"最後同步時間: {datetime.now().strftime('%H:%M:%S')}")
        time.sleep(60)
