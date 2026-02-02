import streamlit as st
import pandas as pd
from openai import OpenAI
import os
from datetime import datetime
import hashlib
import re

# 1. 页面配置
st.set_page_config(page_title="思政名师智能素材库", layout="wide", page_icon="🏛️")

# 自定义 CSS：定义荧光笔和红色字体的视觉效果
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    /* 荧光笔：鲜亮的黄色背景 */
    mark { 
        background-color: #ffff00 !important; 
        color: #000 !important; 
        padding: 0 2px; 
        border-radius: 2px; 
        font-weight: bold;
    }
    /* 重点红：醒目的红色字体 */
    .important-red { 
        color: #e11d48 !important; 
        font-weight: bold; 
    }
    .stExpander { border: 1px solid #e2e8f0 !important; border-radius: 12px !important; background: white !important; }
    .book-tag { background: #fee2e2; color: #b91c1c; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; display: block; margin-bottom: 5px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# 2. 自动化工具函数
def get_user_id(api_key):
    return hashlib.md5(api_key.encode()).hexdigest()[:8]

def get_available_books():
    d_path = "data"
    if not os.path.exists(d_path): os.makedirs(d_path)
    files = [f for f in os.listdir(d_path) if not f.startswith('.')]
    files.sort()
    return [f.replace('.pdf', '').replace('.PDF', '').strip() for f in files]

def auto_highlight_fix(text):
    """【黑科技】如果AI写了**加粗**，自动将其替换为荧光笔<mark>标签"""
    # 将 **文本** 替换为 <mark>文本</mark>
    text = re.sub(r'\*\*(.*?)\*\*', r'<mark>\1</mark>', text)
    return text

def load_and_fix_db(file_path):
    standard_cols = ["日期", "标题", "涉及教材", "考点设问", "素材原文"]
    if not os.path.exists(file_path): return pd.DataFrame(columns=standard_cols)
    df = pd.read_csv(file_path)
    rename_map = {'精修解析': '考点设问', '核心知识点': '考点设问', '核心解析': '考点设问', '关联教材': '涉及教材', '原文': '素材原文'}
    df.rename(columns=rename_map, inplace=True)
    for col in standard_cols:
        if col not in df.columns: df[col] = "未记录"
    return df[standard_cols]

# 3. 登录与主逻辑
if 'api_key' not in st.session_state: st.session_state['api_key'] = None

if not st.session_state['api_key']:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        st.title("🏛️ 思政名师工作室")
        input_key = st.text_input("DeepSeek API Key", type="password")
        if st.button("🚀 开启工作室", use_container_width=True):
            if len(input_key) > 5:
                st.session_state['api_key'] = input_key
                st.session_state['uid'] = get_user_id(input_key)
                st.rerun()
else:
    uid = st.session_state['uid']
    db_file = f"material_lib_{uid}.csv"
    books = get_available_books()

    tab1, tab2 = st.tabs(["✨ 智能加工入库", "📂 全景结构化看板"])

    with tab1:
        left_c, right_c = st.columns([1.2, 1])
        with left_c:
            with st.container(border=True):
                m_title = st.text_input("1. 素材标题")
                m_raw = st.text_area("2. 素材原文内容", height=150)
                m_books = st.multiselect("3. 关联教材", options=books)
                
                if st.button("🧠 AI 深度高亮分析", use_container_width=True):
                    client = OpenAI(api_key=st.session_state['api_key'], base_url="https://api.deepseek.com")
                    with st.spinner("正在涂抹荧光笔..."):
                        # 极其严格的 Prompt 约束
                        prompt = f"""你是一位高中政治特级教师。分析素材《{m_title}》在《{'、'.join(m_books)}》中的核心考点。
                        
                        请严格遵守排版要求：
                        1. 严禁使用双星号（**）进行加粗。
                        2. 核心考点词汇（如：新质生产力、生产关系）必须包裹在 <mark> 和 </mark> 标签之间，实现荧光笔效果。
                        3. 重要的结论或核心金句必须包裹在 <span class='important-red'> 和 </span> 之间。
                        4. 保持段落清晰，给出1-2个设问。
                        
                        素材内容：{m_raw}"""
                        
                        resp = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                        # 关键：AI 生成后，立即运行一次自动修正，防范 AI 偷懒用加粗
                        final_text = auto_highlight_fix(resp.choices[0].message.content)
                        st.session_state['buffer'] = final_text

            if 'buffer' in st.session_state:
                st.markdown("✍️ **精修预览**（荧光笔：`<mark>文本</mark>`，红字：`<span class='important-red'>文本</span>`）")
                # 老师可以在这里手动微调
                final_res = st.text_area("最终解析结果", value=st.session_state['buffer'], height=300)
                if st.button("💾 归档至云端库", use_container_width=True):
                    df = load_and_fix_db(db_file)
                    new_row = {"日期": datetime.now().strftime("%Y-%m-%d"), "标题": m_title, "涉及教材": " | ".join(m_books), "考点设问": final_res, "素材原文": m_raw}
                    pd.concat([df, pd.DataFrame([new_row])], ignore_index=True).to_csv(db_file, index=False, encoding='utf-8-sig')
                    st.success("归档成功！")
                    del st.session_state['buffer']
                    st.rerun()

    with tab2:
        df = load_and_fix_db(db_file)
        if not df.empty:
            st.subheader("📝 教研快速索引表")
            st.dataframe(df[["日期", "标题", "涉及教材"]], use_container_width=True, hide_index=True)
            
            st.divider()
            st.subheader("📖 结构化分列看板（荧光笔视图）")
            for i, row in df.iloc[::-1].iterrows():
                with st.expander(f"📌 {row['涉及教材']} | {row['标题']}"):
                    col_left, col_right = st.columns([1, 2.5])
                    with col_left:
                        st.markdown("**📚 对应教材**")
                        for b in str(row['涉及教材']).split(" | "):
                            st.markdown(f"<span class='book-tag'>{b}</span>", unsafe_allow_html=True)
                    with col_right:
                        st.markdown("**💡 考点深度解析**")
                        # 最终渲染：将存入的 HTML 标签转为真实视觉效果
                        st.markdown(row['考点设问'], unsafe_allow_html=True)
                    
                    if st.button(f"🗑️ 删除此记录", key=f"del_{i}"):
                        df.drop(i).to_csv(db_file, index=False, encoding='utf-8-sig')
                        st.rerun()
