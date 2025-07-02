import streamlit as st

def main():
import streamlit as st
import asyncio
import os

# Import core logic functions
from core_logic import process_chat_prompt, process_code_assistance_prompt

def main():
    st.title("🧙‍♂️ Kebogyro LLM Assistant")

    st.sidebar.header("Konfigurasi")
    st.sidebar.markdown("""
    Pastikan environment variable berikut sudah di-set untuk koneksi ke Ollama:
    - `OPENAI_API_BASE`: URL ke Ollama (e.g., `http://localhost:11434/v1`)
    - `OPENAI_API_KEY`: (e.g., `ollama`)
    - `KBG_OLLAMA_MODEL`: Nama model di Ollama (e.g., `llama3`)
    - `KBG_LLM_PROVIDER`: (e.g., `ollama`)
    - `KBG_LLM_TEMPERATURE`: (e.g., `0.1`)
    """)

    st.sidebar.text_input("OPENAI_API_BASE (Ollama URL)", value=os.getenv("OPENAI_API_BASE", "http://localhost:11434/v1"), key="env_ollama_url", type="default", disabled=True)
    st.sidebar.text_input("KBG_OLLAMA_MODEL", value=os.getenv("KBG_OLLAMA_MODEL", "llama3"), key="env_ollama_model", type="default", disabled=True)


    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"]) # Use markdown for better formatting of code

    # Mode selection
    mode = st.radio(
        "Pilih mode:",
        ("Chat Biasa", "Bantuan Kode"),
        horizontal=True,
        key="mode_selection"
    )

    # Input area for user prompt
    user_prompt = st.chat_input("Ketik prompt Anda di sini...")

    if user_prompt:
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        # Display user message in chat message container
        with st.chat_message("user"):
            st.markdown(user_prompt)

        # Display assistant response in chat message container
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""

            try:
                if st.session_state.mode_selection == "Chat Biasa":
                    async def stream_chat_response():
                        nonlocal full_response
                        async for chunk in process_chat_prompt(user_prompt):
                            full_response += chunk
                            response_placeholder.markdown(full_response + "▌")
                        response_placeholder.markdown(full_response)

                    # Run the async function
                    # Streamlit's main execution is not async, so we use asyncio.run()
                    # or handle it appropriately if running in an async context already (less common for basic streamlit)
                    # For simplicity in typical Streamlit setup:
                    asyncio.run(stream_chat_response())

                elif st.session_state.mode_selection == "Bantuan Kode":
                    async def stream_code_assist_response():
                        nonlocal full_response
                        async for chunk in process_code_assistance_prompt(user_prompt):
                            full_response += chunk
                            response_placeholder.markdown(full_response + "▌")
                        response_placeholder.markdown(full_response)

                    asyncio.run(stream_code_assist_response())

                st.session_state.messages.append({"role": "assistant", "content": full_response})

            except Exception as e:
                error_message = f"Terjadi kesalahan: {str(e)}"
                response_placeholder.error(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})


if __name__ == "__main__":
    # Note: To run this Streamlit app, you typically use `streamlit run web_ui/app.py` from the project root.
    # Ensure that `web_ui` is in PYTHONPATH or run from a context where `core_logic` is importable.
    # One way is to run `streamlit run app.py` from within the `web_ui` directory,
    # or adjust PYTHONPATH if running from project root.
    # For simplicity of `from core_logic import ...`, this file assumes it can directly import `core_logic`.
    # If running `streamlit run web_ui/app.py` from project root, Python might not find `core_logic`
    # unless `web_ui` is added to sys.path or `kebogyro_project` is structured as a package recognized by Streamlit.

    # A common practice if `web_ui` is a sub-package:
    # In project root: `python -m streamlit run web_ui.app` (if app.py can be run as a module)
    # Or, ensure PYTHONPATH includes the project root.
    main()
