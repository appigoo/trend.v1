import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time

# --- 頁面配置 ---
st.set_page_config(page_title="量價異動強力監控", layout="wide")

# --- 注入 CSS 閃爍動畫 ---
st.markdown("""
    <style>
    @keyframes blinker {  
        50% { opacity: 0.3; background-color: #FF4B4B; }
    }
    .flash-box {
        padding: 20px;
        border-radius: 10px;
        border: 2px solid #FF4B4B;
        background-color: rgba(255, 75, 75, 0.1);
        animation: blinker 1s linear infinite;
        text-align: center;
        font-weight: bold;
        color: white;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🚀 量價齊動 - 強力視覺監控儀表板")

# --- 側邊欄參數 ---
with st.sidebar:
    symbol = st.text_input("輸入股票代碼", "AAPL").upper()
    st.divider()
    intervals = ["1m", "5m", "15m", "30m"]
    ema_fast_p = st.slider("快速 EMA 週期", 5, 20, 9)
    ema_slow_p = st.slider("慢速 EMA 週期", 21, 50, 21)
    st.divider()
    # 新增：異動倍數參數
    alert_threshold = st.slider("⚠️ 異動警告倍數 (vs 平均值)", 1.5, 5.0, 3.0, 0.5)

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
    if len(df) < 15: return None
    
    # 計算指標
    df['EMA_F'] = df['Close'].ewm(span=ema_fast_p, adjust=False).mean()
    df['EMA_S'] = df['Close'].ewm(span=ema_slow_p, adjust=False).mean()
    df['Price_Chg'] = df['Close'].pct_change() * 100
    df['Vol_Chg'] = df['Volume'].pct_change() * 100
    
    # 當前數據
    curr_p_chg = abs(df['Price_Chg'].iloc[-1]) # 取絕對值判斷波動
    curr_v_chg = df['Vol_Chg'].iloc[-1]
    
    # 前10名平均值 (基準)
    avg_10_p = df['Price_Chg'].iloc[-11:-1].abs().mean()
    avg_10_v = df['Vol_Chg'].iloc[-11:-1].abs().mean()
    
    # 判定是否觸發強力警報
    is_extreme = (curr_p_chg > avg_10_p * alert_threshold) and (curr_v_chg > avg_10_v * alert_threshold)
    
    return {
        "trend": "看漲" if df['EMA_F'].iloc[-1] > df['EMA_S'].iloc[-1] else "看跌",
        "curr_p_chg": df['Price_Chg'].iloc[-1],
        "curr_v_chg": curr_v_chg,
        "avg_p": avg_10_p,
        "avg_v": avg_10_v,
        "is_extreme": is_extreme
    }

# --- 主體循環 ---
placeholder = st.empty()

while True:
    with placeholder.container():
        all_data = fetch_multi_data(symbol)
        cols = st.columns(len(intervals))
        
        for i, inter in enumerate(intervals):
            res = full_analysis(all_data[inter])
            with cols[i]:
                if res:
                    # 如果觸發極端異動，顯示閃爍盒子
                    if res['is_extreme']:
                        st.markdown(f'<div class="flash-box">⚡ {inter} 極端異動告警 ⚡</div>', unsafe_allow_html=True)
                    
                    st.subheader(f"⏱️ {inter}")
                    st.write(f"趨勢: {res['trend']}")
                    
                    st.metric("當前升跌幅", f"{res['curr_p_chg']:.2f}%", 
                              delta=f"基準 {res['avg_p']:.2f}%")
                    st.metric("成交量變動", f"{res['curr_v_chg']:.1f}%", 
                              delta=f"基準 {res['avg_v']:.1f}%", delta_color="inverse")
                else:
                    st.write(f"{inter} 數據準備中")

        # 圖表顯示 (5m 為例)
        st.divider()
        main_df = all_data["5m"]
        if not main_df.empty:
            fig = go.Figure(data=[go.Candlestick(x=main_df.index, open=main_df['Open'], 
                            high=main_df['High'], low=main_df['Low'], close=main_df['Close'], name="K線")])
            fig.update_layout(height=400, xaxis_rangeslider_visible=False, template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True, key=f"chart_{int(time.time())}")

        st.caption(f"最後更新: {datetime.now().strftime('%H:%M:%S')} (設定閾值: {alert_threshold}倍)")
        time.sleep(60)
