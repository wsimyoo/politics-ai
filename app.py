import streamlit as st
import pandas as pd
from github import Github
import datetime
import io
from openai import OpenAI

# --- 1. 页面配置与增强样式 ---
st.set_page_config(page_title="思政教研智库", layout="wide")

st.markdown("""
    <style>
    /* 证据追踪框：蓝色实边，强调来源 */
    .evidence-box { 
        background-color: #f0f7ff; 
        border: 2px solid #007bff; 
        padding: 15px; 
        border-radius: 8px; 
        color: #004085;
    }
    .file-path-tag { 
        font-family: monospace; 
        background-color: #eeeeee; 
        padding: 2px 5px; 
        border-radius: 3px; 
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心初始化：公共教材库读取 ---
def get_github_repo():
    return Github(st.secrets["GH_TOKEN"]).get_repo(st.secrets["GH_REPO"])

def load_common_books():
    """实时读取 data.csv，若失败则显示错误而非静默"""
    try:
        repo = get_github_repo()
        content_file = repo.get_contents("data.csv")
        common_df = pd.read_csv(content_file.download_url)
        unique_cats = set()
        if '分类' in common_df.columns:
            for entry in common_df['分类'].dropna():
                parts = [p.strip() for p in str(entry).split('/') if p.strip()]
                unique_cats.update(parts)
        return sorted(list(unique_cats)), "data.csv"
    except Exception as e:
        return ["必修1", "必修2", "必修3", "必修4"], f"读取失败(Using Default): {str(e)}"

# 预加载并记录来源文件名
book_options, source_file = load_common_books()

# --- 3. 首页登录 ---
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

# --- 4. 个人数据处理 ---
client = OpenAI(api_key=st.session_state['api_key'], base_url="https://api.deepseek.com")
user_uid = st.session_state['api_key'][:8]
# 【修正】定义完整、绝对的文件名字符串
full_personal_filename = f"material_lib_{user_uid}.csv"

def load_personal_data(uid):
    file_path = f"material_lib_{uid}.csv"
    try:
        repo = get_github_repo()
        content_file = repo.get_contents(file_path)
        df = pd.read_csv(content_file.download_url)
        return df, content_file.sha
    except:
        return pd.DataFrame(columns=['时间', '标题', '分类', '内容', '金句', 'AI分析']), None

personal_df, personal_sha = load_personal_data(user_uid)

# --- 5. 侧边栏：全路径展示 ---
with st.sidebar:
    st.title("🛡️ 智库透明管理")
    # 【核心修正】清晰显示所有读取的文件名
    st.write("📖 **当前教材库来源：**")
    st.code(source_file) 
    st.write("💾 **当前个人存档点：**")
    st.code(full_personal_filename)
    
    page = st.radio("前往", ["📝 素材 AI 加工", "📂 结构化看板"])
    st.divider()
    if st.button("🚪 退出登录"):
        st.session_state['authenticated'] = False
        st.rerun()

# --- 6. 功能实现 ---
if page == "📝 素材 AI 加工":
    st.header("📝 教材深度分析")
    col_l, col_r = st.columns([2, 1])
    with col_l:
        raw_text = st.text_area("输入原始素材内容", height=350)
    with col_r:
        title = st.text_input("素材标题")
        mode = st.radio("分析模式", ["单本精读", "跨教材联动分析"])
        # 这里用的是从 data.csv 实读出来的选项
        selected_books = st.multiselect(f"从 {source_file} 中匹配教材", options=book_options)
        
        if st.button("🤖 启动 AI 溯源分析", use_container_width=True):
            if raw_text and selected_books:
                with st.spinner(f"正在结合 {selected_books} 进行溯源分析..."):
                    # 【核心修正】在 Prompt 中强制要求 AI 引用库里有的教材
                    prompt = f"""
                    你是一名严谨的思政专家。请根据提供的教材列表：{selected_books}，分析素材：{raw_text}。
                    要求：
                    1. 【教材契合点】必须指明素材对标了 {selected_books} 中的哪些具体原理。
                    2. 【教学建议】给出针对性的教学环节。
                    3. 【核心金句】提炼灵魂总结。
                    禁止空谈，必须基于所选教材内容。
                    """
                    response = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    st.session_state['ai_result'] = response.choices[0].message.content

    if 'ai_result' in st.session_state:
        st.divider()
        st.subheader("💡 AI 溯源解析结果")
        # 使用证据追踪框包裹，展示 AI 的专业性
        st.markdown(f'<div class="evidence-box">{st.session_state["ai_result"]}</div>', unsafe_allow_html=True)
        
        final_gold = st.text_input("确认金句", value="提取分析中的精髓...")
        
        # 【核心修正】按钮上直接写死完整的文件名，让保存动作透明
        if st.button(f"📤 确认存入云端：{full_personal_filename}", use_container_width=True):
            new_row = {
                '时间': datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                '标题': title, '分类': " / ".join(selected_books),
                '内容': raw_text, '金句': final_gold, 'AI分析': st.session_state['ai_result']
            }
            updated_df = pd.concat([personal_df, pd.DataFrame([new_row])], ignore_index=True)
            repo = get_github_repo()
            csv_content = updated_df.to_csv(index=False)
            if personal_sha:
                repo.update_file(full_personal_filename, "Update", csv_content, personal_sha)
            else:
                repo.create_file(full_personal_filename, "Init", csv_content)
            st.success(f"🚀 保存成功！数据已写入 GitHub 仓库中的 `{full_personal_filename}`")
            st.balloons()

elif page == "📂 结构化看板":
    st.header(f"📂 看板：{full_personal_filename}")
    if personal_df.empty:
        st.info("该存档文件目前为空。")
    else:
        st.dataframe(personal_df, use_container_width=True)
        # 导出功能
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            personal_df.to_excel(writer, index=False)
        st.download_button(f"📥 导出 {full_personal_filename} 为 Excel", output.getvalue(), f"Export_{user_uid}.xlsx")
