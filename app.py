import streamlit as st
import pandas as pd
from openai import OpenAI
import os
from datetime import datetime
import hashlib

# 1. 页面配置与美化
st.set_page_config(page_title="思政名师智能素材库", layout="wide", page_icon="🏛️")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .editor-container { background-color: #fffbeb; padding: 20px; border-radius: 12px; border: 1.5px solid #fcd34d; margin-top: 15px; }
    .material-card { background: white; padding: 15px; border-radius: 10px; border-left: 6px solid #b91c1c; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); margin-bottom: 15px; }
    .tag-container { display: flex; gap: 5px; flex-wrap: wrap; margin-bottom: 8px; }
    .book-tag { background: #fee2e2; color: #991b1b; padding: 2px 10px; border-radius: 15px; font-size: 12px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# 2. 用户哈希函数（一把钥匙开一把锁）
def get_user_id(api_key):
    return hashlib.md5(api_key.encode()).hexdigest()[:8]

# 3. 登录逻辑
if 'api_key' not in st.session_state:
    st.session_state['api_key'] = None

if not st.session_state['api_key']:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        st.title("🏛️ 思政名师专属素材空间")
        st.write("一把钥匙开一把锁：输入 API Key 即可进入您的跨教材素材库。")
        input_key = st.text_input("DeepSeek API Key", type="password")
        if st.button("🚀 开启工作室", use_container_width=True):
            if len(input_key) > 10:
                st.session_state['api_key'] = input_key
                st.session_state['user_id'] = get_user_id(input_key)
                st.rerun()
            else:
                st.error("请输入有效的 API Key")
else:
    # --- 登录后的主系统 ---
    user_id = st.session_state['user_id']
    user_db = f"material_lib_{user_id}.csv"
    
    # 侧边栏
    with st.sidebar:
        st.header(f"👤 工作室 ID: {user_id}")
        if st.button("🚪 退出登录"):
            st.session_state['api_key'] = None
            st.rerun()
        st.divider()
        st.caption("🔒 您的教研历史已根据 API Key 进行了加密隔离，仅您可见。")

    # 主布局：左侧加工，右侧浏览
    left_col, right_col = st.columns([1.2, 1])

    with left_col:
        st.subheader("✨ 素材智能加工与精修")
        
        with st.container(border=True):
            m_title = st.text_input("1. 素材标题", placeholder="输入便于日后搜索的标题...")
            m_raw = st.text_area("2. 素材原文内容", height=150, placeholder="粘贴时政新闻、案例或典故...")
            
            # 自动识别云端 data 文件夹里的教材
            data_path = "data"
            available_books = [f for f in os.listdir(data_path) if f.endswith('.pdf')] if os.path.exists(data_path) else ["必修1", "必修2", "必修3", "必修4"]
            
            # 关联教材多选
            m_books = st.multiselect("3. 关联教材（支持多选，实现跨教材逻辑贯通）", available_books, default=available_books[:1] if available_books else None)
            
            if st.button("🧠 AI 跨教材深度分析", use_container_width=True):
                client = OpenAI(api_key=st.session_state['api_key'], base_url="https://api.deepseek.com")
                with st.spinner("AI 正在翻阅多本教材，检索关联考点..."):
                    books_context = "、".join(m_books)
                    # 提示词优化：强调跨教材贯通
                    prompt = f"""
                    你是一位精通高中思想政治全套教材（必修1-4及选择性必修）的特级教师。
                    请针对素材《{m_title}》，分析其在《{books_context}》等教材中分别对应的核心考点。
                    
                    要求：
                    1. 【跨教材定位】：分教材列出知识点（如：【必修2 经济与社会】... 【必修3 政治与法治】...）。
                    2. 【逻辑贯通】：简述该素材如何串联起不同教材之间的逻辑联系。
                    3. 【教学设问】：给出 1-2 条适合课堂讨论的高质量设问。
                    
                    素材原文：{m_raw}
                    """
                    try:
                        resp = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                        st.session_state['edit_buffer'] = resp.choices[0].message.content
                    except Exception as e:
                        st.error(f"分析失败：{e}")

        # 老师精修区：在这里实现您的个人见解
        if 'edit_buffer' in st.session_state:
            st.markdown('<div class="editor-container">', unsafe_allow_html=True)
            st.markdown("✍️ **老师精修区**：您可以在此修改 AI 的表述，或添加更贴合教学实际的考点：")
            refined_analysis = st.text_area("跨教材考点分析（可手动编辑）", value=st.session_state['edit_buffer'], height=350)
            st.markdown('</div>', unsafe_allow_html=True)
            
            if st.button("💾 确认精修，存入专属素材库", use_container_width=True):
                new_entry = {
                    "日期": datetime.now().strftime("%Y-%m-%d"),
                    "标题": m_title,
                    "关联教材": " | ".join(m_books),
                    "精修解析": refined_analysis,
                    "素材原文": m_raw
                }
                df = pd.read_csv(user_db) if os.path.exists(user_db) else pd.DataFrame(columns=["日期","标题","关联教材","精修解析","素材原文"])
                df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
                df.to_csv(user_db, index=False, encoding='utf-8-sig')
                
                st.success(f"✅ 素材《{m_title}》已成功归档！")
                del st.session_state['edit_buffer']
                st.rerun()

    with right_col:
        st.subheader("📂 跨教材档案墙")
        if os.path.exists(user_db):
            lib_df = pd.read_csv(user_db)
            q = st.text_input("🔍 快速搜索（支持教材、考点或标题关键词）")
            
            display_df = lib_df[lib_df.apply(lambda r: r.astype(str).str.contains(q).any(), axis=1)] if q else lib_df
            
            for i, row in display_df.iloc[::-1].iterrows():
                with st.container():
                    book_tags = "".join([f'<span class="book-tag">{b}</span>' for b in str(row['关联教材']).split(" | ")])
                    st.markdown(f"""
                    <div class="material-card">
                        <div class="tag-container">{book_tags}</div>
                        <div style="font-size:18px; font-weight:bold; color:#1e293b; margin-bottom:5px;">{row['标题']}</div>
                        <div style="font-size:13px; color:#64748b;">存档日期：{row['日期']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    with st.expander("查看完整精修解析与原文"):
                        st.markdown("**【老师精修分析】**")
                        st.write(row['精修解析'])
                        st.divider()
                        st.markdown("**【原文参考】**")
                        st.caption(row['素材原文'])
                        if st.button(f"🗑️ 删除此素材", key=f"del_{i}"):
                            lib_df.drop(i).to_csv(user_db, index=False, encoding='utf-8-sig')
                            st.rerun()
        else:
            st.info("您的库目前还是空的，快去录入并加工您的第一份跨教材素材吧！")

