import streamlit as st
import pandas as pd
from openai import OpenAI
import requests
import base64
from datetime import datetime
import hashlib
import re
import os

# 1. 云端同步核心配置 (需在 Streamlit Secrets 配置 GH_TOKEN 和 GH_REPO)
GH_TOKEN = st.secrets.get("GH_TOKEN")
GH_REPO = st.secrets.get("GH_REPO")

def get_user_id(api_key):
    return hashlib.md5(api_key.encode()).hexdigest()[:8]

def get_available_books():
    """【修复】重新上线：自动从 data 文件夹读取 PDF 文件名"""
    d_path = "data"
    if not os.path.exists(d_path): 
        os.makedirs(d_path)
    files = [f for f in os.listdir(d_path) if not f.startswith('.')]
    files.sort()
    return [f.replace('.pdf', '').replace('.PDF', '').replace('高中政治', '').strip() for f in files]

def sync_data(uid, df_to_save=None):
    """自动按老师 UID 在云端存取专属文件"""
    if not GH_TOKEN or not GH_REPO:
        return pd.DataFrame(columns=["日期", "标题", "涉及教材", "考点设问", "素材原文"]), None
    
    filename = f"material_lib_{uid}.csv"
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{filename}"
    headers = {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    if df_to_save is None: 
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            res = r.json()
            content = base64.b64decode(res['content']).decode('utf-8-sig')
            from io import StringIO
            return pd.read_csv(StringIO(content)), res['sha']
        return pd.DataFrame(columns=["日期", "标题", "涉及教材", "考点设问", "素材原文"]), None
    else: 
        r_get = requests.get(url, headers=headers)
        sha = r_get.json().get('sha') if r_get.status_code == 200 else None
        content_b64 = base64.b64encode(df_to_save.to_csv(index=False, encoding='utf-8-sig').encode('utf-8')).decode('utf-8')
        data = {"message": f"教研员 {uid} 自动同步", "content": content_b64, "sha": sha}
        requests.put(url, json=data, headers=headers)
        return None, None

def auto_highlight_fix(text):
    return re.sub(r'\*\*(.*?)\*\*', r'<mark>\1</mark>', text)

# 2. 页面美化与登录
st.set_page_config(page_title="思政名师专属云智库", layout="wide", page_icon="🏛️")
st.markdown("""<style>
    mark { background-color: #ffff00 !important; color: #000 !important; padding: 0 3px; border-radius: 3px; font-weight: bold; }
    .important-red { color: #e11d48 !important; font-weight: bold; }
    .book-tag { background: #fee2e2; color: #b91c1c; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; display: block; margin-bottom: 5px; text-align: center; border: 1px solid #fecaca; }
    .stExpander { border: 1px solid #e2e8f0 !important; border-radius: 12px !important; background: white !important; }
    </style>""", unsafe_allow_html=True)

if 'api_key' not in st.session_state: st.session_state['api_key'] = None

if not st.session_state['api_key']:
    st.title("🏛️ 思政名师专属云端智库")
    st.info("💡 已开启【一人一库】永久同步模式。请输入 API Key 登录。")
    key = st.text_input("DeepSeek API Key", type="password")
    if st.button("🚀 开启教研空间", use_container_width=True):
        if len(key) > 10:
            st.session_state['api_key'] = key
            st.session_state['uid'] = get_user_id(key)
            st.rerun()
else:
    uid = st.session_state['uid']
    df_cloud, current_sha = sync_data(uid)
    book_options = get_available_books() # 【修复】重新获取教材列表

    with st.sidebar:
        st.header(f"👤 老师 ID: {uid}")
        if not GH_TOKEN: st.error("⚠️ 未配置 GitHub Token，数据将无法自动保存！")
        else: st.success("☁️ 云端同步：已连接")
        
        if st.button("🚪 退出登录"):
            st.session_state['api_key'] = None
            st.rerun()
        st.divider()
        csv_file = df_cloud.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 导出全库备份", data=csv_file, file_name=f"智库备份_{uid}.csv", use_container_width=True)

    tab1, tab2 = st.tabs(["✨ 素材智能加工", "📂 结构化看板"])

    with tab1:
        l, r = st.columns([1.2, 1])
        with l:
            with st.container(border=True):
                m_title = st.text_input("1. 素材标题")
                m_raw = st.text_area("2. 素材原文内容", height=150)
                m_books = st.multiselect("3. 涉及教材", options=book_options)
                
                # 【修复】跨教材分析按钮点击后的响应逻辑
                if st.button("🧠 开启双重深度联动分析", use_container_width=True):
                    if not m_title or not m_books:
                        st.warning("请填写标题并选择教材")
                    else:
                        with st.spinner("AI 正在联动教材库进行深度分析..."):
                            try:
                                client = OpenAI(api_key=st.session_state['api_key'], base_url="https://api.deepseek.com")
                                prompt = f"""作为思政名师，请分析素材《{m_title}》在《{', '.join(m_books)}》中的应用。
                                要求：
                                1. 【分册解析】：详细列出每本教材对应的核心考点。
                                2. 【跨册联动】：分析不同教材模块间的逻辑联系。
                                3. 【教学设问】：给出 1-2 个综合性设问。
                                规范：核心词用 <mark> 标签，重要结论用 <span class='important-red'>。严禁使用 Markdown 加粗（**）。
                                素材原文：{m_raw}"""
                                
                                resp = client.chat.completions.create(
                                    model="deepseek-chat", 
                                    messages=[{"role":"user","content":prompt}]
                                )
                                st.session_state['buffer'] = auto_highlight_fix(resp.choices[0].message.content)
                            except Exception as e:
                                st.error(f"分析失败，请检查 API Key。错误详情: {e}")

        if 'buffer' in st.session_state:
            final_res = st.text_area("精修解析内容", value=st.session_state['buffer'], height=350)
            if st.button("💾 归档并永久保存到云端", use_container_width=True):
                new_row = {"日期": datetime.now().strftime("%Y-%m-%d"), "标题": m_title, "涉及教材": " | ".join(m_books), "考点设问": final_res, "素材原文": m_raw}
                df_cloud = pd.concat([df_cloud, pd.DataFrame([new_row])], ignore_index=True)
                sync_data(uid, df_cloud) 
                st.toast("✅ 数据已同步至云端仓库！")
                del st.session_state['buffer']
                st.rerun()

    with tab2:
        if not df_cloud.empty:
            for i, row in df_cloud.iloc[::-1].iterrows():
                with st.expander(f"📌 {row['标题']} | {row['涉及教材']}"):
                    col_l, col_r = st.columns([1, 2.5])
                    with col_l:
                        st.markdown("**涉及教材**")
                        for b in str(row['涉及教材']).split(" | "):
                            st.markdown(f"<span class='book-tag'>{b}</span>", unsafe_allow_html=True)
                    with col_r:
                        st.markdown("**💡 深度教研解析**")
                        st.markdown(row['考点设问'], unsafe_allow_html=True)
                    if st.button(f"🗑️ 删除此记录", key=f"del_{i}"):
                        df_cloud = df_cloud.drop(i)
                        sync_data(uid, df_cloud)
                        st.rerun()
