import streamlit as st
import pandas as pd
from github import Github
from openai import OpenAI
import hashlib
import re
import io
import time
import uuid
from datetime import datetime

# --- 1. 样式与配置 ---
st.set_page_config(page_title="思政名师智能素材库", layout="wide", page_icon="🏛️")

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

# --- 2. 核心后端函数 ---
def get_github_repo():
    # 依然使用安全调用，防止密码泄露被系统秒封
    return Github(st.secrets["GH_TOKEN"]).get_repo(st.secrets["GH_REPO"])

def load_from_cloud(uid):
    """【防刷丢失补丁】强制穿透云端缓存获取真数据"""
    file_path = f"material_lib_{uid}.csv"
    standard_cols = ["日期", "标题", "涉及教材", "考点设问", "素材原文"]
    try:
        repo = get_github_repo()
        content = repo.get_contents(file_path)
        # 增加超级随机因子，阻断 GitHub 的 CDN 缓存
        fresh_url = f"{content.download_url}?cache_bust={uuid.uuid4()}"
        df = pd.read_csv(fresh_url)
        
        rename_map = {'素材标题': '标题', '精修解析': '考点设问', '核心解析': '考点设问', '涉及教材': '涉及教材', '分类': '涉及教材'}
        df.rename(columns=rename_map, inplace=True)
        for col in standard_cols:
            if col not in df.columns: df[col] = "未记录"
        return df[standard_cols], content.sha
    except Exception as e:
        # 【网络防空补丁】如果是真没找到文件(新用户404)，返回空表；如果是网络卡了，给警报！
        if "404" in str(e):
            return pd.DataFrame(columns=standard_cols), None
        else:
            st.error("⚠️ 连线云端服务器超时，请点击侧边栏【强制同步】重试！")
            return pd.DataFrame(columns=standard_cols), None

# --- 3. 初始化与登录拦截 ---
if 'uid' not in st.session_state: st.session_state['uid'] = None
if 'display_df' not in st.session_state: st.session_state['display_df'] = None

if not st.session_state['uid']:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        st.title("🏛️ 思政名师工作室")
        st.info("💡 提示：请输入您的 DeepSeek API Key 登录专属云端库。")
        input_key = st.text_input("请输入 API Key 登录", type="password")
        if st.button("🚀 开启工作室", use_container_width=True):
            # 【防呆补丁】自动清除复制粘贴带来的首尾空格和换行符！
            clean_key = input_key.strip()
            if len(clean_key) > 10:
                st.session_state['api_key'] = clean_key
                st.session_state['uid'] = hashlib.md5(clean_key.encode()).hexdigest()[:8]
                st.rerun()
            else:
                st.warning("请输入有效的 API Key")
    st.stop()

uid = st.session_state['uid']
db_filename = f"material_lib_{uid}.csv"

# 强制初始化
if st.session_state['display_df'] is None:
    df_cloud, _ = load_from_cloud(uid)
    st.session_state['display_df'] = df_cloud

# --- 4. 侧边栏 ---
with st.sidebar:
    st.header(f"👤 老师 ID: {uid}")
    if st.button("🔄 强制同步云端数据", use_container_width=True):
        with st.spinner("正在穿透云端缓存..."):
            time.sleep(1.5)
            df_fresh, _ = load_from_cloud(uid)
            st.session_state['display_df'] = df_fresh
            st.toast("云端数据已强制对齐")
            st.rerun()
    st.divider()
    if not st.session_state['display_df'].empty:
        csv_io = io.BytesIO()
        st.session_state['display_df'].to_csv(csv_io, index=False, encoding='utf-8-sig')
        st.download_button("导出本地备份 (CSV)", data=csv_io.getvalue(), file_name=f"思政素材_{datetime.now().strftime('%m%d')}.csv", use_container_width=True)
    if st.button("🚪 退出登录"):
        st.session_state.clear()
        st.rerun()

# --- 5. 主功能区 ---
tab1, tab2 = st.tabs(["✨ 智能加工录入", "📂 结构化全景看板"])

