import streamlit as st
import pandas as pd
from github import Github
import datetime
import io
from openai import OpenAI

# --- 1. 页面配置与样式 ---
st.set_page_config(page_title="思政教研智库", layout="wide")

# --- 2. 首页登录（严格执行：输入+按钮） ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    st.markdown("<h1 style='text-align: center;'>🛡️ 思政教研智库</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        input_key = st.text_input("🔑 输入 API Key", type="password")
        if st.button("🚀 点击解锁进入系统", use_container_width=True):
            if input_key:
                st.session_state['authenticated'] = True
                st.session_state['api_key'] = input_key
                st.rerun()
    st.stop()

# --- 3. 初始化 ---
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

df, file_sha = load_data(user_uid)

# --- 4. 教材动态读取逻辑（精准修正点） ---
# 逻辑：从您 CSV 的“分类”列里提取所有出现过的教材名
if not df.empty and '分类' in df.columns:
    unique_cats = set()
    for entry in df['分类'].dropna():
        # 拆分之前多选存入的 " / "
        parts = [p.strip() for p in str(entry).split('/') if p.strip()]
        unique_cats.update(parts)
    book_options = sorted(list(unique_cats))
else:
    book_options = []

# --- 5. 侧边栏 ---
with st.sidebar:
    st.title("🛡️ 菜单")
    page = st.radio("功能切换", ["📝 素材 AI 加工", "📂 结构化看板"])
    if st.button("退出登录"):
        st.session_state['authenticated'] = False
        st.rerun()

# --- 6. 功能区 ---
if page == "📝 素材 AI 加工":
    st.header("📝 教材深度分析")
    col_l, col_r = st.columns([2, 1])
    with col_l:
        raw_text = st.text_area("输入原始素材内容", height=300)
    
    with col_r:
        title = st.text_input("素材标题")
        mode = st.radio("分析模式", ["单本精读", "跨教材联动"])
        
        # 这里是您最关心的：教材多选
        # 如果 book_options 为空（新用户），这里会自动提示您添加
        selected_books = st.multiselect("涉及教材分类（读取自您的 Data）", options=book_options)
        
        # 这个输入框是“点睛之笔”：不仅是新增，它也是您“初始化”教材库的唯一入口
        new_book = st.text_input("✨ 输入新教材名（如：必修1）并回车")
        if new_book and new_book not in selected_books:
            selected_books.append(new_book)
            if new_book not in book_options:
                book_options.append(new_book)

        if st.button("🤖 启动 AI 分析", use_container_width=True):
            if not selected_books:
                st.error("请先在上方输入或选择教材分类！")
            elif not raw_text:
                st.error("请输入素材内容！")
            else:
                with st.spinner("AI 正在解析..."):
                    prompt = f"模式：{mode}。教材：{selected_books}。内容：{raw_text}。给出教材契合点、教学建议、金句。"
                    response = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    st.session_state['ai_result'] = response.choices[0].message.content

    if 'ai_result' in st.session_state:
        st.divider()
        st.success(st.session_state['ai_result'])
        final_gold = st.text_input("确认核心金句")
        if st.button("💾 永久归档"):
            new_row = {
                '时间': datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                '标题': title,
                '分类': " / ".join(selected_books), # 存入 Data
                '内容': raw_text, '金句': final_gold, 'AI分析': st.session_state['ai_result']
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            save_to_github(df, user_uid, file_sha)
            st.success("🎉 数据已存入 Data，新教材分类已永久生效！")

elif page == "📂 结构化看板":
    st.header("📂 数字化教研看板")
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        # Excel 导出
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        st.download_button("📥 导出 Excel", output.getvalue(), f"智库_{datetime.date.today()}.xlsx")
        
        st.divider()
        for i, row in df.iloc[::-1].iterrows():
            with st.expander(f"📌 {row['分类']} | {row['标题']}"):
                st.markdown(f"**核心金句：** :red[{row['金句']}]")
                c1, c2 = st.columns(2)
                with c1: st.info(row['内容'])
                with c2: st.success(row['AI分析'])
