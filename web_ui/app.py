import streamlit as st
import asyncio
import os
import sys
from pathlib import Path

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Try to load .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = project_root / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv not installed, that's okay

# Import core logic functions
from web_ui.core_logic import process_chat_prompt, process_code_assistance_prompt

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
    
    **Cara set environment variables:**
    ```bash
    export OPENAI_API_BASE="http://localhost:11434/v1"
    export OPENAI_API_KEY="ollama"
    export KBG_OLLAMA_MODEL="llama3"
    export KBG_LLM_PROVIDER="ollama"
    export KBG_LLM_TEMPERATURE="0.1"
    ```
    
    Atau buat file `.env` di project root.
    """)

    st.sidebar.text_input("OPENAI_API_BASE (Ollama URL)", value=os.getenv("OPENAI_API_BASE", "http://localhost:11434/v1"), key="env_ollama_url", type="default", disabled=True)
    st.sidebar.text_input("KBG_OLLAMA_MODEL", value=os.getenv("KBG_OLLAMA_MODEL", "llama3"), key="env_ollama_model", type="default", disabled=True)
    st.sidebar.text_input("OPENAI_API_KEY", value=os.getenv("OPENAI_API_KEY", "ollama"), key="env_api_key", type="password", disabled=True)
    st.sidebar.text_input("KBG_LLM_PROVIDER", value=os.getenv("KBG_LLM_PROVIDER", "ollama"), key="env_provider", type="default", disabled=True)
    st.sidebar.text_input("KBG_LLM_TEMPERATURE", value=os.getenv("KBG_LLM_TEMPERATURE", "0.1"), key="env_temperature", type="default", disabled=True)
    
    # Status check
    st.sidebar.subheader("Status")
    required_vars = ['OPENAI_API_BASE', 'OPENAI_API_KEY', 'KBG_OLLAMA_MODEL']
    all_set = all(os.getenv(var) for var in required_vars)
    if all_set:
        st.sidebar.success("✅ Environment variables configured")
    else:
        missing = [var for var in required_vars if not os.getenv(var)]
        st.sidebar.error(f"❌ Missing: {', '.join(missing)}")


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
                # Check environment variables
                missing_vars = []
                required_vars = ['OPENAI_API_BASE', 'OPENAI_API_KEY', 'KBG_OLLAMA_MODEL']
                for var in required_vars:
                    if not os.getenv(var):
                        missing_vars.append(var)
                
                if missing_vars:
                    error_message = f"Environment variables tidak ditemukan: {', '.join(missing_vars)}"
                    response_placeholder.error(error_message)
                    st.session_state.messages.append({"role": "assistant", "content": error_message})
                else:
                    if st.session_state.mode_selection == "Chat Biasa":
                        async def stream_chat_response():
                            nonlocal full_response
                            try:
                                async for chunk in process_chat_prompt(user_prompt):
                                    if chunk:
                                        full_response += chunk
                                        response_placeholder.markdown(full_response + "▌")
                                response_placeholder.markdown(full_response)
                            except Exception as e:
                                error_msg = f"Error dalam streaming chat: {str(e)}"
                                response_placeholder.error(error_msg)
                                raise e

                        asyncio.run(stream_chat_response())

                    elif st.session_state.mode_selection == "Bantuan Kode":
                        async def stream_code_assist_response():
                            nonlocal full_response
                            try:
                                async for chunk in process_code_assistance_prompt(user_prompt):
                                    if chunk:
                                        full_response += chunk
                                        response_placeholder.markdown(full_response + "▌")
                                response_placeholder.markdown(full_response)
                            except Exception as e:
                                error_msg = f"Error dalam streaming code assist: {str(e)}"
                                response_placeholder.error(error_msg)
                                raise e

                        asyncio.run(stream_code_assist_response())

                    st.session_state.messages.append({"role": "assistant", "content": full_response})

            except Exception as e:
                import traceback
                error_message = f"Terjadi kesalahan: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
                response_placeholder.error(error_message)
                st.session_state.messages.append({"role": "assistant", "content": f"Error: {str(e)}"})


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
