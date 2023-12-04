import streamlit as st


def set_session_value(name: str, value):
    if name not in st.session_state:
        st.session_state[name] = value


def get_session_value(name: str):
    if name not in st.session_state:
        return None
    return st.session_state[name]


def rmv_session_value(name: str):
    if name in st.session_state:
        del st.session_state[name]
