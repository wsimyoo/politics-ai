import streamlit as st
import pandas as pd
from github import Github
import datetime

# --- 1. 初始化设置 ---
st.set_page_config(page_title="思政教研智库", layout="wide")

# 从 Secrets 获取配置
try:
    GH_TOKEN = st.secrets["GH_TOKEN"]
    GH_REPO = st.secrets["GH_REPO"]
except:
    st.sidebar.error("⚠️ 未配置 GitHub Token，数据将无法自动保存！")
    GH_TOKEN = None

# --- 2. 核心逻辑函数 ---
def get_github_repo():
    g = Github(GH_TOKEN)
    return g.get_repo(GH_REPO)

def load_data(uid):
    """从 GitHub 读取属于该用户的 CSV 文件"""
    file_path = f"material_lib_{uid}.csv"
    try:
        repo = get_github_repo()
        content = repo.get_contents(file_path)
        df = pd.read_csv(content.download_url)
        return df, content.sha
    except:
        # 如果文件不存在，返回空表
        return pd.DataFrame(columns=['时间', '标题', '分类', '内容', '金句']), None

def save_to_github(df, uid, sha):
    """将数据保存回 GitHub"""
    file_path = f"material_lib_{uid}.csv"
    csv_content = df.to_csv(index=False)
    repo = get_github_repo()
    if sha:
        repo.update_file(file_path, f"Update data for {uid}", csv_content, sha)
    else:
        repo.create_file(file_path, f"Initial data for {uid}", csv_content)

# --- 3. 侧边栏 ---
with st.sidebar:
    st.title("🛡️ 思政教研智库")
    api_key = st.text_input("输入 API Key 登录", type="password")
    
    if GH_TOKEN:
        st.success("✅ 云端同步：已连接")
    
    page = st.radio("功能导航", ["📝 素材录入", "📂 结构化看板"])

# 只有输入 Key 后才运行后续逻辑
if not api_key:
    st.info("请在左侧输入 API Key 开始工作")
    st.stop()

# 使用 API Key 的前 8 位作为用户唯一标识 (UID)
user_uid = api_key[:8]
df, file_sha = load_data(user_uid)

# --- 4. 页面功能 ---

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
        st.balloons()

elif page == "📂 结构化看板":
    st.header("📂 我的数字化教研室")
    
    if df.empty:
        st.warning("目前暂无存档素材，快去录入第一条吧！")
    else:
        # --- 恢复表格可视化 ---
        st.subheader("📊 汇总统计（表格模式）")
        # 允许搜索和筛选的交互式表格
        st.dataframe(
            df, 
            use_container_width=True, 
            column_config={
                "内容": st.column_config.TextColumn("详细内容", width="large"),
                "时间": st.column_config.DatetimeColumn("录入时间")
            }
        )
        
        st.divider()
        
        # --- 保持卡片美化 ---
        st.subheader("🗂️ 素材精选（卡片模式）")
        for index, row in df.iloc[::-1].iterrows(): # 倒序显示最新内容
            with st.expander(f"📌 {row['分类']} | {row['标题']}"):
                st.write(f"**录入时间：** {row['时间']}")
                st.markdown(f"**【核心金句】** :red[{row['金句']}]")
                st.info(row['content'] if 'content' in row else row['内容'])
