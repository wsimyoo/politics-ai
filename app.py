import streamlit as st
import pandas as pd
from github import Github
from openai import OpenAI
import hashlib
import re
import io
import time
import uuid # 新增：用于生成绝对唯一的请求标识
from datetime import datetime

# --- 1. 样式与配置 ---
st.set_page_config(page_title="思政名师智能素材库", layout="wide", page_icon="🏛️")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    mark { background-color: #ffff00 !important; color: #000 !important; padding: 0 3px; border-radius: 3px; font-weight: bold; }
    .important-red { color: #e11d48 !important; font-weight: bold; }
    .stExpander { border: 1px solid #e2e8f0 !important; border-radius: 12px !important; background: white !important; margin-bottom: 10px !important; }
    .book-tag { 
        background: #fee2e2; color: #b91c1c; padding: 2px 8px; border-radius: 4px; 
        font-size: 12px; font-weight: bold; display: block; margin-bottom: 5px; 
        text-align: center; border: 1px solid #fecaca;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心后端函数 ---
def get_github_repo():
    return Github(st.secrets["GH_TOKEN"]).get_repo(st.secrets["GH_REPO"])

def load_from_cloud(uid):
    """【绝对刷新补丁】通过 uuid 绕过任何可能的云端缓存"""
    file_path = f"material_lib_{uid}.csv"
    standard_cols = ["日期", "标题", "涉及教材", "考点设问", "素材原文"]
    try:
        repo = get_github_repo()
        content = repo.get_contents(file_path)
        # 生成一个绝对唯一的随机字符串，强制 GitHub 实时回传
        unique_req = str(uuid.uuid4())
        fresh_url = f"{content.download_url}?v={unique_req}"
        
        df = pd.read_csv(fresh_url)
        # 字段兼容性处理
        rename_map = {'素材标题': '标题', '精修解析': '考点设问', '核心解析': '考点设问', '涉及教材': '涉及教材', '分类': '涉及教材'}
        df.rename(columns=rename_map, inplace=True)
        for col in standard_cols:
            if col not in df.columns: df[col] = "未记录"
        return df[standard_cols], content.sha
    except:
        return pd.DataFrame(columns=standard_cols), None

# --- 3. 状态初始化 ---
if 'uid' not in st.session_state: st.session_state['uid'] = None
if 'display_df' not in st.session_state: st.session_state['display_df'] = None

# --- 4. 登录拦截 ---
if not st.session_state['uid']:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        st.title("🏛️ 思政名师工作室")
        input_key = st.text_input("请输入 API Key 登录", type="password")
        if st.button("🚀 开启工作室", use_container_width=True):
            if len(input_key) > 10:
                st.session_state['api_key'] = input_key
                st.session_state['uid'] = hashlib.md5(input_key.encode()).hexdigest()[:8]
                st.rerun()
    st.stop()

# 登录后的变量准备
uid = st.session_state['uid']
db_filename = f"material_lib_{uid}.csv"

# 关键：初始化内存数据
if st.session_state['display_df'] is None:
    df_init, current_sha = load_from_cloud(uid)
    st.session_state['display_df'] = df_init

# --- 侧边栏 ---
with st.sidebar:
    st.header(f"👤 老师 ID: {uid}")
    if st.button("🔄 强制重刷云端数据", use_container_width=True):
        st.session_state['display_df'] = None # 清空内存触发重新读取
        st.rerun()
    st.divider()
    if not st.session_state['display_df'].empty:
        csv_io = io.BytesIO()
        st.session_state['display_df'].to_csv(csv_io, index=False, encoding='utf-8-sig')
        st.download_button("导出 CSV 清单", data=csv_io.getvalue(), file_name=f"思政智库_{datetime.now().strftime('%m%d')}.csv", use_container_width=True)

# --- 主功能 Tab ---
tab1, tab2 = st.tabs(["✨ 智能加工录入", "📂 结构化全景看板"])

with tab1:
    l_col, r_col = st.columns([1.2, 1])
    with l_col:
        with st.container(border=True):
            m_title = st.text_input("1. 素材标题")
            m_raw = st.text_area("2. 素材原文内容", height=200)
            # 动态获取 PDF 列表
            try:
                repo_obj = get_github_repo()
                pdf_files = [f.name.replace('.pdf', '').replace('.PDF', '') for f in repo_obj.get_contents("data") if f.name.lower().endswith('.pdf')]
            except:
                pdf_files = ["必修1", "必修2", "必修3", "必修4"]
            
            m_books = st.multiselect("3. 关联教材", options=sorted(pdf_files))
            
            if st.button("🧠 开启名师教研分析", use_container_width=True):
                if m_title and m_books and m_raw:
                    client = OpenAI(api_key=st.session_state['api_key'], base_url="https://api.deepseek.com")
                    with st.spinner("AI正在进行多维联动解析..."):
                        prompt = f"针对《{m_title}》结合教材 {m_books} 分析。严禁加粗。核心词用<mark>，结论用<span class='important-red'>。原文：{m_raw}"
                        resp = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                        st.session_state['ai_output'] = re.sub(r'\*\*(.*?)\*\*', r'<mark>\1</mark>', resp.choices[0].message.content)
                else: st.warning("请完整填写素材内容")

    with r_col:
        if 'ai_output' in st.session_state:
            st.markdown("✍️ **预览与编辑**")
            final_text = st.text_area("解析结果", value=st.session_state['ai_output'], height=450)
            if st.button("💾 确认归档入库", use_container_width=True):
                new_row = {"日期": datetime.now().strftime("%Y-%m-%d"), "标题": m_title, "涉及教材": " | ".join(m_books), "考点设问": final_text, "素材原文": m_raw}
                
                # --- 1. 同步到内存 (解决即时显示) ---
                st.session_state['display_df'] = pd.concat([st.session_state['display_df'], pd.DataFrame([new_row])], ignore_index=True)
                
                # --- 2. 同步到 GitHub ---
                repo = get_github_repo()
                csv_str = st.session_state['display_df'].to_csv(index=False, encoding='utf-8-sig')
                _, latest_sha = load_from_cloud(uid)
                if latest_sha: repo.update_file(db_filename, "Save", csv_str, latest_sha)
                else: repo.create_file(db_filename, "Init", csv_str)
                
                st.success("✅ 归档成功！已写入云端并同步看板。")
                if 'ai_output' in st.session_state: del st.session_state['ai_output']
                st.rerun()

with tab2:
    # 始终显示内存中的最新数据
    df_show = st.session_state['display_df']
    if not df_show.empty:
        st.subheader("📊 结构化全景看板")
        search = st.text_input("🔍 搜索关键词（支持标题、考点、教材）")
        filtered_df = df_show[df_show.apply(lambda r: r.astype(str).str.contains(search).any(), axis=1)] if search else df_show
        
        for i, row in filtered_df.iloc[::-1].iterrows():
            with st.expander(f"📌 {row['标题']} | {row['涉及教材']}"):
                c1, c2 = st.columns([1, 2.5])
                with c1:
                    st.markdown("**📚 涉及教材**")
                    for b in str(row['涉及教材']).split(" | "):
                        st.markdown(f"<span class='book-tag'>{b}</span>", unsafe_allow_html=True)
                with c2:
                    st.markdown("**💡 深度联动解析**")
                    st.markdown(row['考点设问'], unsafe_allow_html=True)
                st.divider()
                st.caption(f"素材原文参考：{row['素材原文']}")
    else:
        st.info("库内暂无素材，请在加工页进行录入。")
