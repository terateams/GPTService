import streamlit as st

# 在其他页面
if 'authenticated' not in st.session_state or not st.session_state['authenticated']:
    st.error("请先登录。")
    st.stop()  # 阻止未认证的用户访问页面内容

st.sidebar.markdown("# 知识库搜索")

st.title("知识库搜索")
st.subheader("搜索知识库内容")
st.divider()

