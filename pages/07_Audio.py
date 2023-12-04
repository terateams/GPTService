import streamlit as st
from audio_recorder_streamlit import audio_recorder

audio_bytes = audio_recorder("", icon_size="1x", pause_threshold=3.0)
if audio_bytes:
    st.audio(audio_bytes, format="audio/wav")
