import streamlit as st
import pandas as pd
from openai import OpenAI
import os
from datetime import datetime
import hashlib
import re

# 1. 页面配置
st.set_page_config(page_title="思政名师智能素材库", layout="wide", page_icon="🏛️")

# 自定义 CSS：渲染荧光笔、红字、卡片
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    mark { background-color: #ffff00 !important; color: #000 !important; padding: 0 3px; border-radius: 3px; font-weight: bold; }
    .important-red { color: #e11d48 !important; font-weight: bold; }
    .stExpander { border: 1px solid #e2e8f0 !important; border-radius: 12px !important; background: white !important; margin-bottom: 10px !important; }
    .book-tag { 
        background: #fee2e2; color: #b91c1c; padding: 2px 8px; border-radius: 4px; 
        font-size: 12px; font-weight: bold; display: block; margin-bottom: 5px; 
        text-align: center; border: 1px solid #fecaca;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. 后端逻辑
def get_user_id(api_key):
    return hashlib.md5(api_key.encode()).hexdigest()[:8]

def get_available_books():
    d_path = "data"
    if not os.path.exists(d_path): os.makedirs(d_path)
    files = [f for f in os.listdir(d_path) if not f.startswith('.')]
    files.sort()
    return [f.replace('.pdf', '').replace('.PDF', '').replace('高中政治', '').strip() for f in files]

def auto_highlight_fix(text):
    return re.sub(r'\*\*(.*?)\*\*', r'<mark>\1</mark>', text)

def load_and_fix_db(file_path):
    standard_cols = ["日期", "标题", "涉及教材", "考点设问", "素材原文"]
    if not os.path.exists(file_path): return pd.DataFrame(columns=standard_cols)
    try:
        df = pd.read_csv(file_path)
        rename_map = {'精修解析': '考点设问', '核心知识点': '考点设问', '核心解析': '考点设问', '关联教材': '涉及教材', '原文内容': '素材原文'}
        df.rename(columns=rename_map, inplace=True)
        for col in standard_cols:
            if col not in df.columns: df[col] = "未记录"
        return df[standard_cols]
    except:
        return pd.DataFrame(columns=standard_cols)

# 3. 身份校验与导出
if 'api_key' not in st.session_state: st.session_state['api_key'] = None

if not st.session_state['api_key']:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        st.title("🏛️ 思政名师工作室")
        input_key = st.text_input("DeepSeek API Key", type="password")
        if st.button("🚀 进入工作室", use_container_width=True):
            if len(input_key) > 10:
                st.session_state['api_key'] = input_key
                st.session_state['uid'] = get_user_id(input_key)
                st.rerun()
else:
    uid = st.session_state['uid']
    db_file = f"material_lib_{uid}.csv"
    book_options = get_available_books()

    with st.sidebar:
        st.header(f"👤 老师 ID: {uid}")
        if st.button("🚪 退出登录"):
            st.session_state['api_key'] = None
            st.rerun()
        st.divider()
        st.subheader("📥 教研导出")
        df_all = load_and_fix_db(db_file)
        if not df_all.empty:
            csv = df_all.to_csv(index=False).encode('utf-8-sig')
            st.download_button("导出 CSV 清单", data=csv, file_name=f"思政素材_{datetime.now().strftime('%m%d')}.csv", use_container_width=True)

    tab1, tab2 = st.tabs(["✨ 素材智能加工", "📂 结构化全景看板"])

    # TAB 1: 核心【双重解析】逻辑
    with tab1:
        left_c, right_c = st.columns([1.2, 1])
        with left_c:
            with st.container(border=True):
                m_title = st.text_input("素材标题")
                m_raw = st.text_area("素材原文", height=150)
                m_books = st.multiselect("关联教材（选择多本以开启联动分析）", options=book_options)
                
                if st.button("🧠 开启多维高亮分析", use_container_width=True):
                    if not m_title or not m_books:
                        st.warning("请补全标题并选择教材")
                    else:
                        client = OpenAI(api_key=st.session_state['api_key'], base_url="https://api.deepseek.com")
                        with st.spinner("正在进行多教材联觉分析..."):
                            # 终极提示词：要求【各教材独立分析】+【跨教材综合联动】
                            prompt = f"""你是一位高中政治名师。请针对素材《{m_title}》在以下教材中进行深度教研分析：{', '.join(m_books)}。
                            
                            请按以下【三段式结构】输出，禁止使用加粗，必须使用 <mark>高亮</mark>：
                            
                            ### 1️⃣ 各教材分册解析
                            针对所选的每一本教材，分别列出其对应的核心考点。
                            
                            ### 2️⃣ 跨教材联动分析
                            分析这些不同教材的知识点如何通过该素材产生内在逻辑关联（例如必修2的案例如何支撑必修4的哲学结论）。
                            
                            ### 3️⃣ 综合教学设问
                            给出 1-2 个高质量的综合性设问。
                            
                            排版规范：核心词用 <mark> 标签，关键结论用 <span class='important-red'> 标签。
                            素材原文：{m_raw}"""
                            
                            resp = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                            st.session_state['buffer'] = auto_highlight_fix(resp.choices[0].message.content)

            if 'buffer' in st.session_state:
                st.markdown("✍️ **预览与精修**")
                final_res = st.text_area("考点解析", value=st.session_state['buffer'], height=350)
                if st.button("💾 确认入库", use_container_width=True):
                    df = load_and_fix_db(db_file)
                    new_row = {"日期": datetime.now().strftime("%Y-%m-%d"), "标题": m_title, "涉及教材": " | ".join(m_books), "考点设问": final_res, "素材原文": m_raw}
                    pd.concat([df, pd.DataFrame([new_row])], ignore_index=True).to_csv(db_file, index=False, encoding='utf-8-sig')
                    st.success("入库成功！")
                    del st.session_state['buffer']
                    st.rerun()

    # TAB 2: 结构化分列看板
    with tab2:
        df = load_and_fix_db(db_file)
        if not df.empty:
            st.subheader("📝 快速索引清单")
            st.dataframe(df[["日期", "标题", "涉及教材"]], use_container_width=True, hide_index=True)
            
            st.divider()
            st.subheader("📖 结构化看板 (高亮分列视图)")
            q = st.text_input("🔍 搜索素材关键词...")
            show_df = df[df.apply(lambda r: r.astype(str).str.contains(q).any(), axis=1)] if q else df
            
            for i, row in show_df.iloc[::-1].iterrows():
                with st.expander(f"📌 {row['涉及教材']} | {row['标题']}"):
                    col_l, col_r = st.columns([1, 2.5])
                    with col_l:
                        st.markdown("**📚 涉及教材**")
                        for b in str(row['涉及教材']).split(" | "):
                            st.markdown(f"<span class='book-tag'>{b}</span>", unsafe_allow_html=True)
                    with col_r:
                        st.markdown("**💡 深度教研解析（含跨教材联动）**")
                        st.markdown(row['考点设问'], unsafe_allow_html=True)
                    
                    st.divider()
                    st.caption(f"素材原文参考：{row.get('素材原文', '')}")
                    if st.button(f"🗑️ 删除此记录", key=f"del_{i}"):
                        df.drop(i).to_csv(db_file, index=False, encoding='utf-8-sig')
                        st.rerun()

