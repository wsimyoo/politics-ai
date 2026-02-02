import streamlit as st
import pandas as pd
from openai import OpenAI
import os
from datetime import datetime
import hashlib
import re

# 1. 页面高级配置
st.set_page_config(page_title="思政名师智能素材库", layout="wide", page_icon="🏛️")

# 自定义 CSS：渲染荧光笔、红字、教材标签
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

# 2. 核心后端引擎
def get_user_id(api_key):
    return hashlib.md5(api_key.encode()).hexdigest()[:8]

def get_available_books():
    d_path = "data"
    if not os.path.exists(d_path): os.makedirs(d_path)
    files = [f for f in os.listdir(d_path) if not f.startswith('.')]
    files.sort()
    return [f.replace('.pdf', '').replace('.PDF', '').replace('高中政治', '').strip() for f in files]

def auto_highlight_fix(text):
    """将 AI 可能习惯性使用的 **加粗** 强制转为 <mark> 荧光笔标签"""
    return re.sub(r'\*\*(.*?)\*\*', r'<mark>\1</mark>', text)

def load_and_fix_db(file_path):
    """自动修复旧数据列名，并返回干净的数据框"""
    standard_cols = ["日期", "标题", "涉及教材", "考点设问", "素材原文"]
    if not os.path.exists(file_path): 
        return pd.DataFrame(columns=standard_cols)
    try:
        df = pd.read_csv(file_path)
        rename_map = {
            '精修解析': '考点设问', '核心知识点': '考点设问', 
            '核心解析': '考点设问', '分析结果': '考点设问',
            '关联教材': '涉及教材', '涉及教材 ': '涉及教材',
            '原文': '素材原文', '素材原文内容': '素材原文', '原文内容': '素材原文'
        }
        df.rename(columns=rename_map, inplace=True)
        # 补齐缺失列
        for col in standard_cols:
            if col not in df.columns: df[col] = "未记录"
        return df[standard_cols]
    except:
        return pd.DataFrame(columns=standard_cols)

# 3. 登录与侧边栏逻辑（包含导出）
if 'api_key' not in st.session_state: st.session_state['api_key'] = None

if not st.session_state['api_key']:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        st.title("🏛️ 思政名师工作室")
        input_key = st.text_input("请输入 DeepSeek API Key 开启教研库", type="password")
        if st.button("🚀 开启工作室", use_container_width=True):
            if len(input_key) > 10:
                st.session_state['api_key'] = input_key
                st.session_state['uid'] = get_user_id(input_key)
                st.rerun()
