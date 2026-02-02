import streamlit as st
import pandas as pd
from openai import OpenAI
import os
from datetime import datetime
import hashlib

# 1. 页面配置与高级样式
st.set_page_config(page_title="思政名师智能素材库", layout="wide", page_icon="🏛️")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    /* 重点：优化折叠区样式 */
    .stExpander { border: 1px solid #e2e8f0 !important; background-color: white !important; border-radius: 12px !important; margin-bottom: 15px !important; }
    .stExpander:hover { border-color: #b91c1c !important; }
    /* 表格容器样式 */
    .stDataFrame { border: 1px solid #e2e8f0; border-radius: 10px; }
    /* 教材色块 */
    .book-tag { background: #fee2e2; color: #b91c1c; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# 2. 核心后端逻辑
def get_user_id(api_key):
    return hashlib.md5(api_key.encode()).hexdigest()[:8]

def get_available_books():
    data_path = "data"
    if not os.path.exists(data_path): return []
    # 自动识别已补全后缀的 .pdf 文件
    files = [f for f in os.listdir(data_path) if f.lower().endswith('.pdf')]
    files.sort()
    return [f.replace('.pdf', '').replace('.PDF', '').replace('高中政治', '').strip() for f in files]

# 3. 登录权限系统
if 'api_key' not in st.session_state:
    st.session_state['api_key'] = None

if not st.session_state['api_key']:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        st.title("🏛️ 思政名师专属素材空间")
        st.write("请输入 DeepSeek API Key 开启您的跨教材教研库")
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
    
    # --- 侧边栏：管理面板 ---
    with st.sidebar:
        st.header(f"👤 老师 ID: {user_id}")
        if st.button("🚪 退出登录"):
            st.session_state['api_key'] = None
            st.rerun()
        st.divider()
        st.subheader("📥 教研成果导出")
        if os.path.exists(user_db):
            df_exp = pd.read_csv(user_db)
            csv = df_exp.to_csv(index=False).encode('utf-8-sig')
            st.download_button("下载全部素材 (Excel格式)", data=csv, file_name=f"思政教研素材库_{datetime.now().strftime('%Y%m%d')}.csv", use_container_width=True)
        st.caption("提示：上传PDF后若未显示，请尝试右上角三点-Clear cache")

    # --- 主功能区：双视图切换 ---
    tab1, tab2 = st.tabs(["✨ 素材智能录入加工", "📂 结构化全景看板"])

    # TAB 1: 智能录入
    with tab1:
        left_c, right_c = st.columns([1.2, 1])
        with left_c:
            with st.container(border=True):
                m_title = st.text_input("1. 素材标题", placeholder="如：‘新质生产力’赋能绿色发展")
                m_raw = st.text_area("2. 素材原文内容", height=150, placeholder="粘贴时政、案例或报道原文...")
                m_books = st.multiselect("3. 关联教材（支持多选）", options=book_options)
                
                if st.button("🧠 AI 跨教材深度联想", use_container_width=True):
                    if not m_title or not m_raw or not m_books:
                        st.warning("请完整填写标题、原文并勾选教材")
                    else:
                        client = OpenAI(api_key=st.session_state['api_key'], base_url="https://api.deepseek.com")
                        with st.spinner("AI 正在联动解析知识点..."):
                            prompt = f"你是一位思政名师。分析《{m_title}》在《{'、'.join(m_books)}》中的核心考点，并给出针对性的教学设问。要求逻辑严密，文字精炼。\n原文：{m_raw}"
                            resp = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                            st.session_state['buffer'] = resp.choices[0].message.content

            if 'buffer' in st.session_state:
                st.markdown('<div style="background-color: #fffbeb; padding: 20px; border-radius: 12px; border: 1.5px solid #fcd34d;">', unsafe_allow_html=True)
                final_analysis = st.text_area("✍️ 老师精修区（在此确认最终解析结果）", value=st.session_state['buffer'], height=300)
                if st.button("💾 归档至云端素材库", use_container_width=True):
                    new_entry = {"日期": datetime.now().strftime("%Y-%m-%d"), "标题": m_title, "涉及教材": " | ".join(m_books), "考点设问": final_analysis, "素材原文": m_raw}
                    df = pd.read_csv(user_db) if os.path.exists(user_db) else pd.DataFrame(columns=["日期","标题","涉及教材","考点设问","素材原文"])
                    df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
                    df.to_csv(user_db, index=False, encoding='utf-8-sig')
                    st.success("✅ 归档成功！已存入全景看板。")
                    del st.session_state['buffer']
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
        
        with right_c:
            st.info("💡 **教研小贴士**：\n您可以同时选择《必修2》和《必修4》，AI 会自动为您梳理出从‘经济高质量发展’到‘唯物辩证法’的跨模块逻辑。")

    # TAB 2: 结构化全景看板 (重点优化部分)
    with tab2:
        if os.path.exists(user_db):
            df = pd.read_csv(user_db).fillna("")
            
            # 兼容性修复列名
            mapping = {'关联教材': '涉及教材', '核心考点': '考点设问', '核心知识点': '考点设问', '精修解析': '考点设问'}
            for old, new in mapping.items():
                if old in df.columns: df.rename(columns={old: new}, inplace=True)

            # --- 视图一：极简结构化清单表 ---
            st.subheader("📌 快速检索清单")
            q_table = st.text_input("🔍 输入关键词快速过滤表格记录...")
            
            view_df = df.copy()
            if q_table:
                view_df = view_df[view_df.apply(lambda r: r.astype(str).str.contains(q_table).any(), axis=1)]
            
            st.dataframe(
                view_df[["日期", "标题", "涉及教材"]],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "日期": st.column_config.Column(width="small"),
                    "标题": st.column_config.Column("素材名称", width="large"),
                    "涉及教材": st.column_config.Column("关联书目", width="medium"),
                }
            )

            st.divider()

            # --- 视图二：分列折叠详情区 ---
            st.subheader("📖 结构化教研详情 (点击标题展开分列视图)")
            
            # 卡片级别的搜索过滤
            q_card = st.text_input("🔍 搜索详细考点或原文内容...")
            show_df = df[df.apply(lambda r: r.astype(str).str.contains(q_card).any(), axis=1)] if q_card else df
            
            for i, row in show_df.iloc[::-1].iterrows():
                # 使用 expander 实现您的“折叠”想法
                with st.expander(f"📌 {row['涉及教材']} | {row['标题']}"):
                    # 在折叠框内部实现您想要的“再分列”
                    col_b, col_p = st.columns([1, 2.5])
                    
                    with col_b:
                        st.markdown("**📚 涉及教材**")
                        books = str(row['涉及教材']).split(" | ")
                        for b in books:
                            st.markdown(f"<span class='book-tag'>{b}</span>", unsafe_allow_html=True)
                    
                    with col_p:
                        st.markdown("**💡 关联考点与设问解析**")
                        st.write(row['考点设问'])
                    
                    st.divider()
                    st.markdown("**📄 素材原文参考**")
                    st.caption(row.get('素材原文', "无原文内容"))
                    
                    if st.button(f"🗑️ 删除此条素材", key=f"del_{i}"):
                        df.drop(i).to_csv(user_db, index=False, encoding='utf-8-sig')
                        st.rerun()
        else:
            st.info("素材库目前为空，请先在‘录入加工’页添加内容。")
