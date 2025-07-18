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
from web_ui.core_logic import (
    process_chat_prompt, process_code_assistance_prompt,
    process_chat_prompt_with_debug, process_code_assistance_prompt_with_debug,
    DebugInfo
)
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
    
    # Check if debug mode is enabled
    debug_enabled = getattr(st.session_state, 'debug_enabled', False)
    show_raw_llm = getattr(st.session_state, 'show_raw_llm', False)
    show_processed = getattr(st.session_state, 'show_processed', False)
    show_timing = getattr(st.session_state, 'show_timing', False)
    
    # Initialize debug info if needed
    debug_info = DebugInfo() if debug_enabled else None
    
    # Process and display assistant response
    with st.chat_message("assistant"):
        response_placeholder = UIComponents.create_streaming_placeholder()
        full_response = ""
        
        try:
            # Get current mode
            mode = getattr(st.session_state, 'current_mode', 'Chat')
            
            # Choose appropriate processor based on debug mode
            if debug_enabled:
                if mode == "Chat":
                    processor = process_chat_prompt_with_debug(user_prompt, config, debug_info)
                else:  # Code Assistant
                    processor = process_code_assistance_prompt_with_debug(user_prompt, config, debug_info)
            else:
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
            
            # Finalize response with copy button
            UIComponents.finalize_streaming_response(
                response_placeholder, 
                full_response
            )
            
            # Add to history
            UIComponents.add_message_to_history("assistant", full_response)
            
            # Display debug information if enabled
            if debug_enabled and debug_info:
                UIComponents.render_debug_information(
                    debug_info, 
                    show_raw_llm, 
                    show_processed, 
                    show_timing
                )
            
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
    
    # Check if configuration is valid (with caching)
    # Use session state to avoid repeated validation calls
    config_hash = config._get_config_hash()
    if "validation_result" not in st.session_state or st.session_state.get("config_hash") != config_hash:
        validation_result = config.validate()
        st.session_state.validation_result = validation_result
        st.session_state.config_hash = config_hash
    else:
        validation_result = st.session_state.validation_result
    
    # Render sidebar with validation result
    UIComponents.render_sidebar(config, validation_result)
    
    if not validation_result.is_valid:
        st.warning("Please fix configuration issues before proceeding.")
        return
    
    # Render chat interface
    UIComponents.render_chat_history()
    user_prompt = UIComponents.render_chat_interface()
    
    # Process user input
    if user_prompt:
        asyncio.run(handle_user_input(user_prompt, config))


if __name__ == "__main__":
    main()
