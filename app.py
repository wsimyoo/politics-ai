import streamlit as st
import pandas as pd
from github import Github
import datetime
import io
from openai import OpenAI

# --- 1. 样式与配置 (恢复最稳定的美化方案) ---
st.set_page_config(page_title="思政教研智库", layout="wide")

st.markdown("""
    <style>
    .highlight-ai { 
        background-color: #f8fbff; border-left: 5px solid #007bff; 
        padding: 20px; border-radius: 10px; color: #1a1a1a; line-height: 1.7;
    }
    .cloud-tag { 
        background-color: #e6fffa; color: #2c7a7b; padding: 3px 10px; 
        border-radius: 15px; font-size: 0.85rem; font-weight: bold; border: 1px solid #b2f5ea;
    }
    .stDataFrame { border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心逻辑：PDF 自动识别 ---
def get_github_repo():
    return Github(st.secrets["GH_TOKEN"]).get_repo(st.secrets["GH_REPO"])

def load_books_from_folder():
    try:
        repo = get_github_repo()
        files = repo.get_contents("data")
        # 提取文件名并去掉后缀
        books = [f.name.replace(".pdf", "") for f in files if f.name.endswith(".pdf")]
        return sorted(books), "data/ (教材库已连接 ✅)"
    except Exception as e:
        return ["必修1", "必修2", "必修3", "必修4"], f"❌ 读取失败: {str(e)}"

book_options, source_status = load_books_from_folder()

# --- 3. 登录拦截 ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    st.markdown("<h1 style='text-align: center;'>🛡️ 思政教研智库</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        input_key = st.text_input("🔑 输入 API Key", type="password")
        if st.button("🚀 进入系统", use_container_width=True):
            if input_key:
                st.session_state['authenticated'] = True
                st.session_state['api_key'] = input_key
                st.rerun()
    st.stop()

# --- 4. 个人数据同步 (增加字段兼容性检查) ---
client = OpenAI(api_key=st.session_state['api_key'], base_url="https://api.deepseek.com")
user_uid = st.session_state['api_key'][:8]
full_filename = f"material_lib_{user_uid}.csv"

def load_personal_data(uid):
    file_path = f"material_lib_{uid}.csv"
    try:
        repo = get_github_repo()
        content_file = repo.get_contents(file_path)
        df = pd.read_csv(content_file.download_url)
        # 兼容性处理：统一列名
        rename_map = {'素材标题': '标题', '原始内容': '内容'}
        df = df.rename(columns=rename_map)
        return df, content_file.sha
    except:
        return pd.DataFrame(columns=['时间', '标题', '分类', '内容', 'AI分析']), None

if 'personal_df' not in st.session_state:
    df, sha = load_personal_data(user_uid)
    st.session_state['personal_df'] = df
    st.session_state['personal_sha'] = sha

# --- 5. 侧边栏 ---
with st.sidebar:
    st.title("🛡️ 智库管理")
    st.caption(f"📖 {source_status}")
    st.code(f"文件：{full_filename}")
    page = st.radio("前往", ["📝 跨教材联动加工", "📂 结构化看板"])
    
    if st.button("🔄 刷新数据"):
        df, sha = load_personal_data(user_uid)
        st.session_state['personal_df'] = df
        st.session_state['personal_sha'] = sha
        st.rerun()
    
    st.divider()
    if st.button("🚪 退出"):
        st.session_state.clear()
        st.rerun()

# --- 6. 加工页 ---
if page == "📝 跨教材联动加工":
    st.header("📝 跨教材联动加工")
    col_l, col_r = st.columns([2, 1])
    with col_l:
        raw_text = st.text_area("输入原始素材内容", height=400)
    with col_r:
        material_title = st.text_input("素材标题 (必填)")
        mode = st.radio("模式", ["单本精读", "跨教材联动"])
        selected_books = st.multiselect("匹配教材", options=book_options)
        
        if st.button("🤖 启动 AI 分析", use_container_width=True):
            if raw_text and selected_books and material_title:
                with st.spinner("联动解析中..."):
                    prompt = f"教材：{selected_books}。素材：{raw_text}。请给出：1.教材契合点 2.教学建议。必须针对所选PDF教材进行分析。"
                    response = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    st.session_state['ai_result'] = response.choices[0].message.content
            else:
                st.warning("⚠️ 请确保标题、内容和教材均已填写或选择。")

    if 'ai_result' in st.session_state:
        st.divider()
        st.markdown(f'<div class="highlight-ai">{st.session_state["ai_result"]}</div>', unsafe_allow_html=True)
        
        if st.button(f"💾 归档并保存至云端", use_container_width=True):
            new_row = {
                '时间': datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                '标题': material_title, 
                '分类': " / ".join(selected_books),
                '内容': raw_text, 
                'AI分析': st.session_state['ai_result']
            }
            # 更新 Session
            st.session_state['personal_df'] = pd.concat([st.session_state['personal_df'], pd.DataFrame([new_row])], ignore_index=True)
            
            # 推送到 GitHub
            repo = get_github_repo()
            csv_content = st.session_state['personal_df'].to_csv(index=False)
            if st.session_state['personal_sha']:
                repo.update_file(full_filename, "Update", csv_content, st.session_state['personal_sha'])
            else:
                repo.create_file(full_filename, "Init", csv_content)
            
            # 更新本地 SHA
            _, new_sha = load_personal_data(user_uid)
            st.session_state['personal_sha'] = new_sha
            st.success("🎉 已成功存入云端看板！")
            st.balloons()

# --- 7. 看板页 (修复标题不显示问题) ---
elif page == "📂 结构化看板":
    st.header("📂 我的数字化看板")
    df_display = st.session_state['personal_df']
    
    if df_display.empty:
        st.info("暂无数据。")
    else:
        # 1. 顶部宽屏概览表
        st.dataframe(df_display[['时间', '标题', '分类']], use_container_width=True, hide_index=True)
        
        # 2. 导出功能
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_display.to_excel(writer, index=False)
        st.download_button("📥 导出全量 Excel", output.getvalue(), f"Export_{user_uid}.xlsx")
        
        st.divider()
        # 3. 详细内容卡片
        for i, row in df_display.iloc[::-1].iterrows():
            # 兼容性读取：如果'标题'列为空，尝试读取其他可能的字段
            display_title = row.get('标题', '未命名素材')
            
            with st.expander(f"📌 {row['分类']} | {display_title}", expanded=(i == len(df_display)-1)):
                st.markdown(f"<span class='cloud-tag'>☁️ 云端已同步</span>", unsafe_allow_html=True)
                c_raw, c_ai = st.columns(2)
                with c_raw:
                    st.markdown("**【素材内容】**")
                    st.info(row['内容'])
                with c_ai:
                    st.markdown("**【跨教材联动分析】**")
                    st.markdown(f'<div class="highlight-ai">{row["AI分析"]}</div>', unsafe_allow_html=True)
