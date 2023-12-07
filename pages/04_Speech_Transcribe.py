import uuid

import streamlit as st
from st_audiorec import st_audiorec
from audio_recorder_streamlit import audio_recorder
from openai import OpenAI
from pydub import AudioSegment
from libs.msal import msal_auth
import io
import sys
import os
from dotenv import load_dotenv

from libs.session import PageSessionState

sys.path.append(os.path.abspath('..'))
load_dotenv()

page_state = PageSessionState("speech_transcribe")

with st.sidebar:
    value = msal_auth()
    if value is None:
        st.stop()

st.sidebar.markdown("# 🎙️语音转录🎤")

st.markdown("# 🎙️语音转录🎤")
st.markdown("> 上传文本或者录制语音识别，然后合成新的语音")

# 音频录制内容
page_state.initn_attr("audio_recode", None)
# 语音合成内容
page_state.initn_attr("speech_recode", None)
# 是否正在处理中
page_state.initn_attr("audio_processing", False)

# 用于存储临时文件
data_dir = os.getenv("DATA_DIR", "/tmp/data")
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

content_box = st.empty()

uploaded_file = st.sidebar.file_uploader("上传文本文件", type=["txt", "md"])
if uploaded_file is not None:
    stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8"))
    string_data = stringio.read()
    page_state.audio_recode = string_data

if st.sidebar.button("录制音频"):
    page_state.audio_recode = None
    page_state.audio_processing = False
    page_state.speech_recode = None
    content_box.empty()
    st.rerun()

if page_state.audio_recode is None:
    with st.spinner('正在识别语音...'):
        wav_audio_recode = audio_recorder("点击录音", icon_size="2x", pause_threshold=3.0)
        if wav_audio_recode is not None:
            st.audio(wav_audio_recode, format="audio/wav")
            audio_segment = AudioSegment.from_wav(io.BytesIO(wav_audio_recode))
            filename = os.path.join(data_dir, f"{uuid.uuid4()}.audio.wav")
            audio_segment.export(filename, format="wav")
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                response_format="json",
                file=open(filename, "rb"),
            )
            page_state.audio_recode = transcript.text
            st.rerun()

if page_state.audio_recode is not None:
    content_box.markdown(page_state.audio_recode)
    sound = st.selectbox("选择音色", ["alloy", "echo", "fable", "onyx", "nova", "shimmer"])
    c1, c2, c3 = st.columns(3)
    if c1.button("合成语音"):
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        speech_file_path = os.path.join(data_dir, f"{uuid.uuid4()}.speech.mp3")
        with st.status("正在合成语音", expanded=True) as status:
            response = client.audio.speech.create(
                model="tts-1",
                voice=sound,
                input=page_state.audio_recode
            )
            page_state.speech_recode = response.read()
            st.write(f"🎧{sound}音色")
            st.audio(page_state.speech_recode, format="audio/mp3")
            st.write(f"语音{sound}合成完成")
            status.update(label="语音合成完成!", state="complete")

    if page_state.speech_recode is not None:
        c3.download_button(
            label="下载语音",
            data=page_state.speech_recode,
            file_name='speech.mp3',
        )
else:
    if page_state.audio_processing:
        st.write("还有任务在处理")
