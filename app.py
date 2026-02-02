import streamlit as st
import pandas as pd
from openai import OpenAI
import os
from datetime import datetime
import hashlib

# 1. 页面配置与视觉优化
st.set_page_config(page_title="思政名师智能素材库", layout="wide", page_icon="🏛️")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    /* 卡片样式 */
    .material-card { 
        background: white; 
        padding: 20px; 
        border-radius: 12px; 
        border-top: 5px solid #b91c1c; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); 
        margin-bottom: 20px; 
    }
    /* 侧边栏及其他UI微调 */
    .stDataFrame { border: 1px solid #e2e8f0; border-radius: 8px; }
    .editor-container { background-color: #fffbeb; padding: 20px; border-radius: 12px; border: 1px solid #fcd34d; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 2. 工具函数
def get_user_id(api_key):
    """根据API Key生成唯一用户ID，确保数据隔离"""
    return hashlib.md5(api_key.encode()).hexdigest()[:8]

def get_available_books():
    """获取并净化教材名称，解决显示不全问题"""
    data_path = "data"
    if not os.path.exists(data_path):
        return ["请创建data文件夹"]
    # 兼容 .pdf 和 .PDF，并排序
    files = [f for f in os.listdir(data_path) if f.lower().endswith('.pdf')]
    files.sort()
    # 净化名称显示：去掉后缀，去掉常见冗余词
    cleaned_names = [f.replace('.pdf', '').replace('.PDF', '').replace('高中政治', '').strip() for f in files]
    return cleaned_names if cleaned_names else ["未检测到教材"]

# 3. 登录权限检查
if 'api_key' not in st.session_state:
    st.session_state['api_key'] = None

if not st.session_state['api_key']:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        st.title("🏛️ 思政名师专属素材空间")
        st.info("请输入您的 API Key 开启云端教研库。系统将根据 Key 自动隔离您的私人数据。")
        input_key = st.text_input("DeepSeek API Key", type="password")
        if st.button("🚀 进入工作室", use_container_width=True):
            if len(input_key) > 10:
                st.session_state['api_key'] = input_key
                st.session_state['user_id'] = get_user_id(input_key)
                st.rerun()
            else:
                st.error("请输入有效的 API Key")
else:
    user_id = st.session_state['user_id']
    user_db = f"material_lib_{user_id}.csv"
    
    # --- 侧边栏：管理与导出 ---
    with st.sidebar:
        st.header(f"👤 老师 ID: {user_id}")
        if st.button("🚪 退出当前工作室"):
            st.session_state['api_key'] = None
            st.rerun()
        st.divider()
        st.subheader("📥 离线备份")
        if os.path.exists(user_db):
            df_exp = pd.read_csv(user_db)
            csv_data = df_exp.to_csv(index=False).encode('utf-8-sig')
            st.download_button("下载全部素材 (Excel/CSV)", data=csv_data, file_name=f"素材导出_{user_id}.csv", use_container_width=True)
        st.caption("提示：若上传了新教材没看到，请尝试刷新页面或点击右上角三点-Clear cache。")

    # --- 主功能区：Tab 切换 ---
    tab1, tab2 = st.tabs(["✨ 智能加工入库", "📂 全景教研看板"])

    # TAB 1: 录入加工
    with tab1:
        left_c, right_c = st.columns([1.2, 1])
        with left_c:
            st.subheader("✍️ 素材跨教材加工")
            with st.container(border=True):
                m_title = st.text_input("1. 素材标题", placeholder="如：‘新质生产力’带动产业升级")
                m_raw = st.text_area("2. 素材原文内容", height=150, placeholder="粘贴时政报道或案例原文...")
                
                # 获取教材列表
                book_options = get_available_books()
                m_books = st.multiselect("3. 关联教材（可多选，实现逻辑跨越）", options=book_options)
                
                if st.button("🧠 AI 跨教材深度分析", use_container_width=True):
                    if not m_title or not m_raw or not m_books:
                        st.warning("请完整填写标题、内容并选择至少一本教材")
                    else:
                        client = OpenAI(api_key=st.session_state['api_key'], base_url="https://api.deepseek.com")
                        with st.spinner("AI 正在联动教材解析知识点..."):
                            prompt = f"""你是一位高中政治特级教师。请分析素材《{m_title}》在《{'、'.join(m_books)}》等教材中的核心考点。
                            要求：
                            1. 【跨教材定位】：分教材列出知识点（如：【必修2】... 【必修4】...）。
                            2. 【教学设问】：给出1-2个高质量课堂设问。
                            素材内容：{m_raw}"""
                            try:
                                resp = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                                st.session_state['analysis_buffer'] = resp.choices[0].message.content
                            except Exception as e:
                                st.error(f"分析请求失败，请检查Key或网络：{e}")

            # 老师精修区
            if 'analysis_buffer' in st.session_state:
                st.markdown('<div class="editor-container">', unsafe_allow_html=True)
                st.markdown("✍️ **老师精修区**（您可以根据实际教学调整 AI 的表述）")
                final_analysis = st.text_area("考点分析与设问建议", value=st.session_state['analysis_buffer'], height=300)
                
                if st.button("💾 确认并存入档案库", use_container_width=True):
                    new_entry = {
                        "日期": datetime.now().strftime("%Y-%m-%d"),
                        "标题": m_title,
                        "关联教材": " | ".join(m_books),
                        "核心知识点": final_analysis,
                        "原文": m_raw
                    }
                    df = pd.read_csv(user_db) if os.path.exists(user_db) else pd.DataFrame(columns=["日期","标题","关联教材","核心知识点","原文"])
                    df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
                    df.to_csv(user_db, index=False, encoding='utf-8-sig')
                    st.success("✅ 素材归档成功！")
                    del st.session_state['analysis_buffer']
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        with right_c:
            st.subheader("💡 教研建议")
            st.info("您可以一次性勾选《必修2》和《必修4》，AI 会自动为您构建‘经济生活’与‘哲学逻辑’的跨课桥梁。")

    # TAB 2: 全景看板 (表格 + 卡片)
    with tab2:
        if os.path.exists(user_db):
            full_df = pd.read_csv(user_db).fillna("")
            
            # 字段名兼容性修复（解决 Key报错）
            name_map = {'精修解析': '核心知识点', '核心解析': '核心知识点', '分析结果': '核心知识点'}
            for old_name, new_name in name_map.items():
                if old_name in full_df.columns and new_name not in full_df.columns:
                    full_df.rename(columns={old_name: new_name}, inplace=True)

            st.subheader("📖 结构化素材清单表")
            # 搜索过滤
            search_q = st.text_input("🔍 全库搜索（标题、教材、考点关键词）")
            if search_q:
                full_df = full_df[full_df.apply(lambda r: r.astype(str).str.contains(search_q).any(), axis=1)]

            # 强化表格索引视图
            view_df = full_df.copy()
            view_df['知识预览'] = view_df['核心知识点'].apply(lambda x: str(x).replace('\n', ' ')[:80] + '...')
            
            st.dataframe(
                view_df[["日期", "标题", "关联教材", "知识预览"]],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "日期": st.column_config.Column(width="small"),
                    "标题": st.column_config.Column("素材标题", width="medium"),
                    "关联教材": st.column_config.Column("对应书目", width="medium"),
                    "知识预览": st.column_config.Column("核心考点一览", width="large"),
                }
            )

            st.divider()

            # 详细卡片视图
            st.subheader("🗂️ 详细档案卡片")
            for i, row in full_df.iloc[::-1].iterrows():
                with st.container():
                    st.markdown(f"""
                    <div class="material-card">
                        <small style="color:#b91c1c; font-weight:bold;">{row['关联教材']}</small>
                        <h3 style="margin:5px 0;">{row['标题']}</h3>
                        <p style="font-size:12px; color:gray;">入库日期：{row['日期']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    with st.expander("查看完整分析与原文内容"):
                        c1, c2 = st.columns([1.5, 1])
                        with c1:
                            st.markdown("**【跨教材教研分析】**")
                            st.write(row['核心知识点'])
                        with c2:
                            st.markdown("**【原文参考】**")
                            st.caption(row.get('原文', "无原文信息"))
                        if st.button(f"🗑️ 删除该条素材", key=f"del_{i}"):
                            full_df.drop(i).to_csv(user_db, index=False, encoding='utf-8-sig')
                            st.rerun()
        else:
            st.info("您的档案库还是空的，快去加工第一条素材吧！")
