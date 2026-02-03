import streamlit as st
import pandas as pd
from github import Github
import datetime
import io
from openai import OpenAI

# --- 1. 页面配置与视觉样式 (保留所有高亮细节) ---
st.set_page_config(page_title="思政教研智库", layout="wide")

st.markdown("""
    <style>
    /* AI 解析的高亮蓝色框 */
    .highlight-ai { background-color: #e7f3ff; border-left: 5px solid #007bff; padding: 15px; border-radius: 8px; color: #0c5460; line-height: 1.6; }
    /* 云端存证标签 */
    .cloud-tag { background-color: #d4edda; color: #155724; padding: 2px 8px; border-radius: 10px; font-size: 0.8rem; font-weight: bold; border: 1px solid #c3e6cb; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心初始化：公共教材库 (精准指向 data/data.csv) ---
def get_github_repo():
    return Github(st.secrets["GH_TOKEN"]).get_repo(st.secrets["GH_REPO"])

def load_common_books():
    """从 data 文件夹中读取 data.csv，绝不瞎编"""
    try:
        repo = get_github_repo()
        # 路径修正：进入 data 文件夹读取
        content_file = repo.get_contents("data/data.csv")
        common_df = pd.read_csv(content_file.download_url)
        unique_cats = set()
        if '分类' in common_df.columns:
            for entry in common_df['分类'].dropna():
                # 处理多选存储的拆分逻辑
                parts = [p.strip() for p in str(entry).split('/') if p.strip()]
                unique_cats.update(parts)
        return sorted(list(unique_cats)), "data/data.csv (读取成功 ✅)"
    except Exception as e:
        # 诊断：如果失败，显示文件夹内的真实情况
        try:
            repo = get_github_repo()
            files = repo.get_contents("data")
            diag = [f.name for f in files]
            msg = f"❌ 在 data/ 没找到 data.csv。现有：{diag}"
        except:
            msg = f"❌ 找不到 data 文件夹，请检查 GitHub 结构"
        return ["必修1", "必修2", "必修3", "必修4"], msg

book_options, source_status = load_common_books()

# --- 3. 首页登录拦截 (保留按钮点击逻辑) ---
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

# --- 5. 侧边栏 (路径全显) ---
with st.sidebar:
    st.title("🛡️ 教研管理")
    st.write("📖 **公共教材库：**")
    st.caption(source_status)
    st.write("💾 **个人存档文件：**")
    st.code(full_personal_filename)
    
    page = st.radio("前往", ["📝 素材 AI 加工", "📂 结构化看板"])
    st.divider()
    if st.button("🚪 退出登录"):
        st.session_state['authenticated'] = False
        st.rerun()

# --- 6. 核心功能：联动分析 ---
if page == "📝 素材 AI 加工":
    st.header("📝 跨教材联动加工")
    col_l, col_r = st.columns([2, 1])
    with col_l:
        raw_text = st.text_area("输入原始素材（新闻、案例、语段）", height=400)
    with col_r:
        title = st.text_input("素材标题")
        mode = st.radio("分析模式", ["单本精读", "跨教材联动分析"])
        # 联动核心：教材多选
        selected_books = st.multiselect("匹配教材库 (来自 data/data.csv)", options=book_options)
        
        if st.button("🤖 启动 AI 联动分析", use_container_width=True):
            if raw_text and selected_books:
                with st.spinner(f"正在深度联动 {selected_books} ..."):
                    # 联动提示词：要求 AI 必须找多本教材的交叉点
                    prompt = f"""
                    你是一名思政专家。请结合教材：{selected_books}，对素材：{raw_text} 进行分析。
                    分析模式：{mode}。
                    要求：
                    1. 【教材契合点】必须指明素材如何同时关联这几本教材的不同知识点。
                    2. 【教学建议】给出针对性的跨教材教学环节。
                    3. 【核心金句】提炼一句政治站位高、富有文采的总结。
                    """
                    response = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    st.session_state['ai_result'] = response.choices[0].message.content

    if 'ai_result' in st.session_state:
        st.divider()
        st.markdown(f'<div class="highlight-ai">{st.session_state["ai_result"]}</div>', unsafe_allow_html=True)
        final_gold = st.text_input("确认核心金句", value="提炼精华...")
        
        if st.button(f"💾 保存至个人库：{full_personal_filename}", use_container_width=True):
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
            st.success(f"🎉 联动成果已同步至 `{full_personal_filename}`")
            st.balloons()

elif page == "📂 结构化看板":
    st.header(f"📂 我的存档：{full_personal_filename}")
    if personal_df.empty:
        st.info("暂无存档数据。")
    else:
        st.dataframe(personal_df, use_container_width=True)
        # Excel 导出
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            personal_df.to_excel(writer, index=False)
        st.download_button(f"📥 导出 Excel", output.getvalue(), f"Export_{user_uid}.xlsx", use_container_width=True)
        
        st.divider()
        for i, row in personal_df.iloc[::-1].iterrows():
            with st.expander(f"📌 {row['分类']} | {row['标题']}"):
                st.markdown(f"<span class='cloud-tag'>☁️ 云端同步</span> **核心金句：** :red[**{row['金句']}**]", unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**【素材原文】**")
                    st.info(row['内容'])
                with c2:
                    st.markdown("**【跨教材联动解析】**")
                    st.markdown(f'<div class="highlight-ai">{row["AI分析"]}</div>', unsafe_allow_html=True)
