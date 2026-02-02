import streamlit as st
import pandas as pd
from openai import OpenAI
import os
from datetime import datetime
import hashlib

# 1. 页面配置与高级样式
st.set_page_config(page_title="思政名师智能素材库", layout="wide", page_icon="🏛️")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    /* 荧光笔高亮样式 */
    mark { background-color: #fef08a; padding: 0 4px; border-radius: 4px; font-weight: bold; color: #000; }
    .important-red { color: #dc2626; font-weight: bold; }
    /* 折叠框美化 */
    .stExpander { border: 1px solid #e2e8f0 !important; background-color: white !important; border-radius: 12px !important; margin-bottom: 10px !important; }
    /* 教材色块标签 */
    .book-tag { background: #fee2e2; color: #b91c1c; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; display: block; margin-bottom: 5px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# 2. 核心鲁棒性逻辑：解决 KeyError 和教材显示问题
def get_user_id(api_key):
    return hashlib.md5(api_key.encode()).hexdigest()[:8]

def get_available_books():
    """强制扫描 data 目录，解决显示不全"""
    d_path = "data"
    if not os.path.exists(d_path): os.makedirs(d_path)
    # 只要是文件就展示（不限制后缀），防止误删后缀导致识别失败
    files = [f for f in os.listdir(d_path) if not f.startswith('.')]
    files.sort()
    return [f.replace('.pdf', '').replace('.PDF', '').replace('高中政治', '').strip() for f in files]

def load_and_fix_db(file_path):
    """【黑科技】自动对齐列名，彻底终结 KeyError"""
    standard_cols = ["日期", "标题", "涉及教材", "考点设问", "素材原文"]
    if not os.path.exists(file_path):
        return pd.DataFrame(columns=standard_cols)
    
    try:
        df = pd.read_csv(file_path)
        # 兼容性映射：将旧版本的各种列名强制对齐到标准版
        rename_map = {
            '精修解析': '考点设问', '核心知识点': '考点设问', '核心解析': '考点设问', '分析结果': '考点设问',
            '关联教材': '涉及教材', '教材': '涉及教材', '涉及教材 ': '涉及教材',
            '原文': '素材原文', '素材原文内容': '素材原文', '原文内容': '素材原文'
        }
        df.rename(columns=rename_map, inplace=True)
        
        # 补齐缺失列
        for col in standard_cols:
            if col not in df.columns:
                df[col] = "未记录"
        
        return df[standard_cols]
    except Exception:
        return pd.DataFrame(columns=standard_cols)

# 3. 登录权限
if 'api_key' not in st.session_state: st.session_state['api_key'] = None

if not st.session_state['api_key']:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        st.title("🏛️ 思政名师工作室")
        st.info("系统将根据 API Key 自动隔离不同老师的云端数据库。")
        input_key = st.text_input("请输入您的 DeepSeek API Key", type="password")
        if st.button("🚀 开启教研室", use_container_width=True):
            if len(input_key) > 10:
                st.session_state['api_key'] = input_key
                st.session_state['uid'] = get_user_id(input_key)
                st.rerun()
else:
    uid = st.session_state['uid']
    db_file = f"material_lib_{uid}.csv"
    book_options = get_available_books()

    # --- 侧边栏 ---
    with st.sidebar:
        st.header(f"👤 老师 ID: {uid}")
        if st.button("🚪 退出登录"):
            st.session_state['api_key'] = None
            st.rerun()
        st.divider()
        st.subheader("📥 数据备份")
        df_tmp = load_and_fix_db(db_file)
        if not df_tmp.empty:
            csv = df_tmp.to_csv(index=False).encode('utf-8-sig')
            st.download_button("下载全部教研成果", data=csv, file_name=f"思政智库_{datetime.now().strftime('%Y%m%d')}.csv", use_container_width=True)

    tab1, tab2 = st.tabs(["✨ 智能录入加工", "📂 结构化全景看板"])

    # TAB 1: 录入与 AI 荧光笔高亮
    with tab1:
        left_c, right_c = st.columns([1.2, 1])
        with left_c:
            with st.container(border=True):
                m_title = st.text_input("1. 素材标题")
                m_raw = st.text_area("2. 素材原文", height=150)
                m_books = st.multiselect("3. 关联教材", options=book_options)
                
                if st.button("🧠 AI 跨教材高亮分析", use_container_width=True):
                    if not m_title or not m_raw or not m_books:
                        st.warning("请补全信息后再分析")
                    else:
                        client = OpenAI(api_key=st.session_state['api_key'], base_url="https://api.deepseek.com")
                        with st.spinner("正在涂抹荧光笔重点..."):
                            prompt = f"""你是一位思政名师。请分析素材《{m_title}》在《{'、'.join(m_books)}》中的核心考点。
                            要求：
                            1. 将最核心的【考点词汇】用 <mark>标签包围 </mark>（荧光笔效果）。
                            2. 将【关键结论】用 <span class='important-red'>红色样式包围 </span>。
                            3. 给出1-2个课堂设问。文字精炼，逻辑清晰。
                            素材内容：{m_raw}"""
                            resp = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                            st.session_state['buffer'] = resp.choices[0].message.content

            if 'buffer' in st.session_state:
                st.markdown("✍️ **老师精修与预览**（标记语法：`<mark>高亮</mark>`）")
                final_res = st.text_area("考点解析", value=st.session_state['buffer'], height=300)
                if st.button("💾 归档至云端库", use_container_width=True):
                    df = load_and_fix_db(db_file)
                    new_row = {"日期": datetime.now().strftime("%Y-%m-%d"), "标题": m_title, "涉及教材": " | ".join(m_books), "考点设问": final_res, "素材原文": m_raw}
                    pd.concat([df, pd.DataFrame([new_row])], ignore_index=True).to_csv(db_file, index=False, encoding='utf-8-sig')
                    st.success("归档成功！已存入看板。")
                    del st.session_state['buffer']
                    st.rerun()

    # TAB 2: 分列呈现看板
    with tab2:
        df = load_and_fix_db(db_file)
        if not df.empty:
            st.subheader("📝 极简教研清单")
            # 这里的表格绝对不会报 KeyError
            st.dataframe(df[["日期", "标题", "涉及教材"]], use_container_width=True, hide_index=True)
            
            st.divider()
            st.subheader("📖 分列详情预览 (支持荧光笔效果)")
            
            # 增加搜索功能
            q = st.text_input("🔍 搜索库内素材...")
            show_df = df[df.apply(lambda r: r.astype(str).str.contains(q).any(), axis=1)] if q else df
            
            for i, row in show_df.iloc[::-1].iterrows():
                # 使用 expander 实现您的折叠想法
                with st.expander(f"📌 {row['涉及教材']} | {row['标题']}"):
                    col_book, col_detail = st.columns([1, 2.5])
                    with col_book:
                        st.markdown("**📚 涉及教材**")
                        for b in str(row['涉及教材']).split(" | "):
                            st.markdown(f"<span class='book-tag'>{b}</span>", unsafe_allow_html=True)
                    with col_detail:
                        st.markdown("**💡 核心考点与解析**")
                        # 渲染高亮和颜色
                        st.markdown(row['考点设问'], unsafe_allow_html=True)
                    
                    st.divider()
                    st.caption(f"素材原文参考：{row.get('素材原文', '')}")
                    if st.button(f"🗑️ 删除此素材", key=f"del_{i}"):
                        df.drop(i).to_csv(db_file, index=False, encoding='utf-8-sig')
                        st.rerun()
        else:
            st.info("暂无素材。")
