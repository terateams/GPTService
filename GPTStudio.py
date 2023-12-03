import streamlit as st


def sidebar():
    st.sidebar.markdown("""
# 🦜GPTStudio
- [GPTStudio Github](https://github.com/terateams/GPTService)
- [Streamlit Website](https://streamlit.io)
    """)
    if st.sidebar.button('登出'):
        st.session_state['authenticated'] = False
        st.rerun()


def show_page():
    sidebar()
    st.title("🦜GPTStudio")
    st.markdown("""
    GPTStudio 是一个基于 GPT (Generative Pre-trained Transformer) 的工具库，旨在为开发者和数据科学家提供强大且易于使用的 GPT 功能。本工具库结合了知识库管理、GPT 测试能力，以及一个基于 AI 的工具集合，使其成为任何涉及 AI 和大模型的项目的理想选择。
    
    ## 主要特性
    
    ### 管理知识库
    - **知识库上传和维护**：用户可以轻松上传和维护自己的知识库，使 GPT 模型能够访问和利用这些专门的知识。
    - **知识库检索**：提供高效的检索工具，帮助用户快速找到知识库中的相关信息。
    
    ### GPT 测试
    - **模型能力测试**：允许用户测试GPT模型在知识库辅助下的性能和能力。
    - **实时反馈**：提供实时反馈，帮助用户了解模型的响应和准确性。
    
    ### AI 工具集合
    - **广泛的 AI 工具**：包括但不限于文本生成、语言理解、数据分析等多种 AI 相关工具。
    - **大模型支持**：支持与其他大型 AI 模型集成，扩展应用的能力和范围。
    
    ### 基于 Streamlit 的应用实现
    - **直观的界面**：利用 Streamlit 创建的用户界面，直观易用，无需编程经验即可操作。
    - **快速部署**：快速部署 AI 应用，便于展示和共享结果。
    
    ## 贡献
    
    我们欢迎各种形式的贡献，包括但不限于新功能的建议、代码改进、文档补充等。请阅读我们的贡献指南来了解如何开始贡献。
    
    ## 许可证
    
    GPTStudio 是在 MIT 许可证下发布的。有关详细信息，请参阅 [LICENSE](LICENSE) 文件。
    
    ---
    
    """)


# 假设这是从数据库或环境变量中获取的用户凭据
VALID_USERNAME = "admin"
VALID_PASSWORD = "password"


def verify_credentials(username, password):
    """验证用户名和密码"""
    return username == VALID_USERNAME and password == VALID_PASSWORD


def show_login_page():
    """显示登录界面"""
    st.title("登录")
    username = st.text_input("用户名")
    password = st.text_input("密码", type='password')
    if st.button('登录'):
        if verify_credentials(username, password):
            st.session_state['authenticated'] = True
            st.success("登录成功！")
            st.rerun()
        else:
            st.error("登录失败，请检查你的用户名和密码。")


def main():
    """主应用"""
    if 'authenticated' not in st.session_state:
        st.session_state['authenticated'] = False

    if st.session_state['authenticated']:
        show_page()
    else:
        show_login_page()


if __name__ == "__main__":
    main()
