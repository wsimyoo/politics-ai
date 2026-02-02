import streamlit as st
import pandas as pd
from openai import OpenAI
import os
from datetime import datetime
import hashlib
import re

# 1. 页面高级配置与自定义视觉样式
st.set_page_config(page_title="思政名师智能素材库", layout="wide", page_icon="🏛️")

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
    /* 重点红字样式 */
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

# 2. 核心后端引擎函数
def get_user_id(api_key):
    return hashlib.md5(api_key.encode()).hexdigest()[:8]

def get_available_books():
    """扫描 data 目录获取教材列表"""
    d_path = "data"
    if not os.path.exists(d_path): os.makedirs(d_path)
    files = [f for f in os.listdir(d_path) if not f.startswith('.')]
    files.sort()
    return [f.replace('.pdf', '').replace('.PDF', '').replace('高中政治', '').strip() for f in files]

def auto_highlight_fix(text):
    """【核心功能】将 AI 习惯性使用的 **加粗** 强制转为 <mark> 荧光笔标签"""
    return re.sub(r'\*\*(.*?)\*\*', r'<mark>\1</mark>', text)

def load_and_fix_db(file_path):
    """【黑科技】自动对齐列名，防止所有历史版本的 KeyError"""
    standard_cols = ["日期", "标题", "涉及教材", "考点设问", "素材原文"]
    if not os.path.exists(file_path): return pd.DataFrame(columns=standard_cols)
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

# 3. 登录权限与身份识别
if 'api_key' not in st.session_state: st.session_state['api_key'] = None

if not st.session_state['api_key']:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        st.title("🏛️ 思政名师工作室")
        input_key = st.text_input("请输入您的 DeepSeek API Key", type="password")
        if st.button("🚀 开启工作室", use_container_width=True):
            if len(input_key) > 10:
                st.session_state['api_key'] = input_key
                st.session_state['uid'] = get_user_id(input_key)
                st.rerun()
else:
    uid = st.session_state['uid']
    db_file = f"material_lib_{uid}.csv"
    book_options = get_available_books()

    # --- 侧边栏：管理与【导出】功能 ---
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
            st.download_button("导出 CSV 清单", data=csv_data, file_name=f"思政智库_{datetime.now().strftime('%m%d')}.csv", use_container_width=True)
        st.divider()
        st.caption("提示：若教材不全，请检查 data 目录并 Clear Cache。")

    # --- 主功能区：Tab 切换 ---
    tab1, tab2 = st.tabs(["✨ 智能加工录入", "📂 结构化全景看板"])

    # TAB 1: 录入与【各教材分析+跨教材联动】逻辑
    with tab1:
        left_c, right_c = st.columns([1.2, 1])
        with left_c:
            with st.container(border=True):
                m_title = st.text_input("1. 素材标题")
                m_raw = st.text_area("2. 素材原文内容", height=150)
                m_books = st.multiselect("3. 关联教材（选择多本以开启联动分析）", options=book_options)
                
                if st.button("🧠 开启多维深度高亮分析", use_container_width=True):
                    if not m_title or not m_books:
                        st.warning("请填写标题并选择教材")
                    else:
                        client = OpenAI(api_key=st.session_state['api_key'], base_url="https://api.deepseek.com")
                        with st.spinner("正在进行多教材联觉分析并涂抹重点..."):
                            prompt = f"""你是一位高中政治名师。请针对素材《{m_title}》在以下教材中进行深度教研分析：{', '.join(m_books)}。
                            
                            请严格按以下【三段式结构】输出：
                            
                            ### 1️⃣ 各教材分册解析
                            针对所选的每一本教材，分别列出其在该素材中对应的核心考点。
                            
                            ### 2️⃣ 跨教材联动分析
                            深入分析这些不同教材的知识点如何通过该素材产生内在逻辑关联（例如：必修2的经济现象如何体现必修4的哲学逻辑）。
                            
                            ### 3️⃣ 综合教学设问
                            给出 1-2 个高质量的综合性教学设问。
                            
                            排版规范：严禁加粗。核心词包裹在 <mark> </mark> 之间；核心结论用 <span class='important-red'> </span>。
                            素材内容：{m_raw}"""
                            
                            resp = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                            # AI 生成后立即执行“加粗转荧光笔”自动修正
                            st.session_state['buffer'] = auto_highlight_fix(resp.choices[0].message.content)

            if 'buffer' in st.session_state:
                st.markdown("✍️ **预览与精修**")
                final_res = st.text_area("最终解析结果", value=st.session_state['buffer'], height=350)
                if st.button("💾 确认归档入库", use_container_width=True):
                    df_current = load_and_fix_db(db_file)
                    new_row = {"日期": datetime.now().strftime("%Y-%m-%d"), "标题": m_title, "涉及教材": " | ".join(m_books), "考点设问": final_res, "素材原文": m_raw}
                    pd.concat([df_current, pd.DataFrame([new_row])], ignore_index=True).to_csv(db_file, index=False, encoding='utf-8-sig')
                    st.success("入库成功！已同步至看板与导出中心。")
                    del st.session_state['buffer']
                    st.rerun()

    # TAB 2: 结构化看板 (已优化标题顺序)
    with tab2:
        df_display = load_and_fix_db(db_file)
        if not df_display.empty:
            st.subheader("📝 快速索引清单")
            st.dataframe(df_display[["日期", "标题", "涉及教材"]], use_container_width=True, hide_index=True)
            
            st.divider()
            st.subheader("📖 结构化看板 (高亮分列视图)")
            
            search_key = st.text_input("🔍 搜索库内素材...")
            show_df = df_display[df_display.apply(lambda r: r.astype(str).str.contains(search_key).any(), axis=1)] if search_key else df_display
            
            for i, row in show_df.iloc[::-1].iterrows():
                # 重点：素材名称在前，涉及教材在后
                with st.expander(f"📌 {row['标题']} | {row['涉及教材']}"):
                    col_l, col_r = st.columns([1, 2.5])
                    with col_l:
                        st.markdown("**📚 涉及教材**")
                        for b in str(row['涉及教材']).split(" | "):
                            st.markdown(f"<span class='book-tag'>{b}</span>", unsafe_allow_html=True)
                    with col_r:
                        st.markdown("**💡 深度教研解析 (分册解析+跨册联动)**")
                        # 最终渲染：呈现荧光笔和红字效果
                        st.markdown(row['考点设问'], unsafe_allow_html=True)
                    
                    st.divider()
                    st.caption(f"素材原文参考：{row.get('素材原文', '')}")
                    if st.button(f"🗑️ 删除此记录", key=f"del_{i}"):
                        df_display.drop(i).to_csv(db_file, index=False, encoding='utf-8-sig')
                        st.rerun()
        else:
            st.info("库内尚无素材。")

