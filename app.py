import streamlit as st
import pandas as pd
from openai import OpenAI
import os
from datetime import datetime

# 1. 页面配置与美化
st.set_page_config(page_title="政治名师智能素材库", page_icon="📚", layout="wide")
st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; font-size: 16px; font-weight: bold; }
    .main-box { border: 1px solid #ddd; padding: 20px; border-radius: 10px; background: #ffffff; }
    </style>
    """, unsafe_allow_html=True)

# 2. 数据库初始化 (my_data.csv)
DB_FILE = "my_politics_library.csv"
if not os.path.exists(DB_FILE):
    df_init = pd.DataFrame(columns=["日期", "素材标题", "对应模块", "知识点解析", "教学建议", "原文"])
    df_init.to_csv(DB_FILE, index=False, encoding='utf-8-sig')

# 3. 侧边栏：设置
with st.sidebar:
    st.title("🛡️ 系统设置")
    api_key = st.text_input("DeepSeek API Key", type="password")
    st.divider()
    st.info("💡 建议：每次分析完点击'确认入库'，素材将永久保存在云端。")

# 4. 主界面：功能分区
tab1, tab2 = st.tabs(["✨ 智能加工中心", "🗄️ 我的数字化素材库"])

# --- TAB 1: 智能分析与入库 ---
with tab1:
    st.header("🚀 时政素材深度加工")
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown('<div class="main-box">', unsafe_allow_html=True)
        news_title = st.text_input("素材标题（选填）", placeholder="如：新质生产力调研")
        news_content = st.text_area("粘贴新闻原文：", height=300)
        analyze_btn = st.button("🔥 开始 AI 深度解析")
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        if analyze_btn:
            if not api_key:
                st.error("请先在左侧配置 API Key")
            else:
                client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
                with st.spinner('政治教研 AI 正在翻阅教材并匹配真题逻辑...'):
                    # 强化 Prompt：要求 AI 给出结构化结果
                    prompt = f"你是一位思政课特级教师。请根据中国高中政治教材分析以下素材：\n{news_content}\n\n请严格按以下格式输出：\n【模块】(填必修1-4或选修名称)\n【考点】(具体知识点)\n【解析】(原理分析)\n【建议】(教学入课建议)"
                    
                    response = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    res = response.choices[0].message.content
                    st.session_state['temp_res'] = res
                    st.success("解析完成！")
                    st.markdown(res)
                    
        # 入库按钮
        if 'temp_res' in st.session_state:
            if st.button("📥 确认入库（保存至素材库）"):
                # 解析 AI 返回的内容进行结构化存储
                res_text = st.session_state['temp_res']
                # 简单切分逻辑（实际可根据【】符号更精准切分）
                new_data = {
                    "日期": datetime.now().strftime("%Y-%m-%d"),
                    "素材标题": news_title if news_title else "未命名素材",
                    "对应模块": res_text.split("【考点】")[0].replace("【模块】", "").strip(),
                    "知识点解析": res_text,
                    "教学建议": "详见解析列",
                    "原文": news_content[:100] + "..."
                }
                df_db = pd.read_csv(DB_FILE)
                df_db = pd.concat([df_db, pd.DataFrame([new_data])], ignore_index=True)
                df_db.to_csv(DB_FILE, index=False, encoding='utf-8-sig')
                st.balloons()
                st.success("入库成功！请在'我的素材库'查看。")

# --- TAB 2: 素材库管理 (功能1和2的体现) ---
with tab2:
    st.header("🗄️ 专属政治教学数据库")
    
    # 重新读取数据
    library_df = pd.read_csv(DB_FILE)
    
    # 功能1：筛选检索
    col_search1, col_search2 = st.columns([1, 2])
    with col_search1:
        module_filter = st.selectbox("按教材模块筛选", ["全部"] + list(library_df["对应模块"].unique()))
    with col_search2:
        keyword = st.text_input("关键词搜索（如：矛盾、生产力）")

    # 应用筛选
    display_df = library_df.copy()
    if module_filter != "全部":
        display_df = display_df[display_df["对应模块"] == module_filter]
    if keyword:
        display_df = display_df[display_df["知识点解析"].str.contains(keyword) | display_df["素材标题"].str.contains(keyword)]

    # 展示表格
    st.dataframe(display_df, use_container_width=True)

    # 功能2：导出教研资料
    st.divider()
    st.subheader("📄 教研资料导出")
    if not display_df.empty:
        csv = display_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(
            label="📥 导出当前筛选的素材 (Excel格式)",
            data=csv,
            file_name=f"政治素材导出_{datetime.now().strftime('%m%d')}.csv",
            mime='text/csv',
        )
    else:
        st.write("暂无素材，快去加工中心生产吧！")

