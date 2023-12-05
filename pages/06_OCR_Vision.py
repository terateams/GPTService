import streamlit as st
from libs.llms import openai_analyze_image, openai_streaming
from libs.msal import msal_auth

with st.sidebar:
    value = msal_auth()
    if value is None:
        st.stop()

if "ocr_vision_messages" not in st.session_state.keys():
    st.session_state.ocr_vision_messages = []

if "ocr_vision_last_user_msg_processed" not in st.session_state:
    st.session_state.ocr_vision_last_user_msg_processed = True

if "ocr_vision_analysis_result" not in st.session_state:
    st.session_state.ocr_vision_analysis_result = ""

st.sidebar.markdown("# 🔬视觉分析")

st.title("🔬视觉分析")


def clear_result():
    st.session_state.ocr_vision_analysis_result = ""
    st.session_state.ocr_vision_last_user_msg_processed = True
    st.session_state.ocr_vision_messages = []


def save_result():
    st.session_state.ocr_vision_analysis_result = st.session_state.ocr_vision_analysis_result_temp


# Streamlit 应用的主要部分
col1, col2, = st.columns([3, 6])

# 摄像头输入获取图片
image = col1.camera_input("点击按钮截图", on_change=clear_result)

# 图像分析提示输入
prompt = col2.text_input("图像分析提示", "识别分析图片内容")

# 重新获取图像时触发图像分析
if image is not None and not st.session_state.ocr_vision_analysis_result:
    with col2:
        with st.spinner("分析中..."):
            st.session_state.ocr_vision_analysis_result = openai_analyze_image(prompt, image)

# 使用文本区域组件显示分析结果， 支持手工修改
if st.session_state.ocr_vision_analysis_result:
    with col2:
        st.text_area("识别结果(请手工修正识别错误)",
                     value=st.session_state.ocr_vision_analysis_result,
                     key="ocr_vision_analysis_result_temp",
                     on_change=save_result,
                     height=170)


for ocr_vision_messages in st.session_state.ocr_vision_messages:
    with st.chat_message(ocr_vision_messages["role"]):
        st.write(ocr_vision_messages["content"])

if uprompt := st.chat_input("输入你的问题"):
    # 用于标记用户消息还没有处理
    st.session_state.ocr_vision_last_user_msg_processed = False
    st.session_state.ocr_vision_messages.append({"role": "user", "content": uprompt})
    with st.chat_message("user"):
        st.write(uprompt)

# 用户输入响应，如果上一条消息不是助手的消息，且上一条用户消息还没有处理完毕
if ((st.session_state.ocr_vision_messages and
     st.session_state.ocr_vision_messages[-1]["role"] != "assistant" and
     not st.session_state.ocr_vision_last_user_msg_processed) and
        st.session_state.ocr_vision_analysis_result not in [""]):
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            sysmsg = f""""
            以下是来自一图片识别获取的内容结果：
            '''
            {st.session_state.ocr_vision_analysis_result}
            '''
            我们将围绕这个内容进行深入讨论。
            """
            response = openai_streaming(sysmsg, st.session_state.ocr_vision_messages[-10:])
            # 流式输出
            placeholder = st.empty()
            full_response = ''
            for item in response:
                text = item.content
                if text is not None:
                    full_response += text
                    placeholder.markdown(full_response)
            placeholder.markdown(full_response)

    # 用于标记上一条用户消息已经处理完毕
    st.session_state.ocr_vision_last_user_msg_processed = True
    # 追加对话记录
    message = {"role": "assistant", "content": full_response}
    st.session_state.ocr_vision_messages.append(message)
