import streamlit as st
import pandas as pd
from github import Github
import datetime
import io
from openai import OpenAI

# --- 1. 页面配置与视觉样式 (全保留，无简化) ---
st.set_page_config(page_title="思政教研智库", layout="wide")

st.markdown("""
    <style>
    .highlight-gold { background-color: #fff3cd; border-left: 5px solid #ffc107; padding: 15px; border-radius: 5px; color: #856404; font-weight: bold; margin-bottom: 15px; }
    .highlight-ai { background-color: #e7f3ff; border-left: 5px solid #007bff; padding: 15px; border-radius: 5px; color: #0c5460; line-height: 1.6; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心逻辑：读取公共教材库 (data.csv) ---
def get_github_repo():
    return Github(st.secrets["GH_TOKEN"]).get_repo(st.secrets["GH_REPO"])

def load_common_books():
    """严格读取 data.csv，确保教材分类不消失"""
    try:
        repo = get_github_repo()
        content_file = repo.get_contents("data.csv")
        common_df = pd.read_csv(content_file.download_url)
        unique_cats = set()
        if '分类' in common_df.columns:
            for entry in common_df['分类'].dropna():
                parts = [p.strip() for p in str(entry).split('/') if p.strip()]
                unique_cats.update(parts)
        return sorted(list(unique_cats))
    except:
        # 兜底默认值，防止由于 data.csv 缺失导致报错
        return ["必修1", "必修2", "必修3", "必修4", "选修1", "选修2", "选修3"]

# 预加载教材库
book_options = load_common_books()

# --- 3. 首页登录拦截 (新增：点击登录按钮) ---
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

# --- 4. 私人数据处理 ---
client = OpenAI(api_key=st.session_state['api_key'], base_url="https://api.deepseek.com")
user_uid = st.session_state['api_key'][:8]

def load_personal_data(uid):
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

personal_df, personal_sha = load_personal_data(user_uid)

# --- 5. 功能导航 ---
with st.sidebar:
    st.title("🛡️ 智库菜单")
    page = st.radio("前往", ["📝 素材 AI 加工", "📂 结构化看板"])
    if st.button("🚪 退出登录"):
        st.session_state['authenticated'] = False
        st.rerun()

# --- 6. 页面功能 (保留所有跨教材、高亮细节) ---

if page == "📝 素材 AI 加工":
    st.header("📝 教材深度分析与加工")
    col_l, col_r = st.columns([2, 1])
    with col_l:
        raw_text = st.text_area("输入原始素材（新闻、案例、语段）", height=400)
    with col_r:
        title = st.text_input("素材标题")
        mode = st.radio("分析模式", ["单本精读", "跨教材综合联动分析"])
        # 教材选择读取自公共 Data
        selected_books = st.multiselect("涉及教材分类", options=book_options)
        
        if st.button("🤖 启动 AI 分析", use_container_width=True):
            if raw_text and selected_books:
                with st.spinner("AI 正在跨教材深度解析..."):
                    prompt = f"分析模式：{mode}。涉及教材：{selected_books}。素材：{raw_text}。请给出：1.教材契合点 2.教学建议 3.核心金句。"
                    response = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    st.session_state['ai_result'] = response.choices[0].message.content

    if 'ai_result' in st.session_state:
        st.divider()
        st.subheader("💡 AI 教研成果 (已标识重点)")
        # 保持分析结果高亮显示
        st.markdown(f'<div class="highlight-ai">{st.session_state["ai_result"]}</div>', unsafe_allow_html=True)
        
        final_gold = st.text_input("确认核心金句（金句将红字加粗显示）", value="从上方分析中提取...")
        
        if st.button("💾 归档并同步私人素材库"):
            new_row = {
                '时间': datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                '标题': title, '分类': " / ".join(selected_books),
                '内容': raw_text, '金句': final_gold, 'AI分析': st.session_state['ai_result']
            }
            personal_df = pd.concat([personal_df, pd.DataFrame([new_row])], ignore_index=True)
            save_to_github(personal_df, user_uid, personal_sha)
            st.success(f"🎉 素材已同步至您的私人库 material_lib_{user_uid}.csv")

elif page == "📂 结构化看板":
    st.header("📂 我的数字化教研看板")
    if personal_df.empty:
        st.info("您的私人素材库目前没有存档。")
    else:
        st.subheader("📊 汇总统计表")
        st.dataframe(personal_df, use_container_width=True)
        
        # --- 新增：Excel 导出功能 ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            personal_df.to_excel(writer, index=False)
        st.download_button("📥 导出我的全量 Excel", output.getvalue(), f"教研存档_{user_uid}.xlsx", use_container_width=True)
        
        st.divider()
        st.subheader("🗂️ 深度内容预览 (重点高亮模式)")
        for i, row in personal_df.iloc[::-1].iterrows():
            with st.expander(f"📌 {row['分类']} | {row['标题']}"):
                # 核心功能：金句红字加粗
                st.markdown(f"**核心金句：** :red[**{row['金句']}**]")
                
                # 核心功能：双分栏对比展示
                c1, c2 = st.columns(2)
                with c1: 
                    st.markdown("**【原始素材内容】**")
                    st.info(row['content'] if 'content' in row else row['内容'])
                with c2: 
                    st.markdown("**【AI 跨教材深度解析】**")
                    # 保持 AI 分析的高亮样式
                    st.markdown(f'<div class="highlight-ai">{row["AI分析"]}</div>', unsafe_allow_html=True)
