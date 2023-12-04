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
    GPTStudio 是一个基于 GPT (Generative Pre-trained Transformer) 的工具库，
    旨在为开发者和数据科学家提供强大且易于使用的 GPT 功能。
    本工具库结合了知识库管理、GPT 能力，以及一个基于 AI 的工具集合，
    使其成为任何涉及 AI 和大模型的项目的理想选择。
    
    ## 主要特性
    
    ### 知识库检索：
    
    提供高效的检索工具，帮助用户快速找到知识库中的相关信息。
    
    ### GPT 能力测试
    - **模型能力测试**：允许用户测试GPT模型在知识库辅助下的性能和能力。
    - **实时反馈**：提供实时反馈，帮助用户了解模型的响应和准确性。
    
    ### AI 工具集合
    - **广泛的 AI 工具**：包括但不限于文本生成、语言理解、数据分析等多种 AI 相关工具。
    - **大模型支持**：支持与其他大型 AI 模型集成，扩展应用的能力和范围。

    
    """)


def main():
    """主应用"""
    show_page()


if __name__ == "__main__":
    main()
