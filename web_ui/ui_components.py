"""UI components for Streamlit web interface."""

import streamlit as st
from typing import Dict, Any, Optional
from web_ui.config import ConfigManager, ValidationResult


class UIComponents:
    """Reusable UI components for the web interface."""
    
    @staticmethod
    def render_sidebar(config: ConfigManager) -> None:
        """Render the sidebar with configuration information."""
        st.sidebar.header("Configuration")
        
        # Show current configuration
        display_config = config.get_display_config()
        
        st.sidebar.subheader("Current Settings")
        for key, value in display_config.items():
            st.sidebar.text(f"{key}: {value}")
        
        # Configuration help
        st.sidebar.subheader("Setup Help")
        st.sidebar.info("""
        **Required Environment Variables:**
        - `OPENAI_API_BASE`: Ollama URL  
        - `OPENAI_API_KEY`: API key (e.g., "ollama")
        - `KBG_OLLAMA_MODEL`: Model name (e.g., "llama3")
        
        **Optional:**
        - `KBG_LLM_PROVIDER`: Provider (default: "ollama")
        - `KBG_LLM_TEMPERATURE`: Temperature (default: 0.1)
        """)
        
        # Validation status
        st.sidebar.subheader("Status")
        validation_result = config.validate()
        UIComponents._render_validation_status(validation_result)
    
    @staticmethod
    def _render_validation_status(validation_result: ValidationResult) -> None:
        """Render configuration validation status."""
        if validation_result.is_valid:
            st.sidebar.success("✅ Configuration is valid")
        else:
            st.sidebar.error("❌ Configuration issues found")
            
            if validation_result.missing_vars:
                st.sidebar.error(f"Missing: {', '.join(validation_result.missing_vars)}")
            
            if validation_result.errors:
                for error in validation_result.errors:
                    st.sidebar.error(f"Error: {error}")
    
    @staticmethod
    def render_chat_interface() -> Optional[str]:
        """Render the chat interface and return user input."""
        # Mode selection
        mode = st.radio(
            "Select Mode:",
            ("Chat", "Code Assistant"),
            horizontal=True,
            key="mode_selection"
        )
        
        # Store mode in session state for use in processing
        st.session_state.current_mode = mode
        
        # Chat input
        user_prompt = st.chat_input("Enter your message here...")
        
        return user_prompt
    
    @staticmethod
    def render_chat_history() -> None:
        """Render the chat history from session state."""
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    
    @staticmethod
    def add_message_to_history(role: str, content: str) -> None:
        """Add a message to the chat history."""
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        st.session_state.messages.append({
            "role": role,
            "content": content
        })
    
    @staticmethod
    def create_streaming_placeholder():
        """Create a placeholder for streaming responses."""
        return st.empty()
    
    @staticmethod
    def update_streaming_placeholder(placeholder, content: str, is_complete: bool = False) -> None:
        """Update streaming placeholder with content."""
        if is_complete:
            placeholder.markdown(content)
        else:
            placeholder.markdown(content + "▌")
    
    @staticmethod
    def render_error_message(error_message: str) -> None:
        """Render an error message."""
        st.error(error_message)
    
    @staticmethod
    def clear_chat_history() -> None:
        """Clear the chat history."""
        if "messages" in st.session_state:
            st.session_state.messages = []
        st.rerun()