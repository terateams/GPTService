import streamlit as st
import sys
import os
from libs.msal import msal_auth
from dotenv import load_dotenv
sys.path.append(os.path.abspath('..'))
load_dotenv()


with st.sidebar:
    value = msal_auth()

    st.write(value)
