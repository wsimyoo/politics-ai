import streamlit as st
import pandas as pd
from github import Github
import datetime

# --- 1. 页面基本配置 ---
st.set_page_config(page_title="思政教研智库", layout="wide")

# --- 2. 登录状态控制 (新增逻辑) ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

# 如果还没登录，显示首页登录界面
if not st.session_state['authenticated']:
    st.markdown("<h1 style='text-align: center;'>🛡️ 思政教研智库</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>请解锁您的私人教研空间</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        input_key = st.text_input("输入 API Key 登录", type="password")
        if input_key:
            st.session_state['authenticated'] = True
            st.session_state['api_key'] = input_key
            st.rerun()
    st.stop() # 强制停止，不显示下方内容

# --- 3. 登录成功后，获取之前的配置 (保持不变) ---
api_key = st.session_state['api_key']
user_uid = api_key[:8]

def get_github_repo():
    GH_TOKEN = st.secrets["GH_TOKEN"]
    GH_REPO = st.secrets["GH_REPO"]
    g = Github(GH_TOKEN)
    return g.get_repo(GH_REPO)

def load_data(uid):
    file_path = f"material_lib_{uid}.csv"
    try:
        repo = get_github_repo()
        content = repo.get_contents(file_path)
        df = pd.read_csv(content.download_url)
        return df, content.sha
    except:
        return pd.DataFrame(columns=['时间', '标题', '分类', '内容', '金句']), None

def save_to_github(df, uid, sha):
    file_path = f"material_lib_{uid}.csv"
    csv_content = df.to_csv(index=False)
    repo = get_github_repo()
    if sha:
        repo.update_file(file_path, f"Update {uid}", csv_content, sha)
    else:
        repo.create_file(file_path, f"Init {uid}", csv_content)

df, file_sha = load_data(user_uid)

# --- 4. 功能导航与侧边栏 (保持不变) ---
with st.sidebar:
    st.title("🛡️ 功能菜单")
    st.success(f"当前用户: {user_uid}")
    page = st.radio("功能导航", ["📝 素材录入", "📂 结构化看板"])
    if st.button("退出登录"):
        st.session_state['authenticated'] = False
        st.rerun()

# --- 5. 核心功能区 (保持不变) ---
if page == "📝 素材录入":
    st.header("📝 新素材加工")
    col1, col2 = st.columns(2)
    with col1:
        title = st.text_input("素材标题")
        category = st.selectbox("教材分类", ["必修1", "必修2", "必修3", "必修4", "选修"])
    with col2:
        golden_sentence = st.text_input("核心金句")
    
    content = st.text_area("素材详情内容", height=200)

    if st.button("💾 归档并永久保存到云端"):
        new_data = {
            '时间': datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            '标题': title,
            '分类': category,
            '内容': content,
            '金句': golden_sentence
        }
        df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
        save_to_github(df, user_uid, file_sha)
        st.success("🎉 数据已安全存入云端仓库！")

elif page == "📂 结构化看板":
    st.header("📂 我的数字化教研室")
    if df.empty:
        st.warning("暂无存档。")
    else:
        st.subheader("📊 汇总统计（表格模式）")
        st.dataframe(df, use_container_width=True)
        
        st.divider()
        st.subheader("🗂️ 素材精选（卡片模式）")
        for index, row in df.iloc[::-1].iterrows():
            with st.expander(f"📌 {row['分类']} | {row['标题']}"):
                st.write(f"**录入时间：** {row['时间']}")
                st.markdown(f"**【核心金句】** :red[{row['金句']}]")
                st.info(row['内容'])

