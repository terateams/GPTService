import streamlit as st
from components.streamlit_tesseract_scanner import tesseract_scanner

img_file_buffer = st.camera_input("Take a picture")

blacklist='@*|©_Ⓡ®¢§š'
data = tesseract_scanner(showimg=True, lang='chi_sim+eng', psm=11)

if data is not None:
    st.write(data)
