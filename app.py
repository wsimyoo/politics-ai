import streamlit as st
import pandas as pd
from openai import OpenAI
import os

# 1. 页面配置：设置一个大气的标题和图标
st.set_page_config(page_title="政治名师 AI 工作站", page_icon="⚖️", layout="wide")

# 2. 深度美化：加入一些“高级感”的 CSS
st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stAlert { border-radius: 10px; }
    .stButton>button { 
        background-color: #003366; 
        color: white; 
        border-radius: 8px; 
        height: 3em; 
        transition: 0.3s;
    }
    .stButton>button:hover { background-color: #00509d; border: none; }
    h1 { color: #003366; font-family: 'Microsoft YaHei'; }
    </style>
    """, unsafe_allow_html=True)

# 3. 侧边栏：专门存放 DeepSeek 的配置
with st.sidebar:
    st.title("🤖 DeepSeek 引擎配置")
    st.info("建议使用 DeepSeek-V3 模型，分析更精准。")
    my_api_key = st.text_input("输入你的 DeepSeek API Key", type="password")
    # 固定的 DeepSeek 接口地址，省得老师手动输入
    base_url = "https://api.deepseek.com"
    
    st.markdown("---")
    st.write("📂 **数据状态**")
    if os.path.exists('textbook.csv'):
        st.success("教材库已就绪")
    else:
        st.error("缺失 textbook.csv")

# 4. 主界面布局
st.title("📖 政治教学素材智能分析平台")
st.caption("基于 DeepSeek 深度求索大模型 | 赋能思政课数字化备课")

col1, col2 = st.columns([1, 1], gap="medium")

with col1:
    st.subheader("📌 时政热点输入")
    news_content = st.text_area("请在此粘贴新闻原文或社论：", height=400, placeholder="例如：新质生产力的内涵与实践...")
    start_analyze = st.button("🔍 开始深度匹配")

with col2:
    st.subheader("🧠 教材关联解析")
    if start_analyze:
        if not my_api_key:
            st.warning("请先在左侧输入 API Key 哦！")
        else:
            try:
                # 建立 DeepSeek 连接
                client = OpenAI(api_key=my_api_key, base_url=base_url)
                
                with st.spinner('DeepSeek 正在解析考点，请稍候...'):
                    # 加载教材内容
                    df = pd.read_csv('textbook.csv')
                    textbook_context = df.to_string()
                    
                    # 构造给 AI 的指令（Prompt）
                    prompt = f"""你是一位政治特级教师。请根据以下教材知识点：
                    {textbook_context}
                    
                    对这则新闻进行深度解析：
                    {news_content}
                    
                    请按此格式输出：
                    1. 【核心考点】（匹配必修几、具体章节）
                    2. 【深度解析】（结合原理分析新闻）
                    3. 【金句积累】（适合学生背诵的政治术语）
                    4. 【模拟设问】（给出一个相关的考试设问方向）
                    """
                    
                    response = client.chat.completions.create(
                        model="deepseek-chat", # 这里固定为 deepseek-chat
                        messages=[{"role": "user", "content": prompt}],
                        stream=False
                    )
                    
                    result = response.choices[0].message.content
                    st.markdown(result)
                    st.balloons() # 成功后撒个花
            except Exception as e:
                st.error(f"连接失败：{str(e)}")

# 底部版权
st.markdown("---")
st.center = st.caption("©️ 2024 专属政治教研 App - 由 DeepSeek 提供动力")

