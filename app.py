import streamlit as st
import pandas as pd
from openai import OpenAI
import os
from datetime import datetime
import hashlib

# 1. 页面配置
st.set_page_config(page_title="思政名师智能素材库", layout="wide", page_icon="🏛️")

# 自定义样式：强化表格观感
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .material-card { background: white; padding: 20px; border-radius: 12px; border-top: 5px solid #b91c1c; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; }
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
        if st.button("🚀 进入教研室", use_container_width=True):
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
            st.download_button("📥 导出教研清单", data=csv, file_name=f"素材导出_{datetime.now().strftime('%m%d')}.csv", use_container_width=True)

    tab1, tab2 = st.tabs(["✨ 素材智能录入", "📂 结构化全景看板"])

    # --- TAB 1: 录入 ---
    with tab1:
        left_c, right_c = st.columns([1.2, 1])
        with left_c:
            with st.container(border=True):
                m_title = st.text_input("1. 素材标题")
                m_raw = st.text_area("2. 素材原文内容", height=150)
                m_books = st.multiselect("3. 关联教材（分列依据）", options=book_options)
                
                if st.button("🧠 AI 跨教材深度解析", use_container_width=True):
                    client = OpenAI(api_key=st.session_state['api_key'], base_url="https://api.deepseek.com")
                    with st.spinner("教研分析中..."):
                        prompt = f"你是政治名师。请分析素材《{m_title}》在《{'、'.join(m_books)}》中的核心考点，并给出教学设问。内容要精炼。\n原文：{m_raw}"
                        resp = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                        st.session_state['buffer'] = resp.choices[0].message.content

            if 'buffer' in st.session_state:
                st.markdown('<div class="editor-container" style="background:#fffbeb; padding:15px; border-radius:10px; border:1px solid #fcd34d;">', unsafe_allow_html=True)
                final_analysis = st.text_area("✍️ 老师精修区", value=st.session_state['buffer'], height=300)
                if st.button("💾 归档素材库", use_container_width=True):
                    new_entry = {"日期": datetime.now().strftime("%Y-%m-%d"), "标题": m_title, "涉及教材": " | ".join(m_books), "考点设问": final_analysis, "原文内容": m_raw}
                    df = pd.read_csv(user_db) if os.path.exists(user_db) else pd.DataFrame(columns=["日期","标题","涉及教材","考点设问","原文内容"])
                    df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
                    df.to_csv(user_db, index=False, encoding='utf-8-sig')
                    st.success("存档成功！")
                    del st.session_state['buffer']
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    # --- TAB 2: 完善后的【分列呈现】清单表 ---
    with tab2:
        if os.path.exists(user_db):
            df = pd.read_csv(user_db).fillna("")
            
            # 统一字段名（兼容旧数据）
            mapping = {'关联教材': '涉及教材', '核心考点': '考点设问', '核心知识点': '考点设问', '精修解析': '考点设问'}
            for old, new in mapping.items():
                if old in df.columns: df.rename(columns={old: new}, inplace=True)

            st.subheader("📝 结构化教研索引表")
            
            # 搜索与过滤
            col_search, col_filter = st.columns([2, 1])
            with col_search:
                q = st.text_input("🔍 全局检索关键词...")
            with col_filter:
                unique_books = sorted(list(set([b for sub in df['涉及教材'].str.split(" | ") for b in sub if b])))
                f_book = st.multiselect("筛选特定教材", options=unique_books)

            # 数据过滤
            dff = df.copy()
            if q: dff = dff[dff.apply(lambda r: r.astype(str).str.contains(q).any(), axis=1)]
            if f_book: dff = dff[dff['涉及教材'].apply(lambda x: any(b in str(x) for b in f_book))]

            # --- 核心修改：分列呈现数据构建 ---
            view_df = dff.copy()
            # 格式化考点列，只保留前80字并去掉换行，方便分列对比
            view_df['核心考点清单'] = view_df['考点设问'].apply(lambda x: str(x).replace('\n', ' ')[:100] + '...')
            
            st.dataframe(
                view_df[["日期", "标题", "涉及教材", "核心考点清单"]],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "日期": st.column_config.Column(width="small"),
                    "标题": st.column_config.Column("素材标题", width="medium"),
                    "涉及教材": st.column_config.Column("关联书目 (分列)", width="medium"),
                    "核心考点清单": st.column_config.Column("考点与教学设问 (分列汇总)", width="large"),
                }
            )

            st.divider()

            # 下方展示详细内容
            st.subheader("📂 素材档案详情")
            for i, row in dff.iloc[::-1].iterrows():
                with st.expander(f"📌 {row['涉及教材']} —— {row['标题']}"):
                    c1, c2 = st.columns([1.5, 1])
                    with c1:
                        st.markdown("**【考点深度解析】**")
                        st.write(row['考点设问'])
                    with c2:
                        st.markdown("**【原文内容】**")
                        st.caption(row.get('原文内容', "无原文"))
                    if st.button(f"🗑️ 删除该记录", key=f"del_{i}"):
                        df.drop(i).to_csv(user_db, index=False, encoding='utf-8-sig')
                        st.rerun()
        else:
            st.info("暂无数据。")

