import streamlit as st
import pandas as pd
from openai import OpenAI
import os
from datetime import datetime
import hashlib

# 1. 页面配置与高级样式
st.set_page_config(page_title="思政名师智库-高亮版", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    /* 荧光笔与重点文字样式 */
    mark { background-color: #fef08a; padding: 0 4px; border-radius: 4px; font-weight: bold; color: #000; }
    .important-red { color: #dc2626; font-weight: bold; }
    /* 卡片美化 */
    .stExpander { border: 1px solid #e2e8f0 !important; background-color: white !important; border-radius: 12px !important; }
    .book-tag { background: #fee2e2; color: #b91c1c; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; display: block; margin-bottom: 5px; }
    </style>
    """, unsafe_allow_html=True)

# 2. 核心函数
def get_user_id(api_key):
    return hashlib.md5(api_key.encode()).hexdigest()[:8]

def get_available_books():
    d_path = "data"
    if not os.path.exists(d_path): os.makedirs(d_path)
    files = [f for f in os.listdir(d_path) if not f.startswith('.')]
    files.sort()
    return [f.replace('.pdf', '').replace('.PDF', '').strip() for f in files]

# 3. 登录检查
if 'api_key' not in st.session_state: st.session_state['api_key'] = None

if not st.session_state['api_key']:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        st.title("🏛️ 思政名师工作室")
        input_key = st.text_input("DeepSeek API Key", type="password")
        if st.button("🚀 开启工作室", use_container_width=True):
            if len(input_key) > 10:
                st.session_state['api_key'] = input_key
                st.session_state['user_id'] = get_user_id(input_key)
                st.rerun()
else:
    uid = st.session_state['user_id']
    db_file = f"material_lib_{uid}.csv"
    books = get_available_books()

    tab1, tab2 = st.tabs(["✨ 智能加工录入", "📂 结构化全景看板"])

    with tab1:
        left_c, right_c = st.columns([1.2, 1])
        with left_c:
            with st.container(border=True):
                m_title = st.text_input("素材标题")
                m_raw = st.text_area("素材原文", height=150)
                m_books = st.multiselect("关联教材", options=books)
                
                if st.button("🧠 AI 跨教材高亮分析", use_container_width=True):
                    client = OpenAI(api_key=st.session_state['api_key'], base_url="https://api.deepseek.com")
                    with st.spinner("正在捕捉重点并涂抹荧光笔..."):
                        # 提示词增强：要求 AI 使用 HTML 标签
                        prompt = f"""你是一位思政名师。分析素材《{m_title}》在《{'、'.join(m_books)}》中的考点。
                        重点：请将最核心的【考点词汇】用 <mark>标签包围 </mark>（荧光笔效果），
                        将【重要结论】用 <span class='important-red'>红色标签包围 </span>。
                        原文内容：{m_raw}"""
                        resp = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                        st.session_state['buffer'] = resp.choices[0].message.content

            if 'buffer' in st.session_state:
                st.markdown("✍️ **预览与精修**（可以直接手动加标签，如 &lt;mark&gt;重点&lt;/mark&gt;）")
                final_analysis = st.text_area("考点解析", value=st.session_state['buffer'], height=300)
                if st.button("💾 存入档案库", use_container_width=True):
                    new_row = {"日期": datetime.now().strftime("%Y-%m-%d"), "标题": m_title, "涉及教材": " | ".join(m_books), "考点设问": final_analysis, "素材原文": m_raw}
                    df = pd.read_csv(db_file) if os.path.exists(db_file) else pd.DataFrame(columns=["日期","标题","涉及教材","考点设问","素材原文"])
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    df.to_csv(db_file, index=False, encoding='utf-8-sig')
                    st.success("入库成功！")
                    del st.session_state['buffer']
                    st.rerun()

    with tab2:
        if os.path.exists(db_file):
            df = pd.read_csv(db_file).fillna("")
            st.markdown("### 📝 快速索引清单")
            st.dataframe(df[["日期", "标题", "涉及教材"]], use_container_width=True, hide_index=True)
            
            st.divider()
            st.markdown("### 📖 分列详情（带荧光笔高亮）")
            for i, row in df.iloc[::-1].iterrows():
                with st.expander(f"📌 {row['涉及教材']} | {row['标题']}"):
                    c1, c2 = st.columns([1, 2.5])
                    with c1:
                        st.markdown("**📚 涉及教材**")
                        for b in str(row['涉及教材']).split(" | "):
                            st.markdown(f"<span class='book-tag'>{b}</span>", unsafe_allow_html=True)
                    with c2:
                        st.markdown("**💡 核心考点解析**")
                        # 关键：使用 unsafe_allow_html=True 来渲染荧光笔效果
                        st.markdown(row['考点设问'], unsafe_allow_html=True)
                    
                    st.divider()
                    st.caption(f"素材原文：{row.get('素材原文', '')}")
                    if st.button(f"🗑️ 删除此条", key=f"del_{i}"):
                        df.drop(i).to_csv(db_file, index=False, encoding='utf-8-sig')
                        st.rerun()
        else:
            st.info("库内尚无素材。")
