import streamlit as st
import pandas as pd
from openai import OpenAI
import os

# 1. 网页标题与样式
st.set_page_config(page_title="政治名师AI素材库", layout="wide")
st.title("📖 政治教学素材智能匹配系统")

# 2. 侧边栏：配置与导航
with st.sidebar:
    st.header("⚙️ 系统配置")
    api_key = st.text_input("填入 API Key (如DeepSeek/智谱)", type="password")
    menu = st.radio("功能导航", ["智能分析", "我的素材库"])

# 3. 初始化素材库文件（如果没有则创建一个）
lib_file = "my_library.csv"
if not os.path.exists(lib_file):
    pd.DataFrame(columns=["日期", "原文", "考点解析"]).to_csv(lib_file, index=False)

# 4. 加载本地教材 (textbook.csv)
@st.cache_data
def load_textbook():
    if os.path.exists('textbook.csv'):
        return pd.read_csv('textbook.csv')
    return None

df_textbook = load_textbook()

# --- 功能一：智能分析 ---
if menu == "智能分析":
    st.subheader("🚀 粘贴时政新闻，自动匹配教材")
    news_input = st.text_area("在此粘贴新闻内容：", height=200, placeholder="例如：神舟十八号成功发射...")
    
    if st.button("开始智能分析"):
        if not api_key:
            st.error("请在左侧填入 API Key 后再试")
        elif df_textbook is None:
            st.error("找不到教材文件 textbook.csv，请检查 GitHub 仓库")
        else:
            client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com") # 默认DeepSeek
            with st.spinner('正在分析中...'):
                prompt = f"你是一位资深政治老师。根据教材库内容：\n{df_textbook.to_string()}\n\n分析这则新闻：\n{news_input}\n\n要求：1.列出匹配的必修模块 2.列出对应的知识点 3.给出教学设计建议。"
                
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": prompt}]
                )
                result = response.choices[0].message.content
                st.session_state['last_result'] = result
                st.markdown(result)

    # 保存按钮
    if 'last_result' in st.session_state:
        if st.button("📥 存入我的素材库"):
            new_row = pd.DataFrame([[pd.Timestamp.now().strftime('%Y-%m-%d'), news_input[:30]+"...", st.session_state['last_result']]], 
                                  columns=["日期", "原文", "考点解析"])
            new_row.to_csv(lib_file, mode='a', index=False, header=False)
            st.success("已成功保存到素材库！")

# --- 功能二：我的素材库 ---
else:
    st.subheader("📚 历次保存的素材")
    try:
        library_df = pd.read_csv(lib_file)
        if not library_df.empty:
            search = st.text_input("🔍 搜索关键词（知识点或日期）：")
            # 简单的模糊搜索
            filtered_df = library_df[library_df.apply(lambda row: search.lower() in str(row).lower(), axis=1)]
            st.dataframe(filtered_df, use_container_width=True)
            
            # 提供下载功能，方便老师把素材导出来放进PPT
            csv_data = library_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📂 导出素材库到 Excel (CSV格式)", data=csv_data, file_name="my_politics_library.csv")
        else:
            st.info("素材库还是空的，快去分析一些新闻并保存吧！")
    except:
        st.write("素材库文件读取失败。")
