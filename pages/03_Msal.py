import streamlit as st
from msal_streamlit_authentication import msal_authentication
import os
from dotenv import load_dotenv
load_dotenv()

MSAL_TENANTID = os.getenv("MSAL_TENANTID")
MSAL_APPID = os.getenv("MSAL_APPID")


st.session_state

if "token" in st.session_state and st.session_state["token"]:
    st.write("Token", st.session_state["token"])
else:
    value = msal_authentication(
        auth={
            "clientId": MSAL_APPID,
            "authority": f"https://login.microsoftonline.com/{MSAL_TENANTID}",
            "redirectUri": "/",
            "postLogoutRedirectUri": "/"
        },
        cache={
            "cacheLocation": "sessionStorage",
            "storeAuthStateInCookie": False
        },
        login_request={
            "scopes": [f"{MSAL_APPID}/.default"]
        },
        key=1)
    st.session_state["token"] = value


