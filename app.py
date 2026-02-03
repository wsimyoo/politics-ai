import streamlit as st
import pandas as pd
from github import Github
import datetime
import io
from openai import OpenAI

# --- 1. 页面配置与增强样式 ---
st.set_page_config(page_title="思政教研智库", layout="wide")

# 视觉增强样式：增加一个“已存云端”的标签样式
st.markdown("""
    <style>
    .highlight-gold { background-color: #fff3cd; border-left: 5px solid #ffc107; padding: 15px; border-radius: 5px; color: #856404; font-weight: bold; margin-bottom: 15px; }
    .highlight-ai { background-color: #e7f3ff; border-left: 5px solid #007bff; padding: 15px; border-radius: 5px; color: #0c5460; line-height: 1.6; }
    .cloud-tag { background-color: #d4edda; color: #155724; padding: 2px 8px; border-radius: 10px; font-size: 0.8rem; font-weight: bold; border: 1px solid #c3e6cb; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心逻辑：读取公共教材库 (data.csv) ---
def get_github_repo():
    return Github(st.secrets["GH_TOKEN"]).get_repo(st.secrets["GH_REPO"])

def load_common_books():
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
        return ["必修1", "必修2", "必修3", "必修4", "选修1", "选修2", "选修3"]

book_options = load_common_books()

# --- 3. 首页登录拦截 ---
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

# --- 4. 个人数据处理（解决文件名显示不全问题） ---
client = OpenAI(api_key=st.session_state['api_key'], base_url="https://api.deepseek.com")
user_uid = st.session_state['api_key'][:8]
# 明确完整文件名变量
target_filename = f"material_lib_{user_uid}.csv"

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
    if sha: 
        return repo.update_file(file_path, f"Update {uid}", csv_content, sha)
    else: 
        return repo.create_file(file_path, f"Init {uid}", csv_content)

personal_df, personal_sha = load_personal_data(user_uid)

# --- 5. 侧边栏（明确显示完整文件名） ---
with st.sidebar:
    st.title("🛡️ 智库菜单")
    # 解决诉求：直接显示完整的 Data 文件名
    st.info(f"📂 当前云端文件：\n`{target_filename}`")
    page = st.radio("前往", ["📝 素材 AI 加工", "📂 结构化看板"])
    st.divider()
    if st.button("🚪 退出登录"):
        st.session_state['authenticated'] = False
        st.rerun()

# --- 6. 页面功能 ---

if page == "📝 素材 AI 加工":
    st.header("📝 教材深度分析")
    col_l, col_r = st.columns([2, 1])
    with col_l:
        raw_text = st.text_area("输入原始素材内容", height=350)
    with col_r:
        title = st.text_input("素材标题")
        mode = st.radio("分析模式", ["单本精读", "跨教材联动"])
        selected_books = st.multiselect("选择教材（读取自 data.csv）", options=book_options)
        
        if st.button("🤖 启动 AI 分析", use_container_width=True):
            with st.spinner("AI 正在跨教材解析..."):
                prompt = f"分析模式：{mode}。教材：{selected_books}。素材：{raw_text}。给出教材契合点、教学建议、金句。"
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": prompt}]
                )
                st.session_state['ai_result'] = response.choices[0].message.content

    if 'ai_result' in st.session_state:
        st.divider()
        st.markdown(f'<div class="highlight-ai">{st.session_state["ai_result"]}</div>', unsafe_allow_html=True)
        final_gold = st.text_input("确认金句", value="从上方提取...")
        
        # 解决诉求：保存动作必须显示明确的反馈
        if st.button(f"💾 立即保存至云端 ({target_filename})", use_container_width=True):
            new_row = {
                '时间': datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                '标题': title, '分类': " / ".join(selected_books),
                '内容': raw_text, '金句': final_gold, 'AI分析': st.session_state['ai_result']
            }
            updated_df = pd.concat([personal_df, pd.DataFrame([new_row])], ignore_index=True)
            try:
                save_to_github(updated_df, user_uid, personal_sha)
                st.toast("✅ 数据已成功推送到云端 GitHub 仓库！", icon="🎉")
                st.success(f"🎉 保存成功！文件已实时同步至：`{target_filename}`")
                st.balloons()
                # 重新加载，确保看板同步
                personal_df, personal_sha = load_personal_data(user_uid)
            except Exception as e:
                st.error(f"保存失败，请检查网络或配置：{e}")

elif page == "📂 结构化看板":
    st.header("📂 数字化教研看板")
    # 显示当前预览的文件名
    st.caption(f"当前数据来源：GitHub / {target_filename}")
    
    if personal_df.empty:
        st.info("云端暂无数据。")
    else:
        st.dataframe(personal_df, use_container_width=True)
        
        # Excel 导出
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            personal_df.to_excel(writer, index=False)
        st.download_button("📥 导出我的全量 Excel", output.getvalue(), f"Export_{target_filename.split('.')[0]}.xlsx", use_container_width=True)
        
        st.divider()
        for i, row in personal_df.iloc[::-1].iterrows():
            with st.expander(f"📌 {row['分类']} | {row['标题']}"):
                # 解决诉求：在每一条记录上明确显示“已存云端”标签
                st.markdown(f"<span class='cloud-tag'>☁️ 已存云端</span> **核心金句：** :red[**{row['金句']}**]", unsafe_allow_html=True)
                
                c1, c2 = st.columns(2)
                with c1: 
                    st.markdown("**【素材原文】**")
                    st.info(row['内容'])
                with c2: 
                    st.markdown("**【AI 解析】**")
                    st.markdown(f'<div class="highlight-ai">{row["AI分析"]}</div>', unsafe_allow_html=True)
