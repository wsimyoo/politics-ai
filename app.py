import streamlit as st
import pandas as pd
from openai import OpenAI
import requests
import os
from datetime import datetime

# 1. 页面高级配置
st.set_page_config(
    page_title="思政智库 - AI教研集成系统",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. 注入精装修 CSS (深蓝教研风)
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .main-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    .highlight-text { color: #1e40af; font-weight: 700; }
    .stButton>button { width: 100%; border-radius: 8px; background-color: #1e40af; color: white; border: none; }
    .stButton>button:hover { background-color: #1d4ed8; color: white; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #f1f5f9;
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. 侧边栏：配置与教材选择
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/library.png", width=60)
    st.title("教研配置面板")
    
    with st.expander("🔑 接口授权", expanded=True):
        ds_api_key = st.text_input("DeepSeek Key", type="password")
        jina_key = st.text_input("Jina Reader Key", type="password")
        
    with st.expander("📖 教材版本控制", expanded=True):
        book_select = st.multiselect(
            "关联教材范围",
            ["必修1 中国特色社会主义", "必修2 经济与社会", "必修3 政治与法治", "必修4 哲学与文化", "选修1-3"],
            default=["必修2 经济与社会"]
        )
    
    st.divider()
    user_tag = st.text_input("👤 专属识别码", placeholder="输入名字以隔离素材库")
    DB_FILE = f"db_{user_tag}.csv" if user_tag else "db_default.csv"

# 4. 核心逻辑函数
def fetch_content(url, key):
    if not key: return "ERR_NO_KEY"
    try:
        res = requests.get(f"https://r.jina.ai/{url}", headers={"Authorization": f"Bearer {key}"}, timeout=10)
        return res.text
    except: return "ERR_FETCH"

# 5. 主页面布局
st.title("🏛️ 思政素材智能匹配与数据库系统")
st.caption(f"当前用户：{user_tag if user_tag else '公共访客'} | 教材底座：{', '.join(book_select)}")

tab_main, tab_lib, tab_setting = st.tabs(["✨ 智能加工", "🗃️ 个人素材库", "⚙️ 系统维护"])

# --- TAB 1: 智能加工 ---
with tab_main:
    col_in, col_out = st.columns([2, 3], gap="large")
    
    with col_in:
        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        st.subheader("📍 素材采集")
        input_mode = st.radio("来源类型", ["文字粘贴", "网页/公众号链接"], horizontal=True)
        
        raw_input = ""
        if input_mode == "网页/公众号链接":
            target_url = st.text_input("输入网址")
            if st.button("🔌 抓取原文内容"):
                fetched = fetch_content(target_url, jina_key)
                if "ERR" in fetched: st.error("抓取失败，请检查Jina Key")
                else: 
                    st.session_state['temp_content'] = fetched[:5000]
                    st.success("内容已成功同步")
            raw_input = st.session_state.get('temp_content', "")
        else:
            raw_input = st.text_area("粘贴素材原文", height=300)
            
        analyze_title = st.text_input("素材命名", placeholder="如果不填，将由AI生成标题")
        process_btn = st.button("🧠 深度匹配教材考点")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_out:
        if process_btn:
            if not ds_api_key: st.warning("请在左侧配置 DeepSeek Key")
            else:
                client = OpenAI(api_key=ds_api_key, base_url="https://api.deepseek.com")
                with st.spinner("正在根据必修教材逻辑进行结构化解析..."):
                    prompt = f"""你是一位思政课专家。请针对选定教材：{book_select}，解析以下素材：
                    {raw_input}
                    输出格式必须包含：
                    ### 【核心考点】
                    ### 【教材解析】
                    ### 【金句积累】
                    ### 【模拟设问】
                    """
                    response = client.chat.completions.create(model="deepseek-chat", messages=[{"role": "user","content": prompt}])
                    st.session_state['analysis_res'] = response.choices[0].message.content
        
        if 'analysis_res' in st.session_state:
            st.markdown('<div class="main-card">', unsafe_allow_html=True)
            st.markdown(st.session_state['analysis_res'])
            if st.button("💾 确认入库并生成卡片"):
                # 保存逻辑
                new_row = {
                    "日期": datetime.now().strftime("%Y-%m-%d"),
                    "标题": analyze_title if analyze_title else "未命名",
                    "教材": str(book_select),
                    "解析": st.session_state['analysis_res']
                }
                # 这里检查文件并保存
                df = pd.read_csv(DB_FILE) if os.path.exists(DB_FILE) else pd.DataFrame(columns=["日期","标题","教材","解析"])
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                df.to_csv(DB_FILE, index=False, encoding='utf-8-sig')
                st.toast("素材已永久存入个人库！", icon='✅')
            st.markdown('</div>', unsafe_allow_html=True)

# --- TAB 2: 素材库 ---
with tab_lib:
    if os.path.exists(DB_FILE):
        full_df = pd.read_csv(DB_FILE)
        search_kw = st.text_input("🔍 在库中搜索知识点或素材标题")
        if search_kw:
            full_df = full_df[full_df['解析'].str.contains(search_kw) | full_df['标题'].str.contains(search_kw)]
        
        for idx, row in full_df.iterrows():
            with st.expander(f"📅 {row['日期']} | {row['标题']}"):
                st.info(f"关联版本：{row['教材']}")
                st.markdown(row['解析'])
                if st.button(f"🗑️ 删除此素材", key=f"del_{idx}"):
                    # 删除逻辑...
                    pass
    else:
        st.write("素材库空空如也，快去加工中心吧！")


