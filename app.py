import streamlit as st
import pandas as pd
from github import Github
from openai import OpenAI
import hashlib
import re
import io
from datetime import datetime

# --- 1. 样式配置 (保留高感知视觉效果) ---
st.set_page_config(page_title="思政名师智能素材库", layout="wide", page_icon="🏛️")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    /* 荧光笔高亮 */
    mark { background-color: #ffff00 !important; color: #000 !important; padding: 0 3px; border-radius: 3px; font-weight: bold; }
    /* 重点红字 */
    .important-red { color: #e11d48 !important; font-weight: bold; }
    /* 卡片美化 */
    .stExpander { border: 1px solid #e2e8f0 !important; border-radius: 12px !important; background: white !important; margin-bottom: 10px !important; }
    /* 教材色块标签 */
    .book-tag { 
        background: #fee2e2; color: #b91c1c; padding: 2px 8px; border-radius: 4px; 
        font-size: 12px; font-weight: bold; display: block; margin-bottom: 5px; 
        text-align: center; border: 1px solid #fecaca;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心引擎 (PDF读取 + GitHub同步) ---
def get_github_repo():
    return Github(st.secrets["GH_TOKEN"]).get_repo(st.secrets["GH_REPO"])

def get_available_books():
    """实时扫描 data/ 目录获取 PDF 教材列表"""
    try:
        repo = get_github_repo()
        files = repo.get_contents("data")
        books = [f.name.replace('.pdf', '').replace('.PDF', '').strip() for f in files if f.name.endswith(('.pdf', '.PDF'))]
        return sorted(books)
    except:
        return ["必修1", "必修2", "必修3", "必修4"]

def load_from_cloud(uid):
    """【云端防丢】实时同步数据与最新 SHA 校验码"""
    file_path = f"material_lib_{uid}.csv"
    standard_cols = ["日期", "标题", "涉及教材", "考点设问", "素材原文"]
    try:
        repo = get_github_repo()
        content = repo.get_contents(file_path)
        df = pd.read_csv(content.download_url)
        # 兼容旧版本所有可能的列名
        rename_map = {'素材标题': '标题', '精修解析': '考点设问', '核心解析': '考点设问', '分类': '涉及教材', '涉及教材': '涉及教材'}
        df.rename(columns=rename_map, inplace=True)
        for col in standard_cols:
            if col not in df.columns: df[col] = "未记录"
        return df[standard_cols], content.sha
    except:
        return pd.DataFrame(columns=standard_cols), None

# --- 3. 登录与身份识别 ---
if 'api_key' not in st.session_state: st.session_state['api_key'] = None

if not st.session_state['api_key']:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        st.title("🏛️ 思政名师工作室")
        input_key = st.text_input("请输入 DeepSeek API Key 登录", type="password")
        if st.button("🚀 开启工作室", use_container_width=True):
            if len(input_key) > 10:
                st.session_state['api_key'] = input_key
                st.session_state['uid'] = hashlib.md5(input_key.encode()).hexdigest()[:8]
                st.rerun()
else:
    uid = st.session_state['uid']
    db_filename = f"material_lib_{uid}.csv"
    book_options = get_available_books()
    
    # 强制预加载数据
    df_cloud, current_sha = load_from_cloud(uid)

    # --- 侧边栏 ---
    with st.sidebar:
        st.header(f"👤 老师 ID: {uid}")
        st.caption(f"📂 存档: {db_filename}")
        if st.button("🔄 强制同步云端数据", use_container_width=True):
            st.rerun()
        st.divider()
        st.subheader("📥 成果导出")
        if not df_cloud.empty:
            csv_io = io.BytesIO()
            df_cloud.to_csv(csv_io, index=False, encoding='utf-8-sig')
            st.download_button("导出 CSV 清单", data=csv_io.getvalue(), file_name=f"思政智库_{datetime.now().strftime('%m%d')}.csv", use_container_width=True)
        st.divider()
        if st.button("🚪 退出登录"):
            st.session_state.clear()
            st.rerun()

    # --- 主功能区 ---
    tab1, tab2 = st.tabs(["✨ 智能加工录入", "📂 结构化全景看板"])

    with tab1:
        l_col, r_col = st.columns([1.2, 1])
        with l_col:
            with st.container(border=True):
                m_title = st.text_input("1. 素材标题")
                m_raw = st.text_area("2. 素材原文", height=200)
                m_books = st.multiselect("3. 关联教材 (支持跨册联动)", options=book_options)
                
                if st.button("🧠 开启多维深度高亮分析", use_container_width=True):
                    if m_title and m_books and m_raw:
                        client = OpenAI(api_key=st.session_state['api_key'], base_url="https://api.deepseek.com")
                        with st.spinner("跨册联动教研分析中..."):
                            prompt = f"""你是一位高中政治名师。请针对素材《{m_title}》在以下教材中进行深度教研分析：{', '.join(m_books)}。
                            要求：
                            1. 分册解析：各教材对应的考点。
                            2. 跨教材联动：知识点间的内在逻辑（如经济现象与哲学逻辑）。
                            3. 综合设问：1-2个高质量设问。
                            注意：严禁加粗。核心词包裹在 <mark> </mark> 中；关键结论用 <span class='important-red'> </span>。素材：{m_raw}"""
                            
                            resp = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                            # 自动将 **加粗** 转为荧光笔 mark
                            st.session_state['ai_output'] = re.sub(r'\*\*(.*?)\*\*', r'<mark>\1</mark>', resp.choices[0].message.content)
                    else:
                        st.warning("请完整填写标题、原文并选择教材")

        with r_col:
            if 'ai_output' in st.session_state:
                st.markdown("✍️ **预览与精修**")
                final_text = st.text_area("解析结果 (可手动编辑)", value=st.session_state['ai_output'], height=450)
                if st.button("💾 确认归档入库", use_container_width=True):
                    new_data = {"日期": datetime.now().strftime("%Y-%m-%d"), "标题": m_title, "涉及教材": " | ".join(m_books), "考点设问": final_text, "素材原文": m_raw}
                    updated_df = pd.concat([df_cloud, pd.DataFrame([new_data])], ignore_index=True)
                    
                    repo = get_github_repo()
                    csv_str = updated_df.to_csv(index=False, encoding='utf-8-sig')
                    
                    # 保存前最后一刻再次抓取 SHA 防止丢失
                    _, latest_sha = load_from_cloud(uid)
                    if latest_sha:
                        repo.update_file(db_filename, "Save", csv_str, latest_sha)
                    else:
                        repo.create_file(db_filename, "Init", csv_str)
                    
                    st.success("✅ 归档成功！数据已实时同步。")
                    del st.session_state['ai_output']
                    st.rerun()

    with tab2:
        df_display = df_cloud
        if not df_display.empty:
            st.subheader("📊 快速索引表")
            st.dataframe(df_display[["日期", "标题", "涉及教材"]], use_container_width=True, hide_index=True)
            st.divider()
            
            search = st.text_input("🔍 搜索库内素材关键词...")
            show_df = df_display[df_display.apply(lambda r: r.astype(str).str.contains(search).any(), axis=1)] if search else df_display
            
            st.subheader("📖 结构化看板 (高亮详情)")
            for i, row in show_df.iloc[::-1].iterrows():
                with st.expander(f"📌 {row['标题']} | {row['涉及教材']}"):
                    # 1:2.5 分栏回归
                    c1, c2 = st.columns([1, 2.5])
                    with c1:
                        st.markdown("**📚 涉及教材**")
                        for b in str(row['涉及教材']).split(" | "):
                            st.markdown(f"<span class='book-tag'>{b}</span>", unsafe_allow_html=True)
                    with c2:
                        st.markdown("**💡 联动教研解析**")
                        st.markdown(row['考点设问'], unsafe_allow_html=True)
                    
                    st.divider()
                    st.caption(f"素材原文参考：{row['素材原文']}")
                    if st.button(f"🗑️ 删除此记录", key=f"del_{i}"):
                        new_df = df_display.drop(i)
                        get_github_repo().update_file(db_filename, "Delete", new_df.to_csv(index=False, encoding='utf-8-sig'), current_sha)
                        st.rerun()
        else:
            st.info("您的库目前为空，请在加工页录入素材。")
