import streamlit as st
import sys
import os
from dotenv import load_dotenv
from libs.knowledge import knowledge_dictionary, search_knowledge
from libs.prompts import get_ta365_sysmsg
from libs.msal import msal_auth
from libs.llms import openai_streaming

sys.path.append(os.path.abspath('..'))
load_dotenv()

with st.sidebar:
    value = msal_auth()
    if value is None:
        st.stop()

st.sidebar.markdown("# 💡Ta365 AI 助手")

st.title("💡Ta365 AI 助手")
st.markdown("> 一个通用型人工智能助手，可以帮助你解决各种问题。")
st.divider()

if "ta365_messages" not in st.session_state.keys():
    st.session_state.ta365_messages = [{"role": "assistant", "content": "我是 Ta365 AI 助手，欢迎提问"}]

if "ta365_last_user_msg_processed" not in st.session_state:
    st.session_state.ta365_last_user_msg_processed = True

if "ta365_streaming_end" not in st.session_state:
    st.session_state.ta365_streaming_end = True


def stop_streaming():
    """当停止按钮被点击时执行，用于修改处理标志"""
    st.session_state.ta365_streaming_end = True
    st.session_state.ta365_last_user_msg_processed = True


collection = st.selectbox("选择知识库", knowledge_dictionary.keys())
collection_value = knowledge_dictionary[collection]

for ta365_messages in st.session_state.ta365_messages:
    with st.chat_message(ta365_messages["role"]):
        st.write(ta365_messages["content"])


def clear_chat_history():
    st.session_state.ta365_messages = [{"role": "assistant", "content": "我是 Ta365 AI 助手，欢迎提问"}]


st.sidebar.button('清除历史', on_click=clear_chat_history)


# 用户输入
if prompt := st.chat_input("输入你的问题"):
    # 用于标记用户消息还没有处理
    st.session_state.ta365_streaming_end = False
    st.session_state.ta365_last_user_msg_processed = False
    st.session_state.ta365_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

stop_action = st.sidebar.empty()

if not st.session_state.ta365_streaming_end:
    stop_action.button('停止输出', on_click=stop_streaming, help="点击此按钮停止流式输出")

# 用户输入响应，如果上一条消息不是助手的消息，且上一条用户消息还没有处理完毕
if (st.session_state.ta365_messages[-1]["role"] != "assistant"
        and not st.session_state.ta365_last_user_msg_processed):
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # 检索知识库
            kmsg = ""
            if collection_value not in "":
                kmsg = search_knowledge(collection_value, prompt)
            sysmsg = get_ta365_sysmsg(kmsg)
            response = openai_streaming(sysmsg, st.session_state.ta365_messages[-10:])
            # 流式输出
            placeholder = st.empty()
            full_response = ''
            for item in response:
                # 如果用户手动停止了流式输出，就退出循环
                if st.session_state.ta365_streaming_end:
                    break
                text = item.content
                if text is not None:
                    full_response += text
                    placeholder.markdown(full_response)
            placeholder.markdown(full_response)
            if kmsg != "":
                st.expander("知识库检索结果", expanded=False).markdown(kmsg)

    stop_action.empty()
    # 用于标记流式输出已经结束
    st.session_state.ta365_streaming_end = True
    # 用于标记上一条用户消息已经处理完毕
    st.session_state.ta365_last_user_msg_processed = True
    message = {"role": "assistant", "content": full_response}
    st.session_state.ta365_messages.append(message)

