import streamlit as st
import pandas as pd
from openai import OpenAI
import os
import pdfplumber
from datetime import datetime
import hashlib

# 1. 页面基础配置
st.set_page_config(page_title="思政名师·专属教研空间", page_icon="🎓", layout="wide")

# 自定义样式：区分登录前后的氛围
st.markdown("""
    <style>
    .login-box { border: 2px solid #e5e7eb; padding: 40px; border-radius: 10px; text-align: center; max-width: 600px; margin: 0 auto; }
    .main-header { font-size: 24px; font-weight: bold; color: #1e40af; }
    </style>
    """, unsafe_allow_html=True)

# --- 核心工具函数 ---

def get_user_id(api_key):
    """将API Key转化为唯一的简短用户ID (取哈希前8位)，保护Key的隐私同时区分用户"""
    return hashlib.md5(api_key.encode()).hexdigest()[:8]

@st.cache_data(show_spinner=False)
def load_book_content(file_name):
    """读取公共教材库"""
    path = os.path.join("data", file_name)
    text = ""
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages[:50]:
                content = page.extract_text()
                if content: text += content + "\n"
        return text
    except: return ""

# --- 初始化 Session State (记忆用户登录状态) ---
if 'api_key' not in st.session_state:
    st.session_state['api_key'] = None
if 'user_id' not in st.session_state:
    st.session_state['user_id'] = None

# =================================================
# 🚪 第一阶段：登录界面 (如果没有登录)
# =================================================
if not st.session_state['api_key']:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.title("🎓 欢迎回到教研工作室")
        st.write("一把钥匙开一把锁：输入 Key 即刻进入您的专属空间")
        
        input_key = st.text_input("请输入 DeepSeek API Key", type="password")
        
        if st.button("🚀 进入工作室", use_container_width=True):
            if len(input_key) > 10:
                st.session_state['api_key'] = input_key
                st.session_state['user_id'] = get_user_id(input_key)
                st.rerun() # 刷新页面进入主系统
            else:
                st.error("请输入有效的 API Key")
        
        st.markdown('</div>', unsafe_allow_html=True)

# =================================================
# 🏠 第二阶段：主系统 (登录后显示)
# =================================================
else:
    # 获取当前用户的专属ID
    current_user = st.session_state['user_id']
    # 定义专属数据库文件名
    user_db_file = f"history_{current_user}.csv"
    
    # 侧边栏：用户信息与书架
    with st.sidebar:
        st.info(f"👤 当前用户ID: {current_user}")
        if st.button("🚪 退出登录"):
            st.session_state['api_key'] = None
            st.rerun()
            
        st.divider()
        st.subheader("📚 公共教材库")
        
        # 自动读取 data 文件夹
        data_dir = "data"
        if not os.path.exists(data_dir): os.makedirs(data_dir)
        books = [f for f in os.listdir(data_dir) if f.endswith('.pdf')]
        
        if books:
            selected_book = st.selectbox("选择教材", books)
        else:
            st.warning("公共书架为空")
            selected_book = None

    # 主区域
    st.title("🏛️ 智能教研工作台")
    
    tab1, tab2 = st.tabs(["✨ 备课", "📂 我的档案"])
    
    # 预加载教材
    context = ""
    if selected_book:
        with st.spinner("正在调阅教材..."):
            context = load_book_content(selected_book)

    with tab1:
        user_input = st.text_area("输入备课需求：", height=200)
        if st.button("生成方案", use_container_width=True):
            if not context:
                st.error("请先确保 data 文件夹有书")
            else:
                client = OpenAI(api_key=st.session_state['api_key'], base_url="https://api.deepseek.com")
                with st.spinner("AI 正在思考..."):
                    # 这里使用了简化的提示词，您可以根据需要加强
                    prompt = f"基于教材{selected_book}，回答：{user_input}\n教材内容：{context[:10000]}"
                    try:
                        resp = client.chat.completions.create(
                            model="deepseek-chat",
                            messages=[{"role": "user", "content": prompt}]
                        )
                        result = resp.choices[0].message.content
                        st.session_state['last_result'] = result
                    except Exception as e:
                        st.error(f"出错：{e}")

        # 显示结果并提供保存按钮
        if 'last_result' in st.session_state:
            st.markdown("---")
            st.markdown(st.session_state['last_result'])
            
            c_save, c_title = st.columns([1, 3])
            with c_title:
                save_title = st.text_input("存档标题", placeholder="如：第三课教学设计")
            with c_save:
                st.write("") # 占位
                st.write("") 
                if st.button("💾 存入我的档案"):
                    # 保存逻辑：只存入 user_db_file
                    new_row = {"日期": datetime.now().strftime("%Y-%m-%d"), "教材": selected_book, "标题": save_title, "内容": st.session_state['last_result']}
                    
                    df = pd.read_csv(user_db_file) if os.path.exists(user_db_file) else pd.DataFrame(columns=["日期","教材","标题","内容"])
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    df.to_csv(user_db_file, index=False)
                    st.success("已存入您的个人库！")

    with tab2:
        st.subheader("📂 我的专属教研历史")
        # 只读取当前用户的 CSV
        if os.path.exists(user_db_file):
            history_df = pd.read_csv(user_db_file)
            st.dataframe(history_df[["日期", "标题", "教材"]], use_container_width=True)
            
            # 提供下载功能（防止云端重置丢失数据）
            with open(user_db_file, "rb") as f:
                st.download_button(
                    label="📥 备份我的档案 (下载CSV)",
                    data=f,
                    file_name=f"archive_{current_user}.csv",
                    mime="text/csv"
                )
        else:
            st.info("您还没有存档记录，快去备课吧！")

