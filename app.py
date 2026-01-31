import streamlit as st
import pandas as pd
from openai import OpenAI
import os
import re

# ... 前面的页面配置保持不变 ...

# --- 增强功能：链接识别函数 ---
def is_url(string):
    regex = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    return re.findall(regex, string)

# --- TAB 1: 智能加工中心 (升级版) ---
with tab1:
    st.header("🚀 多模态素材加工")
    
    # 增加链接输入区
    input_type = st.radio("选择输入方式", ["直接粘贴文本", "输入网页/文章链接"], horizontal=True)
    
    if input_type == "输入网页/文章链接":
        source_url = st.text_input("🔗 粘贴公众号、新闻网页或视频链接：")
        st.caption("注：部分公众号文章有访问限制，若自动抓取失败，AI 将尝试通过标题进行联网检索分析。")
        news_input = source_url # 将链接传给 AI
    else:
        news_input = st.text_area("在此粘贴素材文字内容：", height=250)

    if st.button("🔥 智能识别并解析"):
        if not api_key:
            st.error("请先配置 API Key")
        else:
            client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
            
            with st.spinner('正在调取 DeepSeek-V3 联网解析能力...'):
                # 针对链接，我们优化 Prompt，让 AI 去“联想”和“检索”
                if input_type == "输入网页/文章链接":
                    system_prompt = "你是一位拥有联网检索能力的政治老师。请根据提供的链接内容（或根据链接特征进行检索），分析其对应的政治教材考点。"
                else:
                    system_prompt = "你是一位资深思政老师，请根据文本分析教材考点。"

                prompt = f"目标素材/链接：{news_input}\n\n要求：1.识别素材核心事件 2.关联必修1-4知识点 3.给出解析 4.设计一道考题设问。"
                
                # 调用 DeepSeek (确保 key 有联网权限)
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ]
                )
                # ... 后续显示与入库代码与之前一致 ...


