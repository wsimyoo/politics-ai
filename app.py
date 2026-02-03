import streamlit as st
import pandas as pd
from github import Github
import datetime
import io
from openai import OpenAI

# --- 1. 页面配置 ---
st.set_page_config(page_title="思政教研智库", layout="wide")

# --- 2. 首页登录拦截 (新增按钮登录) ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    st.markdown("<h1 style='text-align: center;'>🛡️ 思政教研智库</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        input_key = st.text_input("🔑 输入 API Key 登录", type="password")
        if st.button("🚀 点击解锁进入", use_container_width=True):
            if input_key:
                st.session_state['authenticated'] = True
                st.session_state['api_key'] = input_key
                st.rerun()
    st.stop()

# --- 3. 初始化与数据加载 ---
client = OpenAI(api_key=st.session_state['api_key'], base_url="https://api.deepseek.com")
user_uid = st.session_state['api_key'][:8]

def get_github_repo():
    return Github(st.secrets["GH_TOKEN"]).get_repo(st.secrets["GH_REPO"])

def load_data(uid):
    file_path = f"material_lib_{uid}.csv"
    try:
        repo = get_github_repo()
        content_file = repo.get_contents(file_path)
        df = pd.read_csv(content_file.download_url)
        return df, content_file.sha
    except:
        return pd.DataFrame(columns=['时间', '标题', '分类', '内容', '金句', 'AI分析']), None

def save_to_github(df, uid, sha):
    file_path = f"material_lib_{uid}.csv"
    csv_content = df.to_csv(index=False)
    repo = get_github_repo()
    if sha: repo.update_file(file_path, f"Update {uid}", csv_content, sha)
    else: repo.create_file(file_path, f"Init {uid}", csv_content)

# 核心：实时读取您的 data 数据
df, file_sha = load_data(user_uid)

# --- 4. 关键：从 Data 中提取分类，绝不乱写 ---
if not df.empty and '分类' in df.columns:
    # 提取 CSV 中已有的分类，去除重复
    raw_categories = df['分类'].dropna().unique().tolist()
    # 处理多选存入的 " / " 格式，将其拆解为独立的教材标签
    final_categories = set()
    for cat in raw_categories:
        for sub_cat in str(cat).split(" / "):
            if sub_cat.strip(): final_categories.add(sub_cat.strip())
    data_based_books = sorted(list(final_categories))
else:
    # 如果 data 是空的，提示先录入或给一个最基础的种子分类
    data_based_books = ["必修1", "必修2", "必修3", "必修4"]

# --- 5. 侧边栏 ---
with st.sidebar:
    st.title("🛡️ 智库菜单")
    page = st.radio("前往", ["📝 素材 AI 加工", "📂 结构化看板"])
    if st.button("退出登录"):
        st.session_state['authenticated'] = False
        st.rerun()

# --- 6. 功能区 ---
if page == "📝 素材 AI 加工":
    st.header("📝 基于 Data 的素材加工")
    col1, col2 = st.columns([2, 1])
    with col1:
        raw_text = st.text_area("输入原始素材内容", height=300)
    with col2:
        title = st.text_input("素材标题")
        mode = st.radio("分析模式", ["单本精读", "跨教材联动"])
        
        # 重点：此处选项完全来自您的 Data
        selected_books = st.multiselect("涉及教材分类（读取自 Data）", options=data_based_books)
        # 允许手动录入新分类以便后续出现在 Data 中
        extra_book = st.text_input("新增教材分类（可选）")
        if extra_book:
            selected_books.append(extra_book)
        
        if st.button("🤖 启动 AI 分析", use_container_width=True):
            if raw_text and selected_books:
                with st.spinner("AI 正在解析..."):
                    prompt = f"模式：{mode}。教材：{selected_books}。内容：{raw_text}。请给出教材契合点、教学建议、核心金句。"
                    response = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    st.session_state['ai_result'] = response.choices[0].message.content

    if 'ai_result' in st.session_state:
        st.divider()
        st.success(st.session_state['ai_result'])
        final_gold = st.text_input("确认核心金句")
        if st.button("💾 归档至云端"):
            new_row = {
                '时间': datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                '标题': title,
                '分类': " / ".join(selected_books),
                '内容': raw_text, '金句': final_gold, 'AI分析': st.session_state['ai_result']
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            save_to_github(df, user_uid, file_sha)
            st.success("🎉 数据已同步，分类已存入 Data！")

elif page == "📂 结构化看板":
    st.header("📂 数字化教研看板")
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        
        # --- 新增：Excel 导出功能 ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        st.download_button("📥 导出全量 Excel", output.getvalue(), f"智库数据_{datetime.date.today()}.xlsx", use_container_width=True)
        
        st.divider()
        for i, row in df.iloc[::-1].iterrows():
            with st.expander(f"📌 {row['分类']} | {row['标题']}"):
                st.markdown(f"**核心金句：** :red[{row['金句']}]")
                c1, c2 = st.columns(2)
                with c1: st.info(row['内容'])
                with c2: st.success(row['AI分析'])
