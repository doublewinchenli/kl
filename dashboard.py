import streamlit as st
import akshare as ak
import pandas as pd
import numpy as np
import time

st.set_page_config(layout="wide")
st.title("🚀 实时交易指挥台（稳定版）")

# ======================
# 自动刷新（10秒）
# ======================
REFRESH_INTERVAL = 10
st.caption(f"自动刷新：{REFRESH_INTERVAL}秒")

# ======================
# 缓存数据（核心优化）
# ======================
@st.cache_data(ttl=60)
def get_stock_list():
    try:
        return ak.stock_zh_a_spot_em()
    except:
        return None

@st.cache_data(ttl=300)
def get_stock_hist(code):
    try:
        return ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
    except:
        return None

@st.cache_data(ttl=60)
def get_index():
    try:
        return ak.stock_zh_index_daily(symbol="sh000001")
    except:
        return None

# ======================
# 市场情绪
# ======================
index = get_index()

if index is None or len(index) < 2:
    st.error("❌ 指数数据获取失败")
    st.stop()

idx_change = index['close'].pct_change().iloc[-1]

if idx_change > 0.01:
    emotion = "🔥 主升期"
    emotion_score = 90
elif idx_change > -0.01:
    emotion = "⚠️ 修复期"
    emotion_score = 60
else:
    emotion = "❄️ 冰点/退潮"
    emotion_score = 20

st.subheader(f"市场状态：{emotion}")

# ======================
# 股票池（数量限制避免卡死）
# ======================
stock_list = get_stock_list()

if stock_list is None or len(stock_list) == 0:
    st.error("❌ 股票数据获取失败（akshare可能被限制）")
    st.stop()

codes = stock_list['代码'].tolist()[:20]  # 控制数量

results = []

# ======================
# 核心计算
# ======================
for code in codes:
    try:
        df = get_stock_hist(code)

        if df is None or len(df) < 60:
            continue

        df = df.tail(60)

        A = df['最低'].min()
        B = df['最高'].max()

        P13 = (B - A) / 3 + A
        P12 = (B - A) / 2 + A

        C = df['收盘'].iloc[-1]
        VOL = df['成交量'].iloc[-1]
        VOL5 = df['成交量'].rolling(5).mean().iloc[-1]

        # === 位置分 ===
        distance = abs(C - P13) / P13
        position_score = 90 if distance < 0.02 else 75 if distance < 0.05 else 60

        # === 资金 / 龙头分 ===
        vol_ratio = VOL / VOL5 if VOL5 != 0 else 1
        leader_score = 90 if vol_ratio > 1.5 else 75 if vol_ratio > 1.2 else 60
        fund_score = leader_score

        # === 总分 ===
        total_score = (emotion_score * 0.3 +
                       leader_score * 0.3 +
                       position_score * 0.2 +
                       fund_score * 0.2)

        if total_score < 70:
            continue

        # 类型
        category = "龙头" if leader_score >= 85 else "强势"

        # 买点识别（用当前收盘代替实时，保证稳定）
        in_buy_zone = P13 * 0.98 <= C <= P13 * 1.02
        signal = "🔥 买点" if in_buy_zone else ""

        results.append({
            "股票": code,
            "总分": round(total_score, 1),
            "类型": category,
            "现价": round(C, 2),
            "买入区间": f"{round(P13*0.98,2)} - {round(P13*1.02,2)}",
            "止损": round(P12, 2),
            "信号": signal
        })

    except:
        continue

# ======================
# 展示结果
# ======================
df_result = pd.DataFrame(results)

if df_result.empty:
    st.warning("⚠️ 当前无符合条件股票")
else:
    df_result = df_result.sort_values(by="总分", ascending=False)

    def highlight(row):
        if "买点" in row["信号"]:
            return ["background-color: red"] * len(row)
        return [""] * len(row)

    st.subheader("📊 今日交易池")
    st.dataframe(
        df_result.head(20).style.apply(highlight, axis=1),
        use_container_width=True
    )

# ======================
# 操作建议
# ======================
st.subheader("📌 操作建议")

if emotion_score < 50:
    st.error("当前市场弱势，建议空仓或观望")
elif emotion_score < 80:
    st.warning("市场震荡，轻仓操作")
else:
    st.success("市场主升，可重点做龙头")

# ======================
# 自动刷新
# ======================
time.sleep(REFRESH_INTERVAL)
st.rerun()
