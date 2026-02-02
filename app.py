import streamlit as st
import pandas as pd
from openai import OpenAI
import os
from datetime import datetime
import hashlib

# 1. 页面配置
st.set_page_config(page_title="思政名师智库", layout="wide", page_icon="🏛️")

# 自定义样式：让表格和卡片层次分明
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .material-card { background: white; padding: 18px; border-radius: 12px; border-top: 5px solid #b91c1c; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .stDataFrame { border-radius: 10px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

def get_user_id(api_key):
    return hashlib.md5(api_key.encode()).hexdigest()[:8]

# --- 登录逻辑 ---
if 'api_key' not in st.session_state:
    st.session_state['api_key'] = None

if not st.session_state['api_key']:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        st.title("🏛️ 思政名师专属素材空间")
        input_key = st.text_input("DeepSeek API Key", type="password")
        if st.button("🚀 开启工作室", use_container_width=True):
            if len(input_key) > 10:
                st.session_state['api_key'] = input_key
                st.session_state['user_id'] = get_user_id(input_key)
                st.rerun()
else:
    user_id = st.session_state['user_id']
    user_db = f"material_lib_{user_id}.csv"
    
    with st.sidebar:
        st.header(f"👤 工作 ID: {user_id}")
        if st.button("🚪 退出登录"):
            st.session_state['api_key'] = None
            st.rerun()
        st.divider()
        if os.path.exists(user_db):
            df_export = pd.read_csv(user_db)
            csv = df_export.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 导出教研清单 (Excel/CSV)", data=csv, file_name=f"思政素材清单_{user_id}.csv", use_container_width=True)

    tab1, tab2 = st.tabs(["✨ 素材智能加工", "📂 全景教研看板"])

    # --- TAB 1: 录入（保持逻辑不变） ---
    with tab1:
        left_c, right_c = st.columns([1.2, 1])
        with left_c:
            with st.container(border=True):
                m_title = st.text_input("素材标题")
                m_raw = st.text_area("素材原文", height=150)
                data_path = "data"
                raw_books = [f for f in os.listdir(data_path) if f.endswith('.pdf')] if os.path.exists(data_path) else ["必修1", "必修2", "必修3", "必修4"]
                available_books = [f.replace('.pdf', '').replace('高中政治', '') for f in raw_books]
                m_books = st.multiselect("关联教材", available_books, default=available_books[:1] if available_books else None)
                
                if st.button("🧠 AI 跨教材深度分析", use_container_width=True):
                    client = OpenAI(api_key=st.session_state['api_key'], base_url="https://api.deepseek.com")
                    with st.spinner("教研分析中..."):
                        prompt = f"分析《{m_title}》在《{'、'.join(m_books)}》中的核心知识点并给出设问。要求简洁专业。\n原文：{m_raw}"
                        resp = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                        st.session_state['buffer'] = resp.choices[0].message.content

            if 'buffer' in st.session_state:
                st.markdown('<div class="editor-container" style="background:#fffbeb; padding:15px; border-radius:10px; border:1px solid #fcd34d;">', unsafe_allow_html=True)
                refined_analysis = st.text_area("✍️ 老师精修（考点、建议）", value=st.session_state['buffer'], height=300)
                if st.button("💾 归档素材库", use_container_width=True):
                    # 提取前100字作为知识点预览存入
                    new_data = {"日期": datetime.now().strftime("%Y-%m-%d"), "标题": m_title, "涉及教材": " | ".join(m_books), "核心解析": refined_analysis, "原文内容": m_raw}
                    df = pd.read_csv(user_db) if os.path.exists(user_db) else pd.DataFrame(columns=["日期","标题","涉及教材","核心解析","原文内容"])
                    df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
                    df.to_csv(user_db, index=False, encoding='utf-8-sig')
                    st.success("存档成功！")
                    del st.session_state['buffer']
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
        
        with right_c:
            st.info("💡 操作提示：\n1. 标题起得好，日后搜索没烦恼。\n2. AI 分析完成后，别忘了在编辑区加入您独特的教学视角。")

    # --- TAB 2: 完善后的全景教研看板 ---
    with tab2:
        if os.path.exists(user_db):
            full_df = pd.read_csv(user_db).fillna("")
            
            # 兼容性处理
            if '核心解析' not in full_df.columns and '核心知识点' in full_df.columns:
                full_df.rename(columns={'核心知识点': '核心解析'}, inplace=True)
            elif '核心解析' not in full_df.columns and '精修解析' in full_df.columns:
                full_df.rename(columns={'精修解析': '核心解析'}, inplace=True)

            st.subheader("📖 结构化教研清单")
            st.caption("在表格任意处点击或搜索，实现高效检索。")

            # 构建表格视图数据
            # 这里的 .apply 用于生成简洁的“知识点一览”，剔除换行，保持整齐
            view_df = full_df.copy()
            view_df['考点概要'] = view_df['核心解析'].apply(lambda x: str(x).replace('\n', ' ')[:100] + '...')
            
            # 使用更强大的 Dataframe 展示
            st.dataframe(
                view_df[["日期", "标题", "涉及教材", "考点概要"]],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "日期": st.column_config.Column("入库日期", width="small"),
                    "标题": st.column_config.Column("素材名称", width="medium"),
                    "涉及教材": st.column_config.Column("涉及书目", width="medium"),
                    "考点概要": st.column_config.Column("核心知识点预览", width="large")
                }
            )

            st.divider()

            # 下方保留完整的卡片展示
            st.subheader("🗂️ 详细教研档案卡片")
            q = st.text_input("🔍 搜索过滤卡片...", placeholder="输入教材或关键词...")
            
            filtered_df = full_df[full_df.apply(lambda r: r.astype(str).str.contains(q).any(), axis=1)] if q else full_df
            
            for i, row in filtered_df.iloc[::-1].iterrows():
                with st.container():
                    st.markdown(f"""
                    <div class="material-card">
                        <span style="font-size:12px; color:#b91c1c; font-weight:bold;">[{row['涉及教材']}]</span>
                        <h3 style="margin:5px 0;">{row['标题']}</h3>
                        <p style="font-size:13px; color:#64748b;">存档日期：{row['日期']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    with st.expander("点击展开：考点解析与原文详情"):
                        c1, c2 = st.columns([1.5, 1])
                        with c1:
                            st.markdown("**【教研解析】**")
                            st.write(row['核心解析'])
                        with c2:
                            st.markdown("**【素材原文】**")
                            st.caption(row.get('原文内容', row.get('原文', "无")))
                        if st.button(f"🗑️ 删除该素材记录", key=f"del_{i}"):
                            full_df.drop(i).to_csv(user_db, index=False, encoding='utf-8-sig')
                            st.rerun()
        else:
            st.info("库内尚无素材。")
