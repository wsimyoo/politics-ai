import streamlit as st
import pandas as pd
from github import Github
import datetime
import io
from openai import OpenAI

# --- 1. 页面基本配置 ---
st.set_page_config(page_title="思政教研智库", layout="wide")

# --- 2. 自定义视觉高亮样式 ---
st.markdown("""
    <style>
    /* 金句高亮：黄色背景+金边 */
    .highlight-gold { 
        background-color: #fff3cd; 
        border-left: 5px solid #ffc107; 
        padding: 15px; 
        border-radius: 5px; 
        color: #856404; 
        font-weight: bold;
        margin-bottom: 15px;
    }
    /* AI分析高亮：蓝色背景+蓝边 */
    .highlight-ai { 
        background-color: #e7f3ff; 
        border-left: 5px solid #007bff; 
        padding: 15px; 
        border-radius: 5px; 
        color: #0c5460;
        line-height: 1.6;
    }
    /* 标题美化 */
    .main-title { text-align: center; color: #1E3A8A; margin-bottom: 0; }
    .sub-title { text-align: center; color: #64748B; font-size: 1rem; margin-bottom: 2rem; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 首页登录状态控制 ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    st.markdown("<h1 class='main-title'>🛡️ 思政教研智库</h1>", unsafe_allow_html=True)
    st.markdown("<p class='sub-title'>AI 深度赋能 · 单本/跨教材联动 · 云端永久同步</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        input_key = st.text_input("🔑 请输入您的 API Key 登录", type="password")
        if st.button("🚀 点击解锁进入智库", use_container_width=True):
            if input_key:
                st.session_state['authenticated'] = True
                st.session_state['api_key'] = input_key
                st.rerun()
            else:
                st.warning("请先输入有效的 API Key")
    st.stop()

# --- 4. 初始化 AI 与 GitHub 连接 ---
# 使用 DeepSeek 作为 AI 引擎
client = OpenAI(api_key=st.session_state['api_key'], base_url="https://api.deepseek.com")
user_uid = st.session_state['api_key'][:8] # 取 Key 前8位作为用户 ID

def get_github_repo():
    return Github(st.secrets["GH_TOKEN"]).get_repo(st.secrets["GH_REPO"])

def load_data(uid):
    file_path = f"material_lib_{uid}.csv"
    try:
        repo = get_github_repo()
        content_file = repo.get_contents(file_path)
        df = pd.read_csv(content_file.download_url)
        # 补全可能缺失的 AI分析 列
        if 'AI分析' not in df.columns: df['AI分析'] = ""
        return df, content_file.sha
    except:
        return pd.DataFrame(columns=['时间', '标题', '分类', '内容', '金句', 'AI分析']), None

def save_to_github(df, uid, sha):
    file_path = f"material_lib_{uid}.csv"
    csv_content = df.to_csv(index=False)
    repo = get_github_repo()
    if sha:
        repo.update_file(file_path, f"Update {uid}", csv_content, sha)
    else:
        repo.create_file(file_path, f"Init {uid}", csv_content)

# 初始化读取用户云端数据
df, file_sha = load_data(user_uid)

# --- 5. 侧边栏 ---
with st.sidebar:
    st.title("🛡️ 智库管理")
    st.success(f"👤 当前用户: {user_uid}")
    page = st.radio("功能切换", ["📝 素材 AI 加工", "📂 结构化看板"])
    st.divider()
    if st.button("🚪 退出登录"):
        st.session_state['authenticated'] = False
        st.rerun()

# --- 6. 功能区分发 ---

# A. 素材 AI 加工页
if page == "📝 素材 AI 加工":
    st.header("📝 教材深度分析与加工")
    
    col_l, col_r = st.columns([2, 1])
    with col_l:
        raw_text = st.text_area("输入原始素材（新闻、案例、语段）", height=400, placeholder="在此粘贴素材内容...")
    
    with col_r:
        title = st.text_input("素材标题")
        mode = st.radio("分析模式", ["单本教材精读", "跨教材综合联动"])
        selected_books = st.multiselect("选择关联教材（可多选）", [
            "必修1：中国特色社会主义", "必修2：经济与社会", 
            "必修3：政治与法治", "必修4：哲学与文化",
            "选修1：当代国际政治与经济", "选修2：法律与生活", "选修3：逻辑与思维"
        ])
        
        if st.button("🤖 启动 AI 教研助手", use_container_width=True):
            if raw_text and selected_books:
                with st.spinner("AI 正在深度解析并高亮重点..."):
                    prompt = f"""
                    你是一名资深高中思政特级教师。
                    分析模式：{mode}
                    关联教材：{', '.join(selected_books)}
                    原始素材内容：{raw_text}
                    
                    请提供以下维度的深度解析：
                    1. 【教材契合点】详细说明素材与所选教材的具体课次、原理如何对应。
                    2. 【跨教材逻辑】（若为多本教材）分析不同模块间的内在联系。
                    3. 【教学建议】设计一个互动问题或教学活动建议。
                    4. 【核心金句】提炼一句适合作为板书或学生背诵的灵魂总结。
                    """
                    response = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[{"role": "system", "content": "你是一个精通教材结构的教研专家"}, {"role": "user", "content": prompt}]
                    )
                    st.session_state['ai_result'] = response.choices[0].message.content
            else:
                st.warning("请确保已填写内容并勾选了教材")

    # AI 结果展示区
    if 'ai_result' in st.session_state:
        st.divider()
        st.subheader("💡 AI 教研解析结果")
        # 结果高亮展示
        st.markdown(f'<div class="highlight-ai">{st.session_state["ai_result"]}</div>', unsafe_allow_html=True)
        
        final_gold = st.text_input("确认核心金句（可在此微调）", value="从上方分析中提取关键句...")
        
        if st.button("💾 永久归档至云端"):
            if title:
                new_row = {
                    '时间': datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                    '标题': title,
                    '分类': " / ".join(selected_books),
                    '内容': raw_text,
                    '金句': final_gold,
                    'AI分析': st.session_state['ai_result']
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                save_to_github(df, user_uid, file_sha)
                st.success(f"🎉 素材《{title}》已同步至云端！")
                st.balloons()
            else:
                st.error("请输入素材标题后再存档")

# B. 结构化看板页
elif page == "📂 结构化看板":
    st.header("📂 我的数字化教研看板")
    
    if df.empty:
        st.warning("云端仓库目前为空，请先前往录入素材。")
    else:
        # 1. 表格可视化
        st.subheader("📊 全量素材总表")
        st.dataframe(df, use_container_width=True)
        
        # 2. Excel 导出功能
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='思政素材库')
        
        st.download_button(
            label="📥 导出全量 Excel 存档",
            data=output.getvalue(),
            file_name=f"思政教研智库_{datetime.date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
        st.divider()
        
        # 3. 深度预览（高亮卡片模式）
        st.subheader("🗂️ 素材深度预览 (最新录入在前)")
        for i, row in df.iloc[::-1].iterrows():
            with st.expander(f"📌 {row['分类']} | {row['标题']}"):
                # 金句高亮
                st.markdown(f'<div class="highlight-gold">🔑 核心金句：{row["金句"]}</div>', unsafe_allow_html=True)
                
                col_a, col_b = st.columns(2)
                with col_a: 
                    st.markdown("**【原始素材内容】**")
                    st.info(row['内容'])
                with col_b: 
                    st.markdown("**【AI 跨教材深度解析】**")
                    # AI分析结果高亮
                    st.markdown(f'<div class="highlight-ai">{row["AI分析"]}</div>', unsafe_allow_html=True)


