import streamlit as st
import pandas as pd
from openai import OpenAI
import os
from datetime import datetime
import hashlib

# 1. 页面配置
st.set_page_config(page_title="思政名师智能素材库", layout="wide", page_icon="🏛️")

# 自定义样式：确保卡片还是原来的味道
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .material-card { 
        background: white; 
        padding: 20px; 
        border-radius: 12px; 
        border-top: 5px solid #b91c1c; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); 
        margin-bottom: 20px; 
    }
    .stDataFrame { border-radius: 10px; border: 1px solid #e2e8f0; }
    </style>
    """, unsafe_allow_html=True)

def get_user_id(api_key):
    return hashlib.md5(api_key.encode()).hexdigest()[:8]

def get_available_books():
    data_path = "data"
    if not os.path.exists(data_path): return []
    files = [f for f in os.listdir(data_path) if f.lower().endswith('.pdf')]
    files.sort()
    return [f.replace('.pdf', '').replace('.PDF', '').replace('高中政治', '').strip() for f in files]

# 3. 登录逻辑
if 'api_key' not in st.session_state:
    st.session_state['api_key'] = None

if not st.session_state['api_key']:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        st.title("🏛️ 思政名师专属素材空间")
        input_key = st.text_input("DeepSeek API Key", type="password")
        if st.button("🚀 进入工作室", use_container_width=True):
            if len(input_key) > 10:
                st.session_state['api_key'] = input_key
                st.session_state['user_id'] = get_user_id(input_key)
                st.rerun()
else:
    user_id = st.session_state['user_id']
    user_db = f"material_lib_{user_id}.csv"
    book_options = get_available_books()
    
    with st.sidebar:
        st.header(f"👤 老师 ID: {user_id}")
        if st.button("🚪 退出登录"):
            st.session_state['api_key'] = None
            st.rerun()
        st.divider()
        if os.path.exists(user_db):
            df_exp = pd.read_csv(user_db)
            csv = df_exp.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 导出教研清单", data=csv, file_name=f"素材导出_{user_id}.csv", use_container_width=True)

    tab1, tab2 = st.tabs(["✨ 素材智能录入", "📂 结构化全景看板"])

    # --- TAB 1: 录入（保持原样） ---
    with tab1:
        left_c, right_c = st.columns([1.2, 1])
        with left_c:
            with st.container(border=True):
                m_title = st.text_input("1. 素材标题")
                m_raw = st.text_area("2. 素材原文内容", height=150)
                m_books = st.multiselect("3. 关联教材", options=book_options)
                
                if st.button("🧠 AI 跨教材深度分析", use_container_width=True):
                    client = OpenAI(api_key=st.session_state['api_key'], base_url="https://api.deepseek.com")
                    with st.spinner("AI 深度分析中..."):
                        prompt = f"分析素材《{m_title}》在《{'、'.join(m_books)}》中的核心考点并给出设问。\n原文：{m_raw}"
                        resp = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                        st.session_state['buffer'] = resp.choices[0].message.content

            if 'buffer' in st.session_state:
                st.markdown('<div style="background:#fffbeb; padding:15px; border-radius:10px; border:1px solid #fcd34d;">', unsafe_allow_html=True)
                final_analysis = st.text_area("✍️ 老师精修区", value=st.session_state['buffer'], height=300)
                if st.button("💾 归档素材库", use_container_width=True):
                    new_entry = {"日期": datetime.now().strftime("%Y-%m-%d"), "标题": m_title, "关联教材": " | ".join(m_books), "核心解析": final_analysis, "素材原文": m_raw}
                    df = pd.read_csv(user_db) if os.path.exists(user_db) else pd.DataFrame(columns=["日期","标题","关联教材","核心解析","素材原文"])
                    df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
                    df.to_csv(user_db, index=False, encoding='utf-8-sig')
                    st.success("存档成功！")
                    del st.session_state['buffer']
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    # --- TAB 2: 【表格分列，卡片照旧】的新看板 ---
    with tab2:
        if os.path.exists(user_db):
            df = pd.read_csv(user_db).fillna("")
            
            # 统一字段逻辑
            mapping = {'涉及教材': '关联教材', '核心考点': '核心解析', '考点设问': '核心解析', '精修解析': '核心解析'}
            for old, new in mapping.items():
                if old in df.columns: df.rename(columns={old: new}, inplace=True)

            st.subheader("📝 结构化教研索引表 (教材与考点分列呈现)")
            
            # 表格专用预览数据：将大段解析“脱水”成摘要，分别放入两列
            view_df = df.copy()
            view_df['考点预览'] = view_df['核心解析'].apply(lambda x: str(x).replace('\n', ' ')[:100] + '...')
            
            # 使用 column_config 实现物理意义上的分列
            st.dataframe(
                view_df[["日期", "标题", "关联教材", "考点预览"]],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "日期": st.column_config.Column("入库日期", width="small"),
                    "标题": st.column_config.Column("素材名称", width="medium"),
                    "关联教材": st.column_config.Column("【所属教材】", width="medium"),
                    "考点预览": st.column_config.Column("【核心考点/设问】", width="large")
                }
            )

            st.divider()

            # --- 档案卡片保持原来的结构 ---
            st.subheader("🗂️ 详细档案卡片 (原始视图)")
            q = st.text_input("🔍 搜索过滤卡片...")
            show_df = df[df.apply(lambda r: r.astype(str).str.contains(q).any(), axis=1)] if q else df
            
            for i, row in show_df.iloc[::-1].iterrows():
                with st.container():
                    # 依然使用您喜欢的 HTML 卡片样式
                    st.markdown(f"""
                    <div class="material-card">
                        <small style="color:#b91c1c; font-weight:bold;">{row['关联教材']}</small>
                        <h3 style="margin:5px 0;">{row['标题']}</h3>
                        <p style="font-size:12px; color:gray;">入库日期：{row['日期']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    with st.expander("查看完整精修分析与素材原文"):
                        c1, c2 = st.columns([1.5, 1])
                        with c1:
                            st.markdown("**【教研深度解析】**")
                            st.write(row['核心解析'])
                        with c2:
                            st.markdown("**【原文参考】**")
                            st.caption(row.get('素材原文', row.get('原文内容', "无原文")))
                        if st.button(f"🗑️ 删除此素材", key=f"del_card_{i}"):
                            df.drop(i).to_csv(user_db, index=False, encoding='utf-8-sig')
                            st.rerun()
        else:
            st.info("库内暂无素材。")
