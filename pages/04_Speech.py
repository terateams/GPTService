import uuid

import streamlit as st
from st_audiorec import st_audiorec
from openai import OpenAI
from pydub import AudioSegment
from libs.msal import msal_auth
import io
import sys
import os
from dotenv import load_dotenv

sys.path.append(os.path.abspath('..'))
load_dotenv()

with st.sidebar:
    value = msal_auth()
    if value is None:
        st.stop()


st.markdown("# 🎙️语音转录🎤")
st.markdown("> 上传文本或者录制语音识别，然后合成新的语音")

if "audio_recode" not in st.session_state:
    st.session_state.audio_recode = None

if "speech_recode" not in st.session_state:
    st.session_state.speech_recode = None

if "audio_processing" not in st.session_state:
    st.session_state.audio_processing = False

data_dir = os.getenv("DATA_DIR", "/tmp/data")
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

uploaded_file = st.file_uploader("上传文本文件", type=["txt", "md"])
if uploaded_file is not None:
    stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8"))
    string_data = stringio.read()
    st.session_state.audio_recode = string_data

if st.session_state.audio_recode is None:
    wav_audio_recode = st_audiorec()
    if wav_audio_recode is not None:
        with st.spinner('正在识别语音...', cache=True):
            audio_segment = AudioSegment.from_wav(io.BytesIO(wav_audio_recode))
            filename = os.path.join(data_dir, f"{uuid.uuid4()}.audio.wav")
            audio_segment.export(filename, format="wav")
            client = OpenAI()
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                response_format="json",
                file=open(filename, "rb"),
            )
            st.session_state.audio_recode = transcript.text
            st.rerun()

if st.session_state.audio_recode is not None:
    st.markdown("### 🎤语音合成")
    st.markdown(st.session_state.audio_recode)
    sound = st.selectbox("选择音色", ["alloy", "echo", "fable", "onyx", "nova", "shimmer"])
    c1, c2, c3 = st.columns(3)
    if c1.button("合成语音"):
        client = OpenAI()
        speech_file_path = os.path.join(data_dir, f"{uuid.uuid4()}.speech.mp3")
        with st.status("正在合成语音", expanded=True) as status:
            response = client.audio.speech.create(
                model="tts-1",
                voice=sound,
                input=st.session_state.audio_recode
            )
            st.session_state.speech_recode = response.read()
            st.write(f"🎧{sound}音色")
            st.audio(st.session_state.speech_recode, format="audio/mp3")
            st.write(f"语音{sound}合成完成")
            status.update(label="语音合成完成!", state="complete")

    if c2.button("重新录制"):
        st.session_state.audio_recode = None
        st.session_state.audio_processing = False
        st.session_state.speech_recode = None
        st.rerun()

    if st.session_state.speech_recode is not None:
        c3.download_button(
            label="下载语音",
            data=st.session_state.speech_recode,
            file_name='speech.mp3',
        )
else:
    if st.session_state.audio_processing:
        st.write("还有任务在处理")
