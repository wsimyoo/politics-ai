import streamlit as st
import pandas as pd
from github import Github
import datetime
import io
from openai import OpenAI

# --- 1. 样式与配置 (去除金句相关样式) ---
st.set_page_config(page_title="思政教研智库", layout="wide")

st.markdown("""
    <style>
    .highlight-ai { 
        background-color: #f8fbff; 
        border-left: 5px solid #007bff; 
        padding: 20px; 
        border-radius: 10px; 
        color: #1a1a1a; 
        line-height: 1.7;
    }
    .cloud-tag { 
        background-color: #e6fffa; 
        color: #2c7a7b; 
        padding: 3px 10px; 
        border-radius: 15px; 
        font-size: 0.85rem; 
        font-weight: bold;
        border: 1px solid #b2f5ea;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心逻辑：PDF 自动识别 ---
def get_github_repo():
    return Github(st.secrets["GH_TOKEN"]).get_repo(st.secrets["GH_REPO"])

def load_books_from_folder():
    try:
        repo = get_github_repo()
        files = repo.get_contents("data")
        books = [f.name.replace(".pdf", "") for f in files if f.name.endswith(".pdf")]
        return sorted(books), "data/ (PDF教材已就绪 ✅)"
    except:
        return ["必修1", "必修2", "必修3", "必修4"], "📁 文件夹读取异常"

book_options, source_status = load_books_from_folder()

# --- 3. 登录拦截 ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    st.markdown("<h1 style='text-align: center;'>🛡️ 思政教研智库</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        input_key = st.text_input("🔑 输入 API Key 登录", type="password")
        if st.button("🚀 进入系统", use_container_width=True):
            if input_key:
                st.session_state['authenticated'] = True
                st.session_state['api_key'] = input_key
                st.rerun()
    st.stop()

# --- 4. 个人数据同步逻辑 ---
client = OpenAI(api_key=st.session_state['api_key'], base_url="https://api.deepseek.com")
user_uid = st.session_state['api_key'][:8]
full_filename = f"material_lib_{user_uid}.csv"

def load_personal_data(uid):
    file_path = f"material_lib_{uid}.csv"
    try:
        repo = get_github_repo()
        content_file = repo.get_contents(file_path)
        df = pd.read_csv(content_file.download_url)
        return df, content_file.sha
    except:
        # 移除 '金句' 列
        return pd.DataFrame(columns=['时间', '标题', '分类', '内容', 'AI分析']), None

if 'personal_df' not in st.session_state:
    df, sha = load_personal_data(user_uid)
    st.session_state['personal_df'] = df
    st.session_state['personal_sha'] = sha

# --- 5. 侧边栏 ---
with st.sidebar:
    st.title("🛡️ 智库管理")
    st.caption(f"📖 教材库：{source_status}")
    st.code(f"存档：{full_filename}")
    page = st.radio("前往页面", ["📝 跨教材联动加工", "📂 结构化看板"])
    
    if st.button("🔄 强制同步云端"):
        df, sha = load_personal_data(user_uid)
        st.session_state['personal_df'] = df
        st.session_state['personal_sha'] = sha
        st.rerun()
    
    st.divider()
    if st.button("🚪 退出登录"):
        st.session_state.clear()
        st.rerun()

# --- 6. 联动加工页 (去掉金句输入) ---
if page == "📝 跨教材联动加工":
    st.header("📝 跨教材联动分析")
    col_l, col_r = st.columns([2, 1])
    with col_l:
        raw_text = st.text_area("输入原始素材内容", height=400)
    with col_r:
        title = st.text_input("素材标题")
        mode = st.radio("分析模式", ["单本精读", "多本综合联动"])
        selected_books = st.multiselect("匹配教材 (PDF列表)", options=book_options)
        
        if st.button("🤖 启动 AI 联动解析", use_container_width=True):
            if raw_text and selected_books:
                with st.spinner("正在联动解析..."):
                    prompt = f"教材：{selected_books}。素材：{raw_text}。请给出：1.教材契合点 2.教学建议。要求紧扣教材原文。"
                    response = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    st.session_state['ai_result'] = response.choices[0].message.content

    if 'ai_result' in st.session_state:
        st.divider()
        st.subheader("💡 AI 深度教研建议")
        st.markdown(f'<div class="highlight-ai">{st.session_state["ai_result"]}</div>', unsafe_allow_html=True)
        
        # 直接保存，不再询问金句
        if st.button(f"💾 立即归档至看板", use_container_width=True):
            new_row = {
                '时间': datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                '标题': title, 
                '分类': " / ".join(selected_books),
                '内容': raw_text, 
                'AI分析': st.session_state['ai_result']
            }
            st.session_state['personal_df'] = pd.concat([st.session_state['personal_df'], pd.DataFrame([new_row])], ignore_index=True)
            
            repo = get_github_repo()
            csv_content = st.session_state['personal_df'].to_csv(index=False)
            if st.session_state['personal_sha']:
                repo.update_file(full_filename, "Update", csv_content, st.session_state['personal_sha'])
            else:
                repo.create_file(full_filename, "Init", csv_content)
            
            _, new_sha = load_personal_data(user_uid)
            st.session_state['personal_sha'] = new_sha
            st.success("✅ 归档成功！")
            st.balloons()

# --- 7. 结构化看板 (去掉金句展示) ---
elif page == "📂 结构化看板":
    st.header("📂 我的数字化教研看板")
    df_display = st.session_state['personal_df']
    
    if df_display.empty:
        st.info("目前云端暂无存档。")
    else:
        st.subheader("📊 素材汇总表")
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        
        st.divider()
        st.subheader("🗂️ 深度内容详情卡片")
        
        for i, row in df_display.iloc[::-1].iterrows():
            with st.expander(f"📌 {row['分类']} | {row['标题']}", expanded=(i == len(df_display)-1)):
                st.markdown(f"<span class='cloud-tag'>☁️ 云端同步</span>", unsafe_allow_html=True)
                
                col_data, col_ai = st.columns([1, 1])
                with col_data:
                    st.markdown("**【原始素材内容】**")
                    st.info(row['内容'])
                with col_ai:
                    st.markdown("**【AI 跨教材深度联动分析】**")
                    st.markdown(f'<div class="highlight-ai">{row["AI分析"]}</div>', unsafe_allow_html=True)
