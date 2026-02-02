import streamlit as st
import pandas as pd
from openai import OpenAI
import os
import pdfplumber
from datetime import datetime
import hashlib

st.set_page_config(page_title="思政智库看板", layout="wide", initial_sidebar_state="expanded")

# --- 1. 用户鉴权与个性化 ---
def get_user_id(api_key):
    return hashlib.md5(api_key.encode()).hexdigest()[:8]

# --- 2. 界面美化 CSS ---
st.markdown("""
    <style>
    .material-card { background: white; padding: 15px; border-radius: 8px; border-left: 5px solid #b91c1c; margin-bottom: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .tag-blue { background: #dbeafe; color: #1e40af; padding: 2px 6px; border-radius: 4px; font-size: 12px; }
    .tag-red { background: #fee2e2; color: #991b1b; padding: 2px 6px; border-radius: 4px; font-size: 12px; }
    </style>
    """, unsafe_allow_html=True)

# --- 🔒 登录验证 ---
if 'api_key' not in st.session_state:
    st.session_state['api_key'] = None

if not st.session_state['api_key']:
    st.title("🏛️ 思政名师专属素材空间")
    key = st.text_input("输入 API Key 开启您的私人库", type="password")
    if st.button("进入空间"):
        if key: 
            st.session_state['api_key'] = key
            st.session_state['user_id'] = get_user_id(key)
            st.rerun()
else:
    u_id = st.session_state['user_id']
    u_db = f"lib_{u_id}.csv"
    
    # --- 🏗️ 三栏布局 ---
    left_col, mid_col, right_col = st.columns([1, 2, 1.5])

    # --- 左栏：教材导航 ---
    with left_col:
        st.subheader("📚 教材索引")
        books = [f for f in os.listdir("data") if f.endswith('.pdf')]
        selected_b = st.selectbox("选择教材", books)
        # 这里可以预设教材目录，或者让AI自动提取目录（简化版直接显示文件）
        st.info(f"当前检索范围：{selected_b}")
        with st.expander("查看本册核心逻辑图"):
            st.write("此处可放置该教材的思维导图逻辑...")

    # --- 中栏：素材加工与入库 ---
    with mid_col:
        st.subheader("✍️ 素材智能加工")
        with st.container():
            title = st.text_input("素材标题", placeholder="输入热点标题...")
            raw_text = st.text_area("内容原文", height=250, placeholder="粘贴时政、案例或金句...")
            
            c1, c2 = st.columns(2)
            with c1:
                process_btn = st.button("🧠 AI 关联教材并加工", use_container_width=True)
            with c2:
                save_btn = st.button("💾 直接存入私有库", use_container_width=True)

            if process_btn:
                client = OpenAI(api_key=st.session_state['api_key'], base_url="https://api.deepseek.com")
                with st.spinner("AI 正在深度解析..."):
                    prompt = f"你是一位政治名师。请分析该素材对应的教材考点，并给出一个课堂教学建议。\n素材：{raw_text}"
                    resp = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                    st.session_state['temp_ai'] = resp.choices[0].message.content
            
            if 'temp_ai' in st.session_state:
                st.markdown("---")
                st.markdown(st.session_state['temp_ai'])

            if save_btn:
                # 存储逻辑
                new_row = {"日期": datetime.now().strftime("%m-%d"), "标题": title, "分析": st.session_state.get('temp_ai', '未解析'), "原文": raw_text}
                df = pd.read_csv(u_db) if os.path.exists(u_db) else pd.DataFrame(columns=["日期","标题","分析","原文"])
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                df.to_csv(u_db, index=False, encoding='utf-8-sig')
                st.success("入库成功！已同步至您的档案。")

    # --- 右栏：档案瀑布流 ---
    with right_col:
        st.subheader("📂 个人档案墙")
        if os.path.exists(u_db):
            lib = pd.read_csv(u_db)
            search = st.text_input("🔍 搜索历史素材...")
            filtered_lib = lib[lib['标题'].str.contains(search)] if search else lib
            
            for i, row in filtered_lib.iloc[::-1].iterrows():
                st.markdown(f"""
                <div class="material-card">
                    <span class="tag-blue">{row['日期']}</span>
                    <strong>{row['标题']}</strong>
                    <p style='font-size:0.9em; color:gray;'>{str(row['分析'])[:60]}...</p>
                </div>
                """, unsafe_allow_html=True)
                with st.expander("查看详情"):
                    st.write(row['分析'])
                    st.divider()
                    st.caption(row['原文'])
        else:
            st.info("您的仓库目前是空的。")


