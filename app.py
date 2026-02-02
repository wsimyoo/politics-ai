import streamlit as st
import pandas as pd
from openai import OpenAI
import os
import pdfplumber
from datetime import datetime

# 1. 页面配置：设置网页标题和图标
st.set_page_config(page_title="思政名师·教材智能助理", page_icon="🏛️", layout="wide")

# 2. 注入自定义 CSS 样式，让界面更有教研高级感
st.markdown("""
    <style>
    .stApp { background-color: #fcfcfc; }
    .main-header { color: #1e3a8a; font-size: 2.2rem; font-weight: 700; margin-bottom: 1rem; }
    .book-info { background: #eff6ff; padding: 10px; border-radius: 5px; border-left: 5px solid #2563eb; }
    </style>
    """, unsafe_allow_html=True)

# 3. 核心功能：PDF 文字提取逻辑
@st.cache_data(show_spinner=False)
def get_pdf_content(file_name):
    """从 data 文件夹读取 PDF 内容并缓存"""
    path = os.path.join("data", file_name)
    text = ""
    try:
        with pdfplumber.open(path) as pdf:
            # 读取前 60 页，这通常涵盖了教材的大部分核心考点，同时也保证了 AI 处理的速度
            for page in pdf.pages[:60]:
                content = page.extract_text()
                if content:
                    text += content + "\n"
        return text
    except Exception as e:
        return f"读取出错: {e}"

# 4. 侧边栏：配置与教材库
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/library.png", width=60)
    st.title("教研控制中心")
    
    # 输入 API Key
    api_key = st.text_input("第一步：输入 DeepSeek API Key", type="password")
    
    st.divider()
    st.subheader("📚 云端教材库")
    
    # 自动识别 data 文件夹中的 PDF
    data_dir = "data"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    pdf_list = [f for f in os.listdir(data_dir) if f.endswith('.pdf')]
    
    if pdf_list:
        selected_book = st.selectbox("第二步：选择备课教材", pdf_list)
        st.success(f"已识别到 {len(pdf_list)} 份教材资料")
    else:
        st.error("⚠️ data文件夹中未发现PDF，请先上传教材")
        selected_book = None

    st.divider()
    user_id = st.text_input("教师识别码", value="名师工作室")
    db_file = f"db_{user_id}.csv"

# 5. 主界面布局
st.markdown('<div class="main-header">🚀 政治教学素材智能加工平台</div>', unsafe_allow_html=True)

tab1, tab2 = st.tabs(["✨ 智能加工", "📂 历史档案"])

# 预加载教材内容
book_context = ""
if selected_book:
    with st.spinner(f"正在调阅《{selected_book}》并提取考点..."):
        book_context = get_pdf_content(selected_book)

with tab1:
    col_input, col_output = st.columns([2, 3])
    
    with col_input:
        st.subheader("📍 输入素材或指令")
        user_input = st.text_area(
            "请粘贴时政新闻、材料题干或输入您的出题要求：", 
            height=350,
            placeholder="例如：请结合刚才上传的教材，为'新质生产力'这个时政热点设计三个课堂提问..."
        )
        analyze_btn = st.button("🧠 开始基于教材解析", use_container_width=True)

    with col_output:
        st.subheader("💡 AI 教研成果")
        if analyze_btn:
            if not api_key:
                st.error("请输入 API Key")
            elif not book_context:
                st.error("请先确保 data 文件夹中有 PDF 教材")
            else:
                client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
                with st.spinner("AI 正在深度研读教材并生成方案..."):
                    # 构造专业提示词
                    system_prompt = f"""
                    你是一位资深的思政课特级教师，擅长结合教材进行深度教研。
                    你当前研读的教材是：《{selected_book}》。
                    
                    教材核心参考内容：
                    {book_context[:20000]} 
                    
                    任务要求：
                    1. 必须结合提供的教材内容进行分析。
                    2. 【匹配考点】：指出对应的教材章节、框题和核心理论。
                    3. 【深度解析】：联系时政素材与教材理论，给出逻辑严密的分析。
                    4. 【教学应用】：提供适合课堂使用的设问、板书建议或原创题目。
                    """
                    
                    try:
                        response = client.chat.completions.create(
                            model="deepseek-chat",
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_input}
                            ],
                            temperature=0.7
                        )
                        st.session_state['current_res'] = response.choices[0].message.content
                    except Exception as e:
                        st.error(f"API调用失败: {e}")

        if 'current_res' in st.session_state:
            st.markdown(st.session_state['current_res'])
            if st.button("📥 保存本次教研成果"):
                new_data = {
                    "时间": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "教材": selected_book,
                    "成果": st.session_state['current_res']
                }
                df = pd.read_csv(db_file) if os.path.exists(db_file) else pd.DataFrame(columns=["时间","教材","成果"])
                df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
                df.to_csv(db_file, index=False, encoding='utf-8-sig')
                st.toast("存档成功！可在历史档案中查看。")

with tab2:
    if os.path.exists(db_file):
        history = pd.read_csv(db_file)
        for i, row in history.iloc[::-1].iterrows(): # 倒序显示最新记录
            with st.expander(f"📌 {row['时间']} | {row['教材']}"):
                st.write(row['成果'])
                if st.button(f"🗑️ 删除此条", key=f"del_{i}"):
                    history.drop(i).to_csv(db_file, index=False, encoding='utf-8-sig')
                    st.rerun()
    else:
        st.info("目前还没有存档的教研记录。")

