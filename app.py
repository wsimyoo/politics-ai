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
        st.write("请输入您的 API Key，系统将为您打开专属的跨学科素材库。")
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
        if st.button("🚪 退出当前空间"):
            st.session_state['api_key'] = None
            st.rerun()
        st.divider()
        st.caption("提示：所有存入的素材仅保存在您的专属 ID 下，其他用户无法查看。")

    # 主布局：左侧加工，右侧浏览
    left_col, right_col = st.columns([1.2, 1])

    with left_col:
        st.subheader("✨ 素材智能加工与精修")
        
        with st.container(border=True):
            m_title = st.text_input("1. 素材标题", placeholder="如：贵州'村超'火爆出圈")
            m_raw = st.text_area("2. 素材原文内容", height=150, placeholder="粘贴新闻报道或案例原文...")
            
            # 自动识别云端 data 文件夹里的教材
            data_path = "data"
            available_books = [f for f in os.listdir(data_path) if f.endswith('.pdf')] if os.path.exists(data_path) else ["必修1", "必修2", "必修3", "必修4"]
            
            # 核心：支持多选，解决“一例多用”
            m_books = st.multiselect("3. 关联教材（支持多选，实现跨书关联）", available_books, default=available_books[:1] if available_books else None)
            
            if st.button("🧠 AI 跨学科深度分析", use_container_width=True):
                client = OpenAI(api_key=st.session_state['api_key'], base_url="https://api.deepseek.com")
                with st.spinner("AI 正在联动多本教材进行分析..."):
                    books_context = "、".join(m_books)
                    prompt = f"""
                    你是一位精通高中思想政治全套教材的特级教师。
                    请针对素材《{m_title}》，分析其在《{books_context}》中分别对应的核心考点。
                    
                    要求：
                    1. 必须分教材列出知识点（如：【必修2 经济】、 【必修4 哲学】）。
                    2. 给出 1-2 条具体的课堂设问建议。
                    3. 逻辑清晰，语言专业。
                    
                    素材原文：{m_raw}
                    """
                    try:
                        resp = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                        st.session_state['edit_buffer'] = resp.choices[0].message.content
                    except Exception as e:
                        st.error(f"分析失败，请检查网络或Key：{e}")

        # 老师精修区：AI 生成的内容可以被随意修改
        if 'edit_buffer' in st.session_state:
            st.markdown('<div class="editor-container">', unsafe_allow_html=True)
            st.markdown("✍️ **老师精修建议**：您可以在下方补充 AI 遗漏的本地考点或教学灵感：")
            refined_analysis = st.text_area("考点分析与教学设计（可编辑）", value=st.session_state['edit_buffer'], height=350)
            st.markdown('</div>', unsafe_allow_html=True)
            
            if st.button("💾 确认精修无误，存入我的素材库", use_container_width=True):
                new_entry = {
                    "日期": datetime.now().strftime("%Y-%m-%d"),
                    "标题": m_title,
                    "关联教材": " | ".join(m_books),
                    "解析结果": refined_analysis,
                    "素材原文": m_raw
                }
                # 持久化存储
                df = pd.read_csv(user_db) if os.path.exists(user_db) else pd.DataFrame(columns=["日期","标题","关联教材","解析结果","素材原文"])
                df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
                df.to_csv(user_db, index=False, encoding='utf-8-sig')
                
                st.success(f"✅ 素材《{m_title}》已成功存入您的专属档案！")
                del st.session_state['edit_buffer']
                st.rerun()

    with right_col:
        st.subheader("📂 个人档案库检索")
        if os.path.exists(user_db):
            lib_df = pd.read_csv(user_db)
            q = st.text_input("🔍 搜索（支持关键词、教材名搜索）")
            
            display_df = lib_df[lib_df.apply(lambda r: r.astype(str).str.contains(q).any(), axis=1)] if q else lib_df
            
            # 以瀑布流卡片形式展示
            for i, row in display_df.iloc[::-1].iterrows():
                with st.container():
                    # 视觉卡片设计
                    book_tags = "".join([f'<span class="book-tag">{b}</span>' for b in str(row['关联教材']).split(" | ")])
                    st.markdown(f"""
                    <div class="material-card">
                        <div class="tag-container">{book_tags}</div>
                        <div style="font-size:18px; font-weight:bold; color:#1e293b; margin-bottom:5px;">{row['标题']}</div>
                        <div style="font-size:13px; color:#64748b;">存档日期：{row['日期']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    with st.expander("查看详情"):
                        st.markdown("**【精修考点分析】**")
                        st.write(row['解析结果'])
                        st.divider()
                        st.markdown("**【素材原文】**")
                        st.caption(row['素材原文'])
                        if st.button(f"🗑️ 永久删除", key=f"del_{i}"):
                            lib_df.drop(i).to_csv(user_db, index=False, encoding='utf-8-sig')
                            st.rerun()
        else:
            st.info("您的库目前还是空的，快去加工第一条素材吧！")

