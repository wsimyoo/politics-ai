import streamlit as st
import pandas as pd
from openai import OpenAI
import os
import pdfplumber
from datetime import datetime
import hashlib

st.set_page_config(page_title="我的思政素材库", page_icon="🗃️", layout="wide")

# 自定义样式：强调“仓库”的感觉
st.markdown("""
    <style>
    .stApp { background-color: #f3f4f6; }
    .input-card { background: white; padding: 20px; border-radius: 10px; border: 1px solid #e5e7eb; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .tag { display: inline-block; background: #e0f2fe; color: #0369a1; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; margin-right: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 核心：用户隔离与读取 ---
def get_user_hash(api_key):
    return hashlib.md5(api_key.encode()).hexdigest()[:8]

@st.cache_data(show_spinner=False)
def load_all_textbooks():
    """读取所有教材，构建一个大的知识背景"""
    data_dir = "data"
    combined_text = ""
    if not os.path.exists(data_dir): return ""
    files = [f for f in os.listdir(data_dir) if f.endswith('.pdf')]
    for f in files:
        try:
            with pdfplumber.open(os.path.join(data_dir, f)) as pdf:
                # 每本书提取前40页作为索引依据
                for page in pdf.pages[:40]:
                    txt = page.extract_text()
                    if txt: combined_text += txt + "\n"
        except: pass
    return combined_text

# --- 登录逻辑 ---
if 'api_key' not in st.session_state:
    st.session_state['api_key'] = None

if not st.session_state['api_key']:
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.title("🗃️ 个人专属素材库")
        st.info("输入您的 Key，系统将自动加载您个人的素材档案。")
        k = st.text_input("DeepSeek API Key", type="password")
        if st.button("🔓 打开我的素材库", use_container_width=True):
            if len(k) > 5:
                st.session_state['api_key'] = k
                st.session_state['user_id'] = get_user_hash(k)
                st.rerun()
else:
    # --- 登录后的主界面 ---
    user_id = st.session_state['user_id']
    db_file = f"library_{user_id}.csv" # 每个人的库文件名不一样
    
    # 预加载教材背景
    with st.spinner("正在连接云端教材库..."):
        textbook_context = load_all_textbooks()

    # 侧边栏
    with st.sidebar:
        st.write(f"👤 用户ID: `{user_id}`")
        if st.button("退出"):
            st.session_state['api_key'] = None
            st.rerun()
        st.divider()
        st.markdown("### 📊 库内统计")
        if os.path.exists(db_file):
            df = pd.read_csv(db_file)
            st.metric("已收录素材", f"{len(df)} 条")
        else:
            st.metric("已收录素材", "0 条")

    st.title("🗃️ 智能素材加工厂")

    # 页面布局：左边录入，右边查看
    tab1, tab2 = st.tabs(["➕ 素材入库 (AI 自动打标)", "🔍 检索我的库"])

    with tab1:
        st.markdown('<div class="input-card">', unsafe_allow_html=True)
        col1, col2 = st.columns([3, 1])
        with col1:
            material_title = st.text_input("素材标题", placeholder="例如：2024央视春晚小品《...》")
        with col2:
            material_type = st.selectbox("类型", ["时政新闻", "生活案例", "名言警句", "典故历史"])
            
        material_content = st.text_area("粘贴素材内容", height=200, placeholder="在这里粘贴原文...")
        
        if st.button("✨ AI 智能分析并入库", use_container_width=True):
            if not textbook_context:
                st.error("请先在 GitHub data 文件夹上传教材！")
            elif not material_content:
                st.warning("请填写内容")
            else:
                client = OpenAI(api_key=st.session_state['api_key'], base_url="https://api.deepseek.com")
                with st.spinner("AI 正在翻阅教材，为您匹配考点..."):
                    # 这是一个专门用于“打标签”的 Prompt
                    prompt = f"""
                    你是一个严谨的教材档案管理员。
                    参考教材内容：{textbook_context[:20000]}
                    
                    待分析素材：
                    标题：{material_title}
                    内容：{material_content}
                    
                    请分析该素材与高中政治教材的联系，并严格按以下格式输出（不要废话）：
                    
                    适用教材：(例如：必修1、必修3)
                    核心考点：(提取3-5个最相关的关键词，用顿号隔开)
                    适用分析：(用一句话概括这个素材适合用来说明什么原理，50字以内)
                    """
                    
                    try:
                        resp = client.chat.completions.create(
                            model="deepseek-chat",
                            messages=[{"role": "user", "content": prompt}]
                        )
                        ai_result = resp.choices[0].message.content
                        
                        # 解析 AI 返回的结果 (这里做一个简单的分割处理，实际可以更复杂)
                        # 为了演示稳定，我们直接把 AI 的整段回复存进去，或者让 AI 返回 JSON
                        # 这里简单处理，直接存
                        
                        new_data = {
                            "录入时间": datetime.now().strftime("%Y-%m-%d"),
                            "标题": material_title,
                            "类型": material_type,
                            "原文摘要": material_content[:50]+"...", # 只存前50字预览
                            "AI智能标签": ai_result, # 存入 AI 分析的全部内容
                            "完整内容": material_content
                        }
                        
                        # 存入 CSV
                        df = pd.read_csv(db_file) if os.path.exists(db_file) else pd.DataFrame(columns=["录入时间","标题","类型","原文摘要","AI智能标签","完整内容"])
                        df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
                        df.to_csv(db_file, index=False, encoding='utf-8-sig')
                        
                        st.success("✅ 已成功入库！")
                        st.markdown(f"**AI 分析结果：**\n{ai_result}")
                        
                    except Exception as e:
                        st.error(f"处理失败: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        if os.path.exists(db_file):
            df = pd.read_csv(db_file)
            
            # 搜索框
            search = st.text_input("🔍 搜索库内素材（支持标题、考点搜索）")
            if search:
                # 模糊搜索
                df = df[df.apply(lambda row: row.astype(str).str.contains(search).any(), axis=1)]
            
            # 表格展示
            st.dataframe(
                df[["录入时间", "标题", "类型", "AI智能标签"]], 
                use_container_width=True,
                height=500
            )
            
            # 下载备份
            with open(db_file, "rb") as f:
                st.download_button("📥 导出我的素材库 (Excel/CSV)", f, file_name=f"my_materials_{user_id}.csv")
        else:
            st.info("您的库还是空的，快去录入第一条素材吧！")

