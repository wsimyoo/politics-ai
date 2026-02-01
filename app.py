import streamlit as st
import pandas as pd
from openai import OpenAI
import requests
import os
from datetime import datetime

# 1. 页面配置
st.set_page_config(
    page_title="政治名师 AI 智库",
    page_icon="🏛️",
    layout="wide"
)

# 2. 注入 CSS 样式
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
    </style>
    """, unsafe_allow_html=True)

# 3. 侧边栏
with st.sidebar:
    st.title("教研配置中心")
    ds_api_key = st.text_input("DeepSeek API Key", type="password")
    jina_key = st.text_input("Jina Reader Key", type="password")
    st.divider()
    user_tag = st.text_input("👤 教师识别码", placeholder="请输入您的名字")
    if not user_tag:
        st.warning("请输入识别码以激活")
        st.stop()
    DB_FILE = f"db_user_{user_tag}.csv"

# 4. 辅助函数
def fetch_web_text(url, key):
    try:
        res = requests.get(f"https://r.jina.ai/{url}", headers={"Authorization": f"Bearer {key}"}, timeout=15)
        return res.text[:5000]
    except:
        return "抓取失败，请检查链接或 Key"

# 5. 主界面
st.title("🏛️ 政治教学素材智能加工平台")
tab_process, tab_library = st.tabs(["✨ 素材加工中心", "🗄️ 我的数字化素材库"])

with tab_process:
    col_l, col_r = st.columns([2, 3], gap="large")
    
    with col_l:
        st.subheader("📍 输入素材源")
        in_type = st.radio("素材形式", ["手动粘贴", "网页链接"], horizontal=True)
        
        final_content = ""
        if in_type == "网页链接":
            web_url = st.text_input("在此粘贴链接")
            if st.button("🔌 抓取网页原文"):
                if not jina_key:
                    st.error("请填入 Jina Key")
                else:
                    with st.spinner("抓取中..."):
                        fetched = fetch_web_text(web_url, jina_key)
                        st.session_state['web_data'] = fetched
            final_content = st.session_state.get('web_data', "")
        else:
            final_content = st.text_area("在此粘贴文字", height=300)
        
        input_title = st.text_input("素材标题")
        analyze_trigger = st.button("🚀 开始 AI 深度解析")

    with col_r:
        st.subheader("🧠 解析结果")
        if analyze_trigger:
            if not ds_api_key or not final_content:
                st.error("请检查 Key 和输入内容")
            else:
                client = OpenAI(api_key=ds_api_key, base_url="https://api.deepseek.com")
                with st.spinner("DeepSeek 解析中..."):
                    prompt = f"你是一位特级政治教师。请对标高中政治必修1-4教材解析该素材：\n{final_content}"
                    resp = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[{"role":"user","content":prompt}]
                    )
                    st.session_state['last_ai_res'] = resp.choices[0].message.content
        
        if 'last_ai_res' in st.session_state:
            st.markdown(st.session_state['last_ai_res'])
            if st.button("📥 保存到我的

