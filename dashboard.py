import streamlit as st
import akshare as ak
import pandas as pd
import numpy as np
import time
import os

st.set_page_config(layout="wide")

st.title("🚀 实时交易指挥台（自动系统）")

# ======================
# 自动刷新（10秒）
# ======================
refresh_interval = 10
st.caption(f"自动刷新：{refresh_interval}秒")

# ======================
# 市场情绪
# ======================
index = ak.stock_zh_index_daily(symbol="sh000001")
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
# 股票池（建议替换成你自己的清单）
# ======================
stock_list = ak.stock_zh_a_spot_em()
codes = stock_list['代码'].tolist()[:50]

results = []
alerts = []

# ======================
# 核心计算
# ======================
for code in codes:
    try:
        df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")

        if len(df) < 60:
            continue

        df = df.tail(60)

        A = df['最低'].min()
        B = df['最高'].max()

        P13 = (B - A)/3 + A
        P12 = (B - A)/2 + A

        # 实时行情
        spot = ak.stock_zh_a_spot_em()
        row = spot[spot['代码'] == code]

        if row.empty:
            continue

        price = row['最新价'].values[0]
        VOL = row['成交量'].values[0]

        # 5日均量（用历史）
        VOL5 = df['成交量'].rolling(5).mean().iloc[-1]

        # 分数计算
        distance = abs(price - P13)/P13
        position_score = 90 if distance < 0.02 else 75 if distance < 0.05 else 60

        vol_ratio = VOL / VOL5 if VOL5 != 0 else 1
        leader_score = 90 if vol_ratio > 1.5 else 75 if vol_ratio > 1.2 else 60
        fund_score = leader_score

        total_score = (emotion_score*0.3 +
                       leader_score*0.3 +
                       position_score*0.2 +
                       fund_score*0.2)

        if total_score < 70:
            continue

        # ===== 买点识别 =====
        in_buy_zone = P13*0.98 <= price <= P13*1.02

        signal = "🔥 买点触发" if in_buy_zone else ""

        if in_buy_zone:
            alerts.append(f"{code} 触发买点！价格:{round(price,2)}")

        results.append({
            "股票": code,
            "总分": round(total_score,1),
            "现价": round(price,2),
            "买入区间": f"{round(P13*0.98,2)} - {round(P13*1.02,2)}",
            "止损": round(P12,2),
            "信号": signal
        })

    except:
        continue

# ======================
# 展示表格（高亮买点）
# ======================
df_result = pd.DataFrame(results)
df_result = df_result.sort_values(by="总分", ascending=False)

def highlight(row):
    if "买点" in row["信号"]:
        return ["background-color: red"]*len(row)
    return [""]*len(row)

st.subheader("📊 实时交易池")
st.dataframe(df_result.head(20).style.apply(highlight, axis=1), use_container_width=True)

# ======================
# 弹窗提醒
# ======================
if alerts:
    for msg in alerts:
        st.warning(msg)
        os.system(f'msg * "{msg}"')  # Windows弹窗

# ======================
# 自动刷新
# ======================
time.sleep(refresh_interval)
st.rerun()
