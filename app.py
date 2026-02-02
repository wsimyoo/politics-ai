import streamlit as st
import pandas as pd
from openai import OpenAI
import os
from datetime import datetime
import hashlib

# 1. 页面配置
st.set_page_config(page_title="思政名师智能素材库", layout="wide", page_icon="🏛️")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .editor-container { background-color: #fffbeb; padding: 20px; border-radius: 12px; border: 1.5px solid #fcd34d; margin-top: 15px; }
    .material-card { background: white; padding: 15px; border-radius: 10px; border-left: 6px solid #b91c1c; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); margin-bottom: 15px; }
    .book-tag { background: #fee2e2; color: #991b1b; padding: 2px 10px; border-radius: 15px; font-size: 11px; font-weight: bold; margin-right: 4px; }
    </style>
    """, unsafe_allow_html=True)

# 2. 用户鉴权
def get_user_id(api_key):
    return hashlib.md5(api_key.encode()).hexdigest()[:8]

# 3. 登录逻辑
if 'api_key' not in st.session_state:
    st.session_state['api_key'] = None

if not st.session_state['api_key']:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        st.title("🏛️ 思政名师专属素材空间")
        st.write("一把钥匙开一把锁：请输入 API Key 开启您的跨教材教研库")
        input_key = st.text_input("DeepSeek API Key", type="password")
        if st.button("🚀 开启工作室", use_container_width=True):
            if len(input_key) > 10:
                st.session_state['api_key'] = input_key
                st.session_state['user_id'] = get_user_id(input_key)
                st.rerun()
            else:
                st.error("请输入有效的 API Key")
else:
    user_id = st.session_state['user_id']
    user_db = f"material_lib_{user_id}.csv"
    
    # --- 侧边栏 ---
    with st.sidebar:
        st.header(f"👤 工作室 ID: {user_id}")
        if st.button("🚪 退出登录"):
            st.session_state['api_key'] = None
            st.rerun()
        st.divider()
        st.markdown("### 📥 导出与备份")
        if os.path.exists(user_db):
            df_export = pd.read_csv(user_db)
            # 导出为 CSV
            csv = df_export.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 导出全部素材 (CSV)",
                data=csv,
                file_name=f"思政素材库_{datetime.now().strftime('%Y%m%d')}.csv",
                mime='text/csv',
                use_container_width=True
            )
            st.caption("注：CSV可用Excel直接打开，已处理中文乱码。")

    # --- 主布局 ---
    tab1, tab2 = st.tabs(["✨ 素材加工录入", "📂 素材全景看板"])

    # TAB 1: 录入与精修
    with tab1:
        left_c, right_c = st.columns([1.2, 1])
        with left_c:
            st.subheader("✍️ 跨教材素材加工")
            with st.container(border=True):
                m_title = st.text_input("1. 素材标题")
                m_raw = st.text_area("2. 素材原文内容", height=120)
                data_path = "data"
                available_books = [f for f in os.listdir(data_path) if f.endswith('.pdf')] if os.path.exists(data_path) else ["必修1", "必修2", "必修3", "必修4"]
                m_books = st.multiselect("3. 关联教材", available_books, default=available_books[:1] if available_books else None)
                
                if st.button("🧠 AI 跨教材深度分析", use_container_width=True):
                    client = OpenAI(api_key=st.session_state['api_key'], base_url="https://api.deepseek.com")
                    with st.spinner("AI 正在解析跨教材关联点..."):
                        prompt = f"你是一位政治名师。请分析素材《{m_title}》在《{'、'.join(m_books)}》中的核心考点并给出教学设问。\n原文：{m_raw}"
                        try:
                            resp = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                            st.session_state['buffer'] = resp.choices[0].message.content
                        except Exception as e: st.error(f"分析失败: {e}")

            if 'buffer' in st.session_state:
                st.markdown('<div class="editor-container">', unsafe_allow_html=True)
                refined_analysis = st.text_area("✍️ 老师精修区：补充或修改知识点", value=st.session_state['buffer'], height=300)
                if st.button("💾 确认并存入档案库", use_container_width=True):
                    new_data = {
                        "日期": datetime.now().strftime("%Y-%m-%d"),
                        "标题": m_title,
                        "关联教材": " | ".join(m_books),
                        "核心知识点": refined_analysis,
                        "原文": m_raw
                    }
                    df = pd.read_csv(user_db) if os.path.exists(user_db) else pd.DataFrame(columns=["日期","标题","关联教材","核心知识点","原文"])
                    df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
                    df.to_csv(user_db, index=False, encoding='utf-8-sig')
                    st.success("存档成功！")
                    del st.session_state['buffer']
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        with right_c:
            st.subheader("最近入库记录")
            if os.path.exists(user_db):
                recent_df = pd.read_csv(user_db).iloc[::-1].head(3)
                for _, r in recent_df.iterrows():
                    st.markdown(f"""<div class="material-card"><strong>{r['标题']}</strong><br><small>{r['关联教材']}</small></div>""", unsafe_allow_html=True)
            else: st.info("暂无记录")

    # TAB 2: 全景看板（表格 + 搜索）
    with tab2:
        st.subheader("🔍 全局素材检索与清单")
        if os.path.exists(user_db):
            full_df = pd.read_csv(user_db)
            
            search_q = st.text_input("输入关键词（如标题、考点、教材名）快速检索整个库")
            if search_q:
                full_df = full_df[full_df.apply(lambda r: r.astype(str).str.contains(search_q).any(), axis=1)]
            
            # --- 核心改进：结构化表格展示 ---
            st.markdown("##### 📖 素材知识清单视图")
            # 整理一下表格，让解析结果只显示简要预览，避免表格过长
            display_table = full_df.copy()
            display_table['知识点预览'] = display_table['核心知识点'].apply(lambda x: str(x)[:100].replace('\n', ' ') + '...')
            
            st.dataframe(
                display_table[["日期", "标题", "关联教材", "知识点预览"]],
                use_container_width=True,
                column_config={
                    "日期": st.column_config.Column(width="small"),
                    "标题": st.column_config.Column(width="medium"),
                    "关联教材": st.column_config.Column(width="medium"),
                    "知识点预览": st.column_config.Column(width="large")
                },
                hide_index=True
            )

            st.divider()
            
            # 依然保留精细的卡片视图供阅读
            st.markdown("##### 📄 详细档案卡片")
            for i, row in full_df.iloc[::-1].iterrows():
                with st.expander(f"📌 {row['关联教材']} —— {row['标题']}"):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("**【核心知识点分析】**")
                        st.write(row['核心知识点'])
                    with c2:
                        st.markdown("**【素材原文】**")
                        st.caption(row['原文'])
                    if st.button("🗑️ 删除", key=f"del_tab2_{i}"):
                        full_df.drop(i).to_csv(user_db, index=False, encoding='utf-8-sig')
                        st.rerun()
        else:
            st.info("库内暂无素材，请在第一页进行录入。")

