"""Main Streamlit application for Kebogyro LLM Assistant."""

import streamlit as st
import asyncio
import sys
from pathlib import Path

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import application components
from web_ui.config import ConfigManager, ConfigValidationError
from web_ui.core_logic import process_chat_prompt, process_code_assistance_prompt
from web_ui.ui_components import UIComponents
from web_ui.error_handler import ErrorHandler

async def handle_user_input(user_prompt: str, config: ConfigManager) -> None:
    """Handle user input and stream response."""
    error_handler = ErrorHandler()
    
    # Add user message to history
    UIComponents.add_message_to_history("user", user_prompt)
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(user_prompt)
    
    # Process and display assistant response
    with st.chat_message("assistant"):
        response_placeholder = UIComponents.create_streaming_placeholder()
        full_response = ""
        
        try:
            # Get current mode
            mode = getattr(st.session_state, 'current_mode', 'Chat')
            
            # Choose appropriate processor
            if mode == "Chat":
                processor = process_chat_prompt(user_prompt, config)
            else:  # Code Assistant
                processor = process_code_assistance_prompt(user_prompt, config)
            
            # Stream response
            async for chunk in processor:
                if chunk:
                    full_response += chunk
                    UIComponents.update_streaming_placeholder(
                        response_placeholder, 
                        full_response, 
                        is_complete=False
                    )
            
            # Finalize response
            UIComponents.update_streaming_placeholder(
                response_placeholder, 
                full_response, 
                is_complete=True
            )
            
            # Add to history
            UIComponents.add_message_to_history("assistant", full_response)
            
        except Exception as e:
            error_response = error_handler.handle_generic_error(e)
            error_message = error_handler.format_error_for_ui(error_response)
            UIComponents.render_error_message(error_message)
            UIComponents.add_message_to_history("assistant", error_message)


def main():
    """Main application entry point."""
    st.set_page_config(
        page_title="Kebogyro LLM Assistant",
        page_icon="🧙‍♂️",
        layout="wide"
    )
    
    st.title("🧙‍♂️ Kebogyro LLM Assistant")
    
    # Initialize configuration
    try:
        config = ConfigManager.load_from_env_file()
    except ConfigValidationError as e:
        st.error(f"Configuration error: {e}")
        st.stop()
    
    # Render sidebar
    UIComponents.render_sidebar(config)
    
    # Check if configuration is valid
    validation_result = config.validate()
    if not validation_result.is_valid:
        st.warning("Please fix configuration issues before proceeding.")
        return
    
    # Render chat interface
    UIComponents.render_chat_history()
    user_prompt = UIComponents.render_chat_interface()
    
    # Process user input
    if user_prompt:
        asyncio.run(handle_user_input(user_prompt, config))
    
    # Add clear chat button
    if st.sidebar.button("Clear Chat History"):
        UIComponents.clear_chat_history()


if __name__ == "__main__":
    main()