else:
    uid = st.session_state['uid']
    db_file = f"material_lib_{uid}.csv"
    book_options = get_available_books()

    # --- 这里是核心：侧边栏管理与【导出】功能 ---
    with st.sidebar:
        st.header(f"👤 老师 ID: {uid}")
        if st.button("🚪 退出登录", use_container_width=True):
            st.session_state['api_key'] = None
            st.rerun()
        
        st.divider()
        st.subheader("📥 教研导出中心")
        # 实时加载当前用户的数据库
        df_for_export = load_and_fix_db(db_file)
        if not df_for_export.empty:
            # 导出为 Excel 兼容的带 BOM 的 CSV
            csv_data = df_for_export.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 导出全量清单 (CSV)",
                data=csv_data,
                file_name=f"思政教研素材_{datetime.now().strftime('%m%d')}.csv",
                mime='text/csv',
                use_container_width=True
            )
            st.success("教研清单已就绪，点击上方按钮下载。")
        else:
            st.info("库内暂无素材可供导出。")
        
        st.divider()
        st.caption("技术提示：若教材列表未更新，请上传 PDF 后点击右上角三点 -> Clear Cache 强制刷新。")

    # --- 主功能区：Tab 切换 ---
    tab1, tab2 = st.tabs(["✨ 素材智能加工录入", "📂 结构化全景看板"])

    # TAB 1: 录入与跨教材深度关联
    with tab1:
        left_c, right_c = st.columns([1.2, 1])
        with left_c:
            with st.container(border=True):
                m_title = st.text_input("1. 素材标题", placeholder="输入素材的核心标题")
                m_raw = st.text_area("2. 素材原文内容", height=150)
                m_books = st.multiselect("3. 关联多本教材（开启跨模块深度联想）", options=book_options)
                
                if st.button("🧠 开启跨教材深度分析", use_container_width=True):
                    if not m_title or not m_books:
                        st.warning("请补全标题并勾选教材")
                    else:
                        client = OpenAI(api_key=st.session_state['api_key'], base_url="https://api.deepseek.com")
                        with st.spinner("AI 正在联动解析并涂抹重点高亮..."):
                            prompt = f"""你是一位高中政治特级教师。请深入分析素材《{m_title}》在以下多本教材中的交叉考点：{', '.join(m_books)}。
                            要求：
                            1. 【跨教材联动】：分析该素材如何将所选的不同教材模块（如经济、哲学、法治）有机结合。
                            2. 【标记语法】：严禁使用加粗。核心考点词必须包裹在 <mark> 和 </mark> 之间；核心金句用 <span class='important-red'> 和 </span> 包围。
                            3. 【教学设问】：针对关联知识点给出高质量设问。
                            原文：{m_raw}"""
                            resp = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                            # AI 生成后立即执行“加粗转荧光笔”自动修正，确保 100% 高亮
                            st.session_state['buffer'] = auto_highlight_fix(resp.choices[0].message.content)

            if 'buffer' in st.session_state:
                st.markdown("✍️ **预览与精修**（支持手动编辑标签）")
                final_res = st.text_area("考点解析详情", value=st.session_state['buffer'], height=300)
                if st.button("💾 确认存入云端库", use_container_width=True):
                    df_current = load_and_fix_db(db_file)
                    new_row = {"日期": datetime.now().strftime("%Y-%m-%d"), "标题": m_title, "涉及教材": " | ".join(m_books), "考点设问": final_res, "素材原文": m_raw}
                    pd.concat([df_current, pd.DataFrame([new_row])], ignore_index=True).to_csv(db_file, index=False, encoding='utf-8-sig')
                    st.success("✅ 归档成功！已同步至侧边栏导出及全景看板。")
                    del st.session_state['buffer']
                    st.rerun()

    # TAB 2: 结构化看板
    with tab2:
        df_display = load_and_fix_db(db_file)
        if not df_display.empty:
            st.subheader("📝 快速索引清单")
            st.dataframe(df_display[["日期", "标题", "涉及教材"]], use_container_width=True, hide_index=True)
            
            st.divider()
            st.subheader("📖 结构化看板 (高亮分列视图)")
            
            search_key = st.text_input("🔍 搜索全库素材关键词...")
            show_df = df_display[df_display.apply(lambda r: r.astype(str).str.contains(search_key).any(), axis=1)] if search_key else df_display
            
            for i, row in show_df.iloc[::-1].iterrows():
                with st.expander(f"📌 {row['涉及教材']} | {row['标题']}"):
                    col_l, col_r = st.columns([1, 2.5])
                    with col_l:
                        st.markdown("**📚 涉及教材**")
                        for b in str(row['涉及教材']).split(" | "):
                            st.markdown(f"<span class='book-tag'>{b}</span>", unsafe_allow_html=True)
                    with col_r:
                        st.markdown("**💡 深度解析 (含荧光笔重点)**")
                        # 最终渲染 HTML 高亮效果
                        st.markdown(row['考点设问'], unsafe_allow_html=True)
                    
                    st.divider()
                    st.caption(f"素材原文参考：{row.get('素材原文', '')}")
                    if st.button(f"🗑️ 删除该记录", key=f"del_{i}"):
                        df_display.drop(i).to_csv(db_file, index=False, encoding='utf-8-sig')
                        st.rerun()
        else:
            st.info("库内尚无教研素材。")

