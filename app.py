import streamlit as st
import pandas as pd
from github import Github
import datetime
import io
from openai import OpenAI

# --- 1. 页面配置与视觉样式 ---
st.set_page_config(page_title="思政教研智库", layout="wide")

# 自定义高亮样式 CSS
st.markdown("""
    <style>
    .highlight-gold { 
        background-color: #fff3cd; 
        border-left: 5px solid #ffc107; 
        padding: 15px; 
        border-radius: 5px; 
        color: #856404; 
        font-weight: bold;
        margin-bottom: 15px;
    }
    .highlight-ai { 
        background-color: #e7f3ff; 
        border-left: 5px solid #007bff; 
        padding: 15px; 
        border-radius: 5px; 
        color: #0c5460;
        line-height: 1.6;
    }
    .main-title { text-align: center; color: #1E3A8A; margin-bottom: 0.5rem; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 首页登录拦截逻辑 ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    st.markdown("<h1 class='main-title'>🛡️ 思政教研智库</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>AI 深度解析 · 动态教材联动 · 永久同步云端</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        input_key = st.text_input("🔑 请输入 API Key 解锁智库", type="password")
        # 完善一：点击登录按钮
        if st.button("🚀 点击进入系统", use_container_width=True):
            if input_key:
                st.session_state['authenticated'] = True
                st.session_state['api_key'] = input_key
                st.rerun()
            else:
                st.warning("请先输入有效的 API Key")
    st.stop()

# --- 3. 初始化核心组件 ---
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
        if 'AI分析' not in df.columns: df['AI分析'] = ""
        return df, content_file.sha
    except:
        return pd.DataFrame(columns=['时间', '标题', '分类', '内容', '金句', 'AI分析']), None

def save_to_github(df, uid, sha):
    file_path = f"material_lib_{uid}.csv"
    csv_content = df.to_csv(index=False)
    repo = get_github_repo()
    if sha:
        repo.update_file(file_path, f"Update data for {uid}", csv_content, sha)
    else:
        repo.create_file(file_path, f"Init data for {uid}", csv_content)

# 实时加载数据
df, file_sha = load_data(user_uid)

# --- 4. 动态教材列表生成 (核心要求：基于 Data) ---
if not df.empty and '分类' in df.columns:
    existing_cats = set()
    for row in df['分类'].dropna():
        for cat in str(row).split(" / "):
            if cat.strip(): existing_cats.add(cat.strip())
    dynamic_books = sorted(list(existing_cats))
else:
    # 若 Data 为空，则展示默认基础教材
    dynamic_books = ["必修1", "必修2", "必修3", "必修4", "选修1", "选修2", "选修3"]

# --- 5. 侧边栏 ---
with st.sidebar:
    st.title("🛡️ 智库菜单")
    st.success(f"👤 ID: {user_uid}")
    page = st.radio("导航", ["📝 AI 素材加工", "📂 结构化看板"])
    st.divider()
    if st.button("🚪 退出登录"):
        st.session_state['authenticated'] = False
        st.rerun()

# --- 6. 功能区实现 ---

if page == "📝 AI 素材加工":
    st.header("📝 AI 教研素材加工")
    
    col_l, col_r = st.columns([2, 1])
    with col_l:
        raw_text = st.text_area("输入原始素材（时政、案例等）", height=400)
    
    with col_r:
        title = st.text_input("素材标题")
        mode = st.radio("分析模式", ["单本教材精读", "跨教材综合联动"])
        # 基于 Data 的动态多选
        selected_books = st.multiselect("涉及教材分类", options=dynamic_books)
        new_book = st.text_input("✨ 发现新教材名？在此输入添加")
        if new_book: selected_books.append(new_book)
        
        if st.button("🤖 启动 AI 分析", use_container_width=True):
            if raw_text and selected_books:
                with st.spinner("AI 正在深度解析..."):
                    prompt = f"分析模式：{mode}。涉及教材：{selected_books}。素材：{raw_text}。请给出教材契合点、教学建议及核心金句。"
                    response = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    st.session_state['ai_result'] = response.choices[0].message.content
            else:
                st.warning("内容或教材未填写。")

    if 'ai_result' in st.session_state:
        st.divider()
        st.subheader("💡 AI 教研分析结果")
        st.markdown(f'<div class="highlight-ai">{st.session_state["ai_result"]}</div>', unsafe_allow_html=True)
        
        final_gold = st.text_input("确认核心金句", value="从上方提取...")
        
        if st.button("💾 归档并同步云端"):
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
            st.success("🎉 数据已同步，动态教材列表已更新！")
            st.balloons()

elif page == "📂 结构化看板":
    st.header("📂 数字化教研室")
    
    if df.empty:
        st.info("目前云端尚无素材，请先录入。")
    else:
        # 表格可视化（功能回归）
        st.subheader("📊 素材汇总表")
        st.dataframe(df, use_container_width=True)
        
        # 导出 Excel 功能（新增）
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='教研存档')
        
        st.download_button(
            label="📥 点击下载 Excel 完整版报表",
            data=output.getvalue(),
            file_name=f"思政教研导出_{datetime.date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
        st.divider()
        
        # 深度高亮卡片预览
        st.subheader("🗂️ 素材精选预览 (重点已高亮)")
        for i, row in df.iloc[::-1].iterrows():
            with st.expander(f"📌 {row['分类']} | {row['标题']}"):
                # 金句高亮
                st.markdown(f'<div class="highlight-gold">🔑 核心金句：{row["金句"]}</div>', unsafe_allow_html=True)
                
                col_a, col_b = st.columns(2)
                with col_a: 
                    st.markdown("**【原始素材内容】**")
                    st.info(row['内容'])
                with col_b: 
                    st.markdown("**【AI 教研解析】**")
                    # AI 分析高亮
                    st.markdown(f'<div class="highlight-ai">{row["AI分析"]}</div>', unsafe_allow_html=True)

