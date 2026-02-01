import streamlit as st
import pandas as pd
from openai import OpenAI
import requests
import os
from datetime import datetime

# 1. 页面配置
st.set_page_config(page_title="政治名师 AI 智库", layout="wide")

# 2. 侧边栏：配置中心
with st.sidebar:
    st.title("教研配置")
    ds_key = st.text_input("DeepSeek Key", type="password")
    j_key = st.text_input("Jina Key", type="password")
    st.divider()
    user = st.text_input("👤 识别码", placeholder="请输入名字")
    if not user:
        st.warning("请输入名字以激活")
        st.stop()
    db_path = f"db_{user}.csv"

# 3. 功能函数
def get_web_text(url, key):
    try:
        api_url = f"https://r.jina.ai/{url}"
        head = {"Authorization": f"Bearer {key}"}
        r = requests.get(api_url, headers=head, timeout=15)
        return r.text[:4000]
    except:
        return "抓取失败"

# 4. 主界面
st.title("🏛️ 政治教学素材加工平台")
t1, t2 = st.tabs(["✨ 加工中心", "🗄️ 素材库"])

with t1:
    c1, c2 = st.columns([2, 3])
    with c1:
        mode = st.radio("来源", ["手动", "链接"], horizontal=True)
        txt = ""
        if mode == "链接":
            link = st.text_input("粘贴链接")
            if st.button("🔌 获取原文"):
                res = get_web_text(link, j_key)
                st.session_state['tmp_web'] = res
            txt = st.session_state.get('tmp_web', "")
        else:
            txt = st.text_area("粘贴文字", height=200)
        
        title = st.text_input("素材标题")
        run = st.button("🚀 开始解析")

    with c2:
        if run:
            if not ds_key or not txt:
                st.error("缺少 Key 或内容")
            else:
                client = OpenAI(api_key=ds_key, base_url="https://api.deepseek.com")
                with st.spinner("AI 解析中..."):
                    p = f"你是一位思政老师。请对标高中政治教材解析：\n{txt}"
                    ans = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[{"role":"user","content":p}]
                    )
                    st.session_state['last_ai'] = ans.choices[0].message.content
        
        if 'last_ai' in st.session_state:
            st.markdown(st.session_state['last_ai'])
            # 这里的保存逻辑进行了换行处理，防止复制不全
            if st.button("📥 确认保存入库"):
                now = datetime.now().strftime("%Y-%m-%d")
                new_data = {
                    "日期": now, 
                    "标题": title if title else "未命名", 
                    "解析": st.session_state['last_ai']
                }
                df = pd.read_csv(db_path) if os.path.exists(db_path) else pd.DataFrame(columns=["日期","标题","解析"])
                df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
                df.to_csv(db_path, index=False, encoding='utf-8-sig')
                st.success("已存入库！")

with t2:
    if os.path.exists(db_path):
        lib = pd.read_csv(db_path)
        for i, row in lib.iterrows():
            with st.expander(f"📌 {row['日期']} | {row['标题']}"):
                st.write(row['解析'])
                if st.button("🗑️ 删除", key=f"del_{i}"):
                    lib.drop(i).to_csv(db_path, index=False, encoding='utf-8-sig')
                    st.rerun()
    else:
        st.info("暂无素材")
