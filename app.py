import streamlit as st
import pandas as pd
from openai import OpenAI
import os
from datetime import datetime
import hashlib

# 1. 页面配置
st.set_page_config(page_title="思政名师智库-精修版", layout="wide", page_icon="🏛️")

# 自定义 CSS：增强表格与卡片视觉
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .material-card { background: white; padding: 20px; border-radius: 12px; border-top: 5px solid #b91c1c; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .stDataFrame { border: 1px solid #e2e8f0; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 2. 工具函数
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
        if st.button("🚀 开启工作室", use_container_width=True):
            if len(input_key) > 10:
                st.session_state['api_key'] = input_key
                st.session_state['user_id'] = get_user_id(input_key)
                st.rerun()
else:
    user_id = st.session_state['user_id']
    user_db = f"material_lib_{user_id}.csv"
    book_options = get_available_books()
    
    # --- 侧边栏 ---
    with st.sidebar:
        st.header(f"👤 老师 ID: {user_id}")
        if st.button("🚪 退出登录"):
            st.session_state['api_key'] = None
            st.rerun()
        st.divider()
        if os.path.exists(user_db):
            df_exp = pd.read_csv(user_db)
            csv = df_exp.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 导出教研全表", data=csv, file_name=f"思政素材库_{datetime.now().strftime('%m%d')}.csv", use_container_width=True)

    tab1, tab2 = st.tabs(["✨ 素材智能加工", "📂 全景结构化看板"])

    # --- TAB 1: 录入 ---
    with tab1:
        left_c, right_c = st.columns([1.2, 1])
        with left_c:
            with st.container(border=True):
                m_title = st.text_input("素材标题", placeholder="如：‘数智化’赋能高质量发展")
                m_raw = st.text_area("素材原文", height=150)
                m_books = st.multiselect("关联教材", options=book_options)
                
                if st.button("🧠 AI 跨教材解析", use_container_width=True):
                    client = OpenAI(api_key=st.session_state['api_key'], base_url="https://api.deepseek.com")
                    with st.spinner("深度分析中..."):
                        prompt = f"你是政治名师。分析《{m_title}》在《{'、'.join(m_books)}》中的考点及设问。\n原文：{m_raw}"
                        resp = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                        st.session_state['buffer'] = resp.choices[0].message.content

            if 'buffer' in st.session_state:
                st.markdown('<div style="background:#fffbeb; padding:20px; border-radius:12px; border:1px solid #fcd34d;">', unsafe_allow_html=True)
                final_analysis = st.text_area("✍️ 老师精修区（考点、关联、建议）", value=st.session_state['buffer'], height=300)
                if st.button("💾 确认存入档案库", use_container_width=True):
                    new_entry = {"日期": datetime.now().strftime("%Y-%m-%d"), "标题": m_title, "关联教材": " | ".join(m_books), "核心考点": final_analysis, "原文": m_raw}
                    df = pd.read_csv(user_db) if os.path.exists(user_db) else pd.DataFrame(columns=["日期","标题","关联教材","核心考点","原文"])
                    df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
                    df.to_csv(user_db, index=False, encoding='utf-8-sig')
                    st.success("存档成功！")
                    del st.session_state['buffer']
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    # --- TAB 2: 完善后的结构化看板 ---
    with tab2:
        if os.path.exists(user_db):
            df = pd.read_csv(user_db).fillna("")
            
            # 兼容性处理
            name_map = {'精修解析': '核心考点', '核心知识点': '核心考点', '分析结果': '核心考点'}
            for old, new in name_map.items():
                if old in df.columns and new not in df.columns: df.rename(columns={old: new}, inplace=True)

            # --- 完善后的工具栏 ---
            st.subheader("🔍 高级检索与清单")
            col_search, col_filter = st.columns([2, 1])
            with col_search:
                search_q = st.text_input("输入关键词（标题、内容、教材）", placeholder="搜索全库...")
            with col_filter:
                # 提取库中已有的所有教材名
                unique_books = set()
                for b_str in df['关联教材'].unique():
                    for b in str(b_str).split(" | "): unique_books.add(b)
                selected_filter = st.multiselect("按教材筛选看板", options=list(unique_books))

            # 执行过滤
            filtered_df = df.copy()
            if search_q:
                filtered_df = filtered_df[filtered_df.apply(lambda r: r.astype(str).str.contains(search_q).any(), axis=1)]
            if selected_filter:
                filtered_df = filtered_df[filtered_df['关联教材'].apply(lambda x: any(b in str(x) for b in selected_filter))]

            # --- 结构化表格强化 ---
            st.markdown("##### 📝 结构化教研清单表")
            # 整理预览文字
            view_df = filtered_df.copy()
            view_df['核心考点摘要'] = view_df['核心考点'].apply(lambda x: str(x).replace('\n', ' ')[:100] + '...')
            
            # 使用高性能表格配置
            st.dataframe(
                view_df[["日期", "标题", "关联教材", "核心考点摘要"]],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "日期": st.column_config.DateColumn("录入日期", format="YYYY-MM-DD", width="small"),
                    "标题": st.column_config.Column("素材名称", width="medium"),
                    "关联教材": st.column_config.ListColumn("涉及教材", width="medium"),
                    "核心考点摘要": st.column_config.Column("知识点/考点映射预览", width="large")
                }
            )

            st.divider()

            # 详细卡片
            st.subheader("🗂️ 教研档案详情卡片")
            for i, row in filtered_df.iloc[::-1].iterrows():
                with st.container():
                    st.markdown(f"""
                    <div class="material-card">
                        <small style="color:#b91c1c; font-weight:bold;">{row['关联教材']}</small>
                        <h3 style="margin:5px 0;">{row['标题']}</h3>
                        <p style="font-size:12px; color:gray;">{row['日期']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    with st.expander("查看解析详情及原文"):
                        c1, c2 = st.columns([1.5, 1])
                        with c1:
                            st.markdown("**【教研解析】**")
                            st.write(row['核心考点'])
                        with c2:
                            st.markdown("**【素材原文】**")
                            st.caption(row.get('原文', "无内容"))
                        if st.button(f"🗑️ 删除该记录", key=f"del_{i}"):
                            df.drop(i).to_csv(user_db, index=False, encoding='utf-8-sig')
                            st.rerun()
        else:
            st.info("库内尚无素材。")
