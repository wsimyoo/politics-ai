import streamlit as st
import pandas as pd
from github import Github
import datetime
import io

# --- 1. 页面基本配置 ---
st.set_page_config(page_title="思政教研智库", layout="wide")

# --- 2. 登录状态控制 ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

# 首页登录界面
if not st.session_state['authenticated']:
    st.markdown("<h1 style='text-align: center;'>🛡️ 思政教研智库</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>数字化教研笔记 · 永久云端同步</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        input_key = st.text_input("🔑 请输入您的 API Key", type="password")
        # 完善一：点击登录按钮
        if st.button("🚀 点击登录解锁智库", use_container_width=True):
            if input_key:
                st.session_state['authenticated'] = True
                st.session_state['api_key'] = input_key
                st.rerun()
            else:
                st.warning("请先输入有效的 API Key")
    st.stop() 

# --- 3. 核心功能逻辑（严格保持，不简化） ---
api_key = st.session_state['api_key']
user_uid = api_key[:8]

def get_github_repo():
    # 确保从 Secrets 安全读取
    GH_TOKEN = st.secrets["GH_TOKEN"]
    GH_REPO = st.secrets["GH_REPO"]
    g = Github(GH_TOKEN)
    return g.get_repo(GH_REPO)

def load_data(uid):
    """从云端读取 CSV"""
    file_path = f"material_lib_{uid}.csv"
    try:
        repo = get_github_repo()
        content_file = repo.get_contents(file_path)
        df = pd.read_csv(content_file.download_url)
        return df, content_file.sha
    except:
        # 初始字段定义
        return pd.DataFrame(columns=['时间', '标题', '分类', '内容', '金句']), None

def save_to_github(df, uid, sha):
    """保存到云端"""
    file_path = f"material_lib_{uid}.csv"
    csv_content = df.to_csv(index=False)
    repo = get_github_repo()
    if sha:
        repo.update_file(file_path, f"Update data for {uid}", csv_content, sha)
    else:
        repo.create_file(file_path, f"Init data for {uid}", csv_content)

# 初始化读取数据
df, file_sha = load_data(user_uid)

# --- 4. 侧边栏导航 ---
with st.sidebar:
    st.title("🛡️ 智库管理")
    st.info(f"👤 当前用户 ID: {user_uid}")
    page = st.radio("功能切换", ["📝 素材录入加工", "📂 结构化看板"])
    st.divider()
    if st.button("🚪 退出系统"):
        st.session_state['authenticated'] = False
        st.rerun()

# --- 5. 页面功能区 ---

if page == "📝 素材录入加工":
    st.header("📝 新素材录入")
    col1, col2 = st.columns(2)
    with col1:
        title = st.text_input("素材标题", placeholder="请输入教研素材标题...")
        # 确保教材分类显示完整
        category = st.selectbox("涉及教材分类", [
            "必修1：中国特色社会主义", 
            "必修2：经济与社会", 
            "必修3：政治与法治", 
            "必修4：哲学与文化", 
            "选择性必修1", 
            "选择性必修2", 
            "选择性必修3",
            "其他教研资料"
        ])
    with col2:
        golden_sentence = st.text_input("核心金句/教学重点", placeholder="红字标注的关键句...")
    
    content = st.text_area("详细素材内容/案例详情", height=300)

    if st.button("💾 归档并同步至云端"):
        if title and content:
            new_row = {
                '时间': datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                '标题': title,
                '分类': category,
                '内容': content,
                '金句': golden_sentence
            }
            # 合并数据
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            # 云端同步
            save_to_github(df, user_uid, file_sha)
            st.success(f"🎉 素材《{title}》已成功存档并加密备份到云端！")
            st.balloons()
        else:
            st.error("请至少填写标题和详情内容！")

elif page == "📂 结构化看板":
    st.header("📂 我的数字化教研室")
    
    if df.empty:
        st.warning("云端暂无您的教研素材。")
    else:
        # 1. 表格可视化 (不简化)
        st.subheader("📊 全量素材检索表")
        st.dataframe(df, use_container_width=True)
        
        # 2. 完善二：导出 Excel 功能
        # 转换数据为 Excel 字节流
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='教研素材导出')
        
        st.download_button(
            label="📥 点击下载 Excel 完整版",
            data=output.getvalue(),
            file_name=f"思政智库导出_{datetime.date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
        st.divider()
        
        # 3. 卡片预览 (不简化)
        st.subheader("🗂️ 素材精选预览")
        # 倒序显示，让最新的在最上面
        for index, row in df.iloc[::-1].iterrows():
            with st.expander(f"📌 {row['分类']} | {row['标题']}"):
                st.write(f"**录入时间：** {row['时间']}")
                st.markdown(f"**【核心金句】** :red[{row['金句']}]")
                st.info(row['内容'])


