import streamlit as st
import pandas as pd
from github import Github
from openai import OpenAI
import hashlib
import re
import io
from datetime import datetime

# --- 1. 样式配置 ---
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

# --- 2. 核心引擎函数 ---
def get_github_repo():
    return Github(st.secrets["GH_TOKEN"]).get_repo(st.secrets["GH_REPO"])

def get_available_books():
    try:
        repo = get_github_repo()
        files = repo.get_contents("data")
        books = [f.name.replace('.pdf', '').replace('.PDF', '').strip() for f in files if f.name.endswith(('.pdf', '.PDF'))]
        return sorted(books)
    except:
        return ["必修1", "必修2", "必修3", "必修4"]

def load_from_cloud(uid):
    file_path = f"material_lib_{uid}.csv"
    standard_cols = ["日期", "标题", "涉及教材", "考点设问", "素材原文"]
    try:
        repo = get_github_repo()
        content = repo.get_contents(file_path)
        df = pd.read_csv(content.download_url)
        rename_map = {'素材标题': '标题', '精修解析': '考点设问', '核心解析': '考点设问', '分类': '涉及教材'}
        df.rename(columns=rename_map, inplace=True)
        for col in standard_cols:
            if col not in df.columns: df[col] = "未记录"
        return df[standard_cols], content.sha
    except:
        return pd.DataFrame(columns=standard_cols), None

# --- 3. 登录权限拦截 (彻底修复 KeyError) ---
if 'uid' not in st.session_state:
    st.session_state['uid'] = None

if not st.session_state['uid']:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        st.title("🏛️ 思政名师工作室")
        input_key = st.text_input("请输入 DeepSeek API Key 登录", type="password")
        if st.button("🚀 开启工作室", use_container_width=True):
            if len(input_key) > 10:
                st.session_state['api_key'] = input_key
                st.session_state['uid'] = hashlib.md5(input_key.encode()).hexdigest()[:8]
                st.rerun()
            else:
                st.error("请输入有效的 API Key")
    # 关键点：如果没有登录，直接停止后面所有代码的执行，防止报错
    st.stop()

# --- 4. 只有登录成功才会执行到这里 ---
uid = st.session_state['uid']
db_filename = f"material_lib_{uid}.csv"
book_options = get_available_books()
df_cloud, current_sha = load_from_cloud(uid)

# --- 侧边栏 ---
with st.sidebar:
    st.header(f"👤 老师 ID: {uid}")
    if st.button("🔄 强制同步云端数据", use_container_width=True):
        st.rerun()
    st.divider()
    st.subheader("📥 成果导出")
    if not df_cloud.empty:
        csv_io = io.BytesIO()
        df_cloud.to_csv(csv_io, index=False, encoding='utf-8-sig')
        st.download_button("导出 CSV 清单", data=csv_io.getvalue(), file_name=f"思政智库_{datetime.now().strftime('%m%d')}.csv", use_container_width=True)
    st.divider()
    if st.button("🚪 退出登录"):
        st.session_state.clear()
        st.rerun()

# --- 主功能区 ---
tab1, tab2 = st.tabs(["✨ 智能加工录入", "📂 结构化全景看板"])

with tab1:
    l_col, r_col = st.columns([1.2, 1])
    with l_col:
        with st.container(border=True):
            m_title = st.text_input("1. 素材标题")
            m_raw = st.text_area("2. 素材原文", height=200)
            m_books = st.multiselect("3. 关联教材 (支持联动)", options=book_options)
            
            if st.button("🧠 开启多维深度高亮分析", use_container_width=True):
                if m_title and m_books and m_raw:
                    client = OpenAI(api_key=st.session_state['api_key'], base_url="https://api.deepseek.com")
                    with st.spinner("联动教研分析中..."):
                        prompt = f"你是思政名师。针对《{m_title}》结合教材 {m_books} 分析。输出分册解析、联动分析、教学设问。严禁加粗。核心词用<mark>，结论用<span class='important-red'>。原文：{m_raw}"
                        resp = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                        st.session_state['ai_output'] = re.sub(r'\*\*(.*?)\*\*', r'<mark>\1</mark>', resp.choices[0].message.content)
                else:
                    st.warning("请补全标题、内容和教材")

    with r_col:
        if 'ai_output' in st.session_state:
            st.markdown("✍️ **预览与精修**")
            final_text = st.text_area("解析结果", value=st.session_state['ai_output'], height=450)
            if st.button("💾 确认归档入库", use_container_width=True):
                new_data = {"日期": datetime.now().strftime("%Y-%m-%d"), "标题": m_title, "涉及教材": " | ".join(m_books), "考点设问": final_text, "素材原文": m_raw}
                updated_df = pd.concat([df_cloud, pd.DataFrame([new_data])], ignore_index=True)
                
                repo = get_github_repo()
                csv_str = updated_df.to_csv(index=False, encoding='utf-8-sig')
                _, latest_sha = load_from_cloud(uid)
                if latest_sha:
                    repo.update_file(db_filename, "Save", csv_str, latest_sha)
                else:
                    repo.create_file(db_filename, "Init", csv_str)
                
                st.success("✅ 已同步至云端！")
                del st.session_state['ai_output']
                st.rerun()

with tab2:
    if not df_cloud.empty:
        st.subheader("📊 快速索引")
        st.dataframe(df_cloud[["日期", "标题", "涉及教材"]], use_container_width=True, hide_index=True)
        st.divider()
        search = st.text_input("🔍 搜索库内素材...")
        show_df = df_cloud[df_cloud.apply(lambda r: r.astype(str).str.contains(search).any(), axis=1)] if search else df_cloud
        
        for i, row in show_df.iloc[::-1].iterrows():
            with st.expander(f"📌 {row['标题']} | {row['涉及教材']}"):
                c1, c2 = st.columns([1, 2.5])
                with c1:
                    st.markdown("**📚 涉及教材**")
                    for b in str(row['涉及教材']).split(" | "):
                        st.markdown(f"<span class='book-tag'>{b}</span>", unsafe_allow_html=True)
                with c2:
                    st.markdown("**💡 联动教研解析**")
                    st.markdown(row['考点设问'], unsafe_allow_html=True)
                st.divider()
                st.caption(f"素材原文：{row['素材原文']}")
                if st.button(f"🗑️ 删除此记录", key=f"del_{i}"):
                    new_df = df_cloud.drop(i)
                    get_github_repo().update_file(db_filename, "Delete", new_df.to_csv(index=False, encoding='utf-8-sig'), current_sha)
                    st.rerun()
    else:
        st.info("库内尚无素材。")
