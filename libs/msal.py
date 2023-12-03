from msal_streamlit_authentication import msal_authentication
import os


def msal_auth():
    tenant_id = os.getenv("MSAL_TENANTID")
    app_id = os.getenv("MSAL_APPID")
    return msal_authentication(
        auth={
            "clientId": app_id,
            "authority": f"https://login.microsoftonline.com/{tenant_id}",
            "redirectUri": "/",
            "postLogoutRedirectUri": "/"
        },
        cache={
            "cacheLocation": "sessionStorage",
            "storeAuthStateInCookie": False
        },
        login_button_text="Microsoft Account Login",
        login_request={
            "scopes": [f"{app_id}/.default"]
        },
        key="msal_token"
    )
