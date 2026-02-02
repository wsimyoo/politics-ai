import streamlit as st
import pandas as pd
from openai import OpenAI
import os
from datetime import datetime
import hashlib
import re

# 1. 页面高级配置
st.set_page_config(page_title="思政名师智能素材库", layout="wide", page_icon="🏛️")

# 自定义 CSS：渲染荧光笔、红字、卡片及教材标签
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    /* 荧光笔高亮：强制黄色背景 */
    mark { 
        background-color: #ffff00 !important; 
        color: #000 !important; 
        padding: 0 3px; 
        border-radius: 3px; 
        font-weight: bold;
    }
    /* 重点红字 */
    .important-red { 
        color: #e11d48 !important; 
        font-weight: bold; 
    }
    /* 卡片与标签样式 */
    .stExpander { border: 1px solid #e2e8f0 !important; border-radius: 12px !important; background: white !important; margin-bottom: 10px !important; }
    .book-tag { 
        background: #fee2e2; 
        color: #b91c1c; 
        padding: 2px 8px; 
        border-radius: 4px; 
        font-size: 12px; 
        font-weight: bold; 
        display: block; 
        margin-bottom: 5px; 
        text-align: center;
        border: 1px solid #fecaca;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. 核心后端逻辑引擎
def get_user_id(api_key):
    return hashlib.md5(api_key.encode()).hexdigest()[:8]

def get_available_books():
    """扫描教材文件"""
    d_path = "data"
    if not os.path.exists(d_path): os.makedirs(d_path)
    files = [f for f in os.listdir(d_path) if not f.startswith('.')]
    files.sort()
    return [f.replace('.pdf', '').replace('.PDF', '').replace('高中政治', '').strip() for f in files]

def auto_highlight_fix(text):
    """【黑科技】将 AI 的 **加粗** 强制转为 <mark> 荧光笔标签"""
    return re.sub(r'\*\*(.*?)\*\*', r'<mark>\1</mark>', text)

def load_and_fix_db(file_path):
    """【防御性编程】自动修复列名，防止 KeyError"""
    standard_cols = ["日期", "标题", "涉及教材", "考点设问", "素材原文"]
    if not os.path.exists(file_path):
        return pd.DataFrame(columns=standard_cols)
    try:
        df = pd.read_csv(file_path)
        rename_map = {
            '精修解析': '考点设问', '核心知识点': '考点设问', '核心解析': '考点设问', 
            '分析结果': '考点设问', '关联教材': '涉及教材', '教材': '涉及教材',
            '原文': '素材原文', '原文内容': '素材原文'
        }
        df.rename(columns=rename_map, inplace=True)
        for col in standard_cols:
            if col not in df.columns: df[col] = "未记录"
        return df[standard_cols]
    except:
        return pd.DataFrame(columns=standard_cols)

# 3. 登录与身份隔离
if 'api_key' not in st.session_state: st.session_state['api_key'] = None

if not st.session_state['api_key']:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        st.title("🏛️ 思政名师工作室")
        st.write("输入 API Key 开启您的云端教研空间")
        input_key = st.text_input("DeepSeek API Key", type="password")
        if st.button("🚀 开启工作室", use_container_width=True):
            if len(input_key) > 10:
                st.session_state['api_key'] = input_key
                st.session_state['uid'] = get_user_id(input_key)
                st.rerun()
else:
    uid = st.session_state['uid']
    db_file = f"material_lib_{uid}.csv"
    book_options = get_available_books()

    # --- 侧边栏：找回导出与管理功能 ---
    with st.sidebar:
        st.header(f"👤 老师 ID: {uid}")
        if st.button("🚪 退出登录", use_container_width=True):
            st.session_state['api_key'] = None
            st.rerun()
        st.divider()
        st.subheader("📥 教研成果导出")
        df_all = load_and_fix_db(db_file)
        if not df_all.empty:
            csv_data = df_all.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="下载全部素材 (Excel/CSV)",
                data=csv_data,
                file_name=f"思政素材导出_{datetime.now().strftime('%m%d')}.csv",
                mime='text/csv',
                use_container_width=True
            )
        st.divider()
        st.caption("提示：若教材不全，请检查 data 文件夹并清除缓存。")

    # --- 主功能区：双视图 ---
    tab1, tab2 = st.tabs(["✨ 智能加工入库", "📂 全景结构化看板"])

    # TAB 1: 加工与荧光笔处理
    with tab1:
        left_c, right_c = st.columns([1.2, 1])
        with left_c:
            with st.container(border=True):
                m_title = st.text_input("1. 素材标题")
                m_raw = st.text_area("2. 素材原文内容", height=150)
                m_books = st.multiselect("3. 关联教材", options=book_options)
                
                if st.button("🧠 AI 深度高亮解析", use_container_width=True):
                    if not m_title or not m_books:
                        st.warning("请填写标题并选择教材")
                    else:
                        client = OpenAI(api_key=st.session_state['api_key'], base_url="https://api.deepseek.com")
                        with st.spinner("正在捕捉重点并涂抹荧光笔..."):
                            prompt = f"""你是一位高中政治名师。分析素材《{m_title}》在《{'、'.join(m_books)}》中的核心考点。
                            
                            要求：
                            1. 严禁使用 ** 加粗。
                            2. 核心考点词必须用 <mark> 标签包围。
                            3. 核心结论用 <span class='important-red'> 标签包围。
                            素材原文：{m_raw}"""
                            resp = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                            # AI 生成后立即执行加粗转荧光笔的自动修正
                            st.session_state['buffer'] = auto_highlight_fix(resp.choices[0].message.content)

            if 'buffer' in st.session_state:
                st.markdown("✍️ **预览与精修**（支持 HTML 标签：`<mark>`荧光笔，`<span class='important-red'>`红字）")
                final_res = st.text_area("考点解析结果", value=st.session_state['buffer'], height=300)
                if st.button("💾 归档至云端库", use_container_width=True):
                    df = load_and_fix_db(db_file)
                    new_row = {"日期": datetime.now().strftime("%Y-%m-%d"), "标题": m_title, "涉及教材": " | ".join(m_books), "考点设问": final_res, "素材原文": m_raw}
                    pd.concat([df, pd.DataFrame([new_row])], ignore_index=True).to_csv(db_file, index=False, encoding='utf-8-sig')
                    st.success("入库成功！已同步至看板。")
                    del st.session_state['buffer']
                    st.rerun()

    # TAB 2: 结构化分列看板
    with tab2:
        df = load_and_fix_db(db_file)
        if not df.empty:
            st.subheader("📝 快速索引清单")
            st.dataframe(df[["日期", "标题", "涉及教材"]], use_container_width=True, hide_index=True)
            
            st.divider()
            st.subheader("📖 结构化分列视图 (支持荧光笔显示)")
            
            q = st.text_input("🔍 搜索库内素材内容...")
            show_df = df[df.apply(lambda r: r.astype(str).str.contains(q).any(), axis=1)] if q else df
            
            for i, row in show_df.iloc[::-1].iterrows():
                with st.expander(f"📌 {row['涉及教材']} | {row['标题']}"):
                    col_l, col_r = st.columns([1, 2.5])
                    with col_l:
                        st.markdown("**📚 对应教材**")
                        for b in str(row['涉及教材']).split(" | "):
                            st.markdown(f"<span class='book-tag'>{b}</span>", unsafe_allow_html=True)
                    with col_r:
                        st.markdown("**💡 考点深度解析**")
                        # 最终渲染：将 HTML 标签转为真实视觉效果
                        st.markdown(row['考点设问'], unsafe_allow_html=True)
                    
                    st.divider()
                    st.caption(f"素材原文：{row.get('素材原文', '')}")
                    if st.button(f"🗑️ 删除此素材", key=f"del_{i}"):
                        df.drop(i).to_csv(db_file, index=False, encoding='utf-8-sig')
                        st.rerun()
        else:
            st.info("库内暂无数据。")
