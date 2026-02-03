import streamlit as st
import pandas as pd
from github import Github
import datetime
import io
from openai import OpenAI

# --- 1. 样式与配置 ---
st.set_page_config(page_title="思政教研智库", layout="wide")
st.markdown("""
    <style>
    .highlight-ai { background-color: #f0f7ff; border-left: 5px solid #007bff; padding: 15px; border-radius: 8px; color: #0c5460; }
    .gold-text { color: #ff4b4b; font-weight: bold; font-size: 1.1rem; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心逻辑：直接读取 data 文件夹下的 PDF 名 (拒绝瞎编) ---
def get_github_repo():
    return Github(st.secrets["GH_TOKEN"]).get_repo(st.secrets["GH_REPO"])

def load_books_from_folder():
    """直接把您文件夹里的 PDF 文件名变成下拉菜单选项"""
    try:
        repo = get_github_repo()
        files = repo.get_contents("data")
        # 提取所有 PDF 文件名，去掉后缀，排除 README
        books = [f.name.replace(".pdf", "") for f in files if f.name.endswith(".pdf")]
        if not books:
            return ["必修1", "必修2", "必修3", "必修4"], "📁 data文件夹内暂无PDF"
        return sorted(books), "data/ (已动态识别PDF教材 ✅)"
    except Exception as e:
        return ["必修1", "必修2", "必修3", "必修4"], f"❌ 读取失败: {str(e)}"

# 自动获取教材列表
book_options, source_status = load_books_from_folder()

# --- 3. 登录拦截 ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    st.markdown("<h1 style='text-align: center;'>🛡️ 思政教研智库</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        input_key = st.text_input("🔑 输入 API Key 登录", type="password")
        if st.button("🚀 点击解锁进入系统", use_container_width=True):
            if input_key:
                st.session_state['authenticated'] = True
                st.session_state['api_key'] = input_key
                st.rerun()
    st.stop()

# --- 4. 个人数据同步 ---
client = OpenAI(api_key=st.session_state['api_key'], base_url="https://api.deepseek.com")
user_uid = st.session_state['api_key'][:8]
full_filename = f"material_lib_{user_uid}.csv"

def load_personal_data(uid):
    file_path = f"material_lib_{uid}.csv"
    try:
        repo = get_github_repo()
        content_file = repo.get_contents(file_path)
        return pd.read_csv(content_file.download_url), content_file.sha
    except:
        return pd.DataFrame(columns=['时间', '标题', '分类', '内容', '金句', 'AI分析']), None

personal_df, personal_sha = load_personal_data(user_uid)

# --- 5. 侧边栏 ---
with st.sidebar:
    st.title("🛡️ 教研管理")
    st.write("📖 **检测到教材库：**")
    st.caption(source_status)
    st.write("💾 **当前存档：**")
    st.code(full_filename)
    page = st.radio("前往", ["📝 素材 AI 加工", "📂 结构化看板"])
    st.divider()
    if st.button("🚪 退出登录"):
        st.session_state['authenticated'] = False
        st.rerun()

# --- 6. 联动分析功能 ---
if page == "📝 素材 AI 加工":
    st.header("📝 跨教材联动分析")
    col_l, col_r = st.columns([2, 1])
    with col_l:
        raw_text = st.text_area("输入原始素材（案例、语段、时政）", height=400)
    with col_r:
        title = st.text_input("素材标题")
        mode = st.radio("分析模式", ["单本精读", "跨教材综合联动分析"])
        # 这里的选项就是您的 PDF 文件名！
        selected_books = st.multiselect("匹配您文件夹中的 PDF 教材", options=book_options)
        
        if st.button("🤖 启动 AI 联动分析", use_container_width=True):
            if raw_text and selected_books:
                with st.spinner("正在结合教材进行溯源解析..."):
                    prompt = f"基于教材：{selected_books}，分析素材：{raw_text}。请给出：1.教材契合点 2.教学建议 3.核心金句。要求必须对标所选教材内容。"
                    response = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    st.session_state['ai_result'] = response.choices[0].message.content

    if 'ai_result' in st.session_state:
        st.divider()
        st.markdown(f'<div class="highlight-ai">{st.session_state["ai_result"]}</div>', unsafe_allow_html=True)
        final_gold = st.text_input("确认核心金句")
        if st.button(f"💾 确认保存至云端：{full_filename}", use_container_width=True):
            new_row = {
                '时间': datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                '标题': title, '分类': " / ".join(selected_books),
                '内容': raw_text, '金句': final_gold, 'AI分析': st.session_state['ai_result']
            }
            updated_df = pd.concat([personal_df, pd.DataFrame([new_row])], ignore_index=True)
            repo = get_github_repo()
            csv_content = updated_df.to_csv(index=False)
            if personal_sha: repo.update_file(full_filename, "Update", csv_content, personal_sha)
            else: repo.create_file(full_filename, "Init", csv_content)
            st.success(f"🎉 联动成果已同步至 `{full_filename}`")
            st.balloons()

elif page == "📂 结构化看板":
    st.header(f"📂 我的存档看板")
    if personal_df.empty:
        st.info("暂无数据。")
    else:
        st.dataframe(personal_df, use_container_width=True)
        # Excel 导出
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            personal_df.to_excel(writer, index=False)
        st.download_button("📥 导出 Excel", output.getvalue(), f"Export_{user_uid}.xlsx", use_container_width=True)
        
        st.divider()
        for i, row in personal_df.iloc[::-1].iterrows():
            with st.expander(f"📌 {row['分类']} | {row['标题']}"):
                st.markdown(f"**核心金句：** <span class='gold-text'>{row['金句']}</span>", unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                with c1: st.info(row['内容'])
                with c2: st.markdown(f'<div class="highlight-ai">{row["AI分析"]}</div>', unsafe_allow_html=True)