with tab1:
    l_col, r_col = st.columns([1.2, 1])
    with l_col:
        with st.container(border=True):
            m_title = st.text_input("1. 素材标题")
            m_raw = st.text_area("2. 素材原文内容", height=200)
            
            # --- 教材选择逻辑（主包真实书单，彻底解决显示不全问题） ---
            fallback_books = [
                "必修1 中特",
                "必修2 经济与社会",
                "必修3 政治与法治",
                "必修4 哲学与文化 1-70",
                "必修4 哲学与文化71-134",
                "选择性必修1 当代国际政治与经济",
                "选择性必修2 法律与生活",
                "选择性必修3 逻辑与思维"
            ]
            
            try:
                repo_obj = get_github_repo()
                pdf_list = sorted([f.name.replace('.pdf', '').replace('.PDF', '') for f in repo_obj.get_contents("data") if f.name.lower().endswith('.pdf')])
            except:
                pdf_list = fallback_books
                
            if not pdf_list:
                pdf_list = fallback_books
                
            m_books = st.multiselect("3. 关联教材", options=pdf_list)
            
            if st.button("🧠 开启名师教研分析", use_container_width=True):
                if m_title and m_books and m_raw:
                    client = OpenAI(api_key=st.session_state['api_key'], base_url="https://api.deepseek.com")
                    with st.spinner("AI正在进行多维联动解析..."):
                        prompt = f"针对《{m_title}》结合教材 {m_books} 分析。严禁加粗。核心词用<mark>，结论用<span class='important-red'>。原文：{m_raw}"
                        try:
                            resp = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                            st.session_state['ai_output'] = re.sub(r'\*\*(.*?)\*\*', r'<mark>\1</mark>', resp.choices[0].message.content)
                        except Exception as e:
                            st.error(f"调用 AI 接口失败，请检查 API Key 余额或网络连接。错误：{e}")
                else: 
                    st.warning("请完整填写素材标题、原文并勾选关联教材")

    with r_col:
        if 'ai_output' in st.session_state:
            st.markdown("✍️ **预览与精修**")
            final_text = st.text_area("解析结果", value=st.session_state['ai_output'], height=450)
            if st.button("💾 确认归档入库", use_container_width=True):
                new_row = {"日期": datetime.now().strftime("%Y-%m-%d"), "标题": m_title, "涉及教材": " | ".join(m_books), "考点设问": final_text, "素材原文": m_raw}
                
                # --- 第一步：内存直接更新（保证右边立刻有） ---
                st.session_state['display_df'] = pd.concat([st.session_state['display_df'], pd.DataFrame([new_row])], ignore_index=True)
                
                # --- 第二步：同步至 GitHub ---
                try:
                    repo = get_github_repo()
                    csv_str = st.session_state['display_df'].to_csv(index=False, encoding='utf-8-sig')
                    _, latest_sha = load_from_cloud(uid)
                    if latest_sha: repo.update_file(db_filename, "Update", csv_str, latest_sha)
                    else: repo.create_file(db_filename, "Init", csv_str)
                    
                    st.success("✅ 归档成功！已写入云端。")
                    if 'ai_output' in st.session_state: del st.session_state['ai_output']
                    st.rerun()
                except Exception as e:
                    st.error(f"云端同步超时，但本地已暂存。建议10秒后点侧边栏刷新。错误: {e}")

with tab2:
    # 始终展示 st.session_state['display_df']，这是最实时的
    if not st.session_state['display_df'].empty:
        st.subheader("📊 快速索引清单")
        st.dataframe(st.session_state['display_df'][["日期", "标题", "涉及教材"]], use_container_width=True, hide_index=True)
        st.divider()
        
        st.subheader("📖 结构化看板详情")
        search = st.text_input("🔍 搜索关键词（标题、教材、考点）")
        df_filtered = st.session_state['display_df']
        if search:
            df_filtered = df_filtered[df_filtered.apply(lambda r: r.astype(str).str.contains(search).any(), axis=1)]
        
        for i, row in df_filtered.iloc[::-1].iterrows():
            with st.expander(f"📌 {row['标题']} | {row['涉及教材']}"):
                c1, c2 = st.columns([1, 2.5])
                with c1:
                    st.markdown("**📚 涉及教材**")
                    for b in str(row['涉及教材']).split(" | "):
                        st.markdown(f"<span class='book-tag'>{b}</span>", unsafe_allow_html=True)
                with c2:
                    st.markdown("**💡 深度联动解析**")
                    st.markdown(row['考点设问'], unsafe_allow_html=True)
                st.divider()
                st.caption(f"素材原文参考：{row['素材原文']}")
                if st.button(f"🗑️ 删除", key=f"del_{i}"):
                    st.session_state['display_df'] = st.session_state['display_df'].drop(i)
                    # 同步到云端
                    csv_str = st.session_state['display_df'].to_csv(index=False, encoding='utf-8-sig')
                    _, latest_sha = load_from_cloud(uid)
                    get_github_repo().update_file(db_filename, "Delete", csv_str, latest_sha)
                    st.rerun()
    else:
        st.info("库内暂无素材，请在加工页录入。")
