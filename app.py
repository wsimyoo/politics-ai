import streamlit as st
import pandas as pd
from openai import OpenAI
import requests
import os
from datetime import datetime

# 1. 页面配置：设置沉浸式标题和图标
st.set_page_config(
    page_title="政治名师 AI 智库",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. 注入精装修 CSS：让界面像一个高端教研软件
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .main-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        border: 1px solid #e2e8f0;
    }
    .stButton>button { border-radius: 8px; height: 3em; transition: 0.3s; }
    .stTextArea textarea { border-radius: 10px; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 25px;
        background-color: #f1f5f9;
        border-radius: 8px 8px 0 0;
        font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. 侧边栏：核心身份识别与 Key 配置
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/teacher.png", width=60)
    st.title("教研配置中心")
    
    with st.expander("🔑 接口授权", expanded=True):
        ds_api_key = st.text_input("DeepSeek API Key", type="password", help="在此输入您的 API 密钥")
        jina_key = st.text_input("Jina Reader Key", type="password", help="用于解析网页链接内容")
    
    st.divider()
    # 个性化隔离核心：根据识别码生成不同的数据库文件
    user_tag = st.text_input("👤 教师识别码", placeholder="输入您的姓氏或工号")
    if not user_tag:
        st.warning("⚠️ 请输入识别码以激活个人空间")
        st.stop()
    
    DB_FILE = f"db_user_{user_tag}.csv"
    st.success(f"已连接：{user_tag} 的专属库")

# 4. 辅助函数：抓取网页内容
def fetch_web_text(url, key):
    if not key: return "ERR_NO_JINA_KEY"
    try:
        # 使用 Jina Reader 转换为文本，防止 AI 瞎编
        res = requests.get(f"https://r.jina.ai/{url}", headers={"Authorization": f"Bearer {key}"}, timeout=15)
        return res.text[:5000] # 截取前5000字，防止 Token 溢出
    except:
        return "ERR_NETWORK"

# 5. 主界面布局
st.title("🏛️ 政治教学素材智能加工平台")
tab_process, tab_library = st.tabs(["✨ 素材加工中心", "🗄️ 我的数字化素材库"])

# --- TAB 1: 素材加工中心 ---
with tab_process:
    col_l, col_r = st.columns([2, 3], gap="large")
    
    with col_l:
