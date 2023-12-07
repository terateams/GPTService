import streamlit as st


class PageSessionState:
    def __init__(self, prefix):
        self._prefix = prefix

    def initn_attr(self, key: str, default_value: object):
        if not hasattr(self, key):
            setattr(self, key, default_value)

    def __getattr__(self, key):
        if key == "_prefix":
            return self.__dict__[key]
        return st.session_state.get(f"{self._prefix}_{key}", None)

    def __setattr__(self, key, value):
        if key == "_prefix":
            self.__dict__[key] = value
        else:
            st.session_state[f"{self._prefix}_{key}"] = value

    def __delattr__(self, key):
        if key == "_prefix":
            raise AttributeError("Cannot delete _prefix attribute")
        st.session_state.pop(f"{self._prefix}_{key}", None)

    def newkey(self, key):
        return f"{self._prefix}_{key}"
