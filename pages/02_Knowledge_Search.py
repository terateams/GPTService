import streamlit as st
import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.abspath('..'))
load_dotenv()
from libs.http import search_knowledge
from libs.msal import msal_auth

if os.getenv("DEV_MODE") not in ["true", "1", "on"]:
    value = msal_auth()
    if value is None:
        st.stop()

knowledges = {
    "青少年编程": "codeboy",
    "对数课堂": "logbot",
}

st.sidebar.markdown("# 知识库搜索")

st.title("知识库搜索")
st.divider()

if "messages" not in st.session_state.keys():
    st.session_state.messages = [{"role": "assistant", "content": "欢迎使用知识库检索， 请输入主题"}]

collection = st.selectbox("选择知识库", knowledges.keys())
collection_value = knowledges[collection]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])


def clear_chat_history():
    st.session_state.messages = [{"role": "assistant", "content": "欢迎使用知识库检索，请输入主题"}]


st.sidebar.button('清除历史', on_click=clear_chat_history)

if prompt := st.chat_input("输入检索主题"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

if st.session_state.messages[-1]["role"] != "assistant":
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = search_knowledge(collection_value, prompt)
            if response is None:
                response = "没有找到相关知识"
            st.markdown(response)
    message = {"role": "assistant", "content": response}
    st.session_state.messages.append(message)
