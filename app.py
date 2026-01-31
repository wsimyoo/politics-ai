import streamlit as st
import pandas as pd
from openai import OpenAI
import os
from datetime import datetime

# 1. 页面基本配置
st.set_page_config(page_title="政治名师智能素材库", page_icon="📚", layout="wide")

# 2. 数据库初始化：确保保存功能正常
DB_FILE = "my_politics_library.csv"
if not os.path.exists(DB_FILE):
    df_init = pd.DataFrame(columns=["日期", "素材标题", "对应模块", "解析内容", "原文/链接"])
    df_init.to_csv(DB_FILE, index=False, encoding='utf-8-sig')

# 3. 侧边栏：配置 DeepSeek
with st.sidebar:
    st.title("🛡️ 配置中心")
    api_key = st.text_input("DeepSeek API Key", type="password")
    st.divider()
    st.info("💡 提示：在此输入 Key 后即可开始分析。")

# 4. 主界面：定义标签页（修复 NameError 的关键）
tab1, tab2 = st.tabs(["✨ 智能加工中心", "🗄️ 我的数字化素材库"])

# --- TAB 1: 智能分析中心 ---
with tab1:
    st.header("🚀 素材加工")
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📍 输入素材")
        input_type = st.radio("选择方式", ["文字内容", "文章链接"], horizontal=True)
        news_title = st.text_input("给素材起个名")
        
        if input_type == "文章链接":
            news_input = st.text_input("🔗 粘贴公众号或新闻链接：")
        else:
            news_input = st.text_area("在此粘贴文字：", height=200)
            
        analyze_btn = st.button("🔥 开始 AI 解析")

    with col2:
        st.subheader("🧠 解析结果")
        if analyze_btn:
            if not api_key:
                st.error("请先在左侧输入 API Key")
            else:
                client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
                with st.spinner('AI 正在读取并匹配教材...'):
                    # 提示词优化：让 AI 即使面对链接也能尝试检索
                    prompt = f"你是一位思政名师。请分析该素材（如果是链接请基于标题和已知信息检索）：\n{news_input}\n\n格式要求：\n【模块】：必修X\n【考点】：具体知识点\n【解析】：深度分析\n【金句】：适合背诵的词句"
                    
                    try:
                        response = client.chat.completions.create(
                            model="deepseek-chat",
                            messages=[{"role": "user", "content": prompt}]
                        )
                        res = response.choices[0].message.content
                        st.session_state['temp_res'] = res # 临时存入 session 供保存使用
                        st.markdown(res)
                    except Exception as e:
                        st.error(f"分析失败，请检查 Key 或网络：{e}")
        
        # 存入数据库功能
        if 'temp_res' in st.session_state:
            if st.button("📥 确认入库（永久保存）"):
                current_res = st.session_state['temp_res']
                # 提取模块名称的简单逻辑
                module_name = "未分类"
                if "【模块】" in current_res:
                    module_name = current_res.split("【模块】")[1].split("\n")[0].strip("：: ")
                
                new_data = {
                    "日期": datetime.now().strftime("%Y-%m-%d"),
                    "素材标题": news_title if news_title else "未命名素材",
                    "对应模块": module_name,
                    "解析内容": current_res,
                    "原文/链接": news_input
                }
                # 写入 CSV
                lib_df = pd.read_csv(DB_FILE)
                lib_df = pd.concat([lib_df, pd.DataFrame([new_data])], ignore_index=True)
                lib_df.to_csv(DB_FILE, index=False, encoding='utf-8-sig')
                st.success("已存入'我的素材库'！")

# --- TAB 2:


