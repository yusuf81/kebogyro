"""UI components for Streamlit web interface."""

import streamlit as st
import logging
from typing import Dict, Any, Optional
from web_ui.config import ConfigManager, ValidationResult, ConfigValidationResult


class UIComponents:
    """Reusable UI components for the web interface."""
    
    @staticmethod
    def render_sidebar(config: ConfigManager, validation_result=None) -> None:
        """Render the sidebar with mode selection, debug options, and configuration information."""
        # Mode selection in sidebar
        st.sidebar.header("Mode Selection")
        mode = st.sidebar.radio(
            "Select Mode:",
            ("Chat", "Code Assistant"),
            key="mode_selection",
            help="Chat: Normal conversation mode\nCode Assistant: Code generation with tool support"
        )
        
        # Store mode in session state for use in processing
        st.session_state.current_mode = mode
        
        # Debug options in sidebar
        st.sidebar.header("Debug Options")
        debug_enabled = st.sidebar.checkbox(
            "Enable Debug Mode", 
            value=getattr(st.session_state, 'debug_enabled', False),
            help="Show raw LLM output and processed output for troubleshooting"
        )
        st.session_state.debug_enabled = debug_enabled
        
        if debug_enabled:
            show_raw_llm = st.sidebar.checkbox(
                "Show Raw LLM Output", 
                value=getattr(st.session_state, 'show_raw_llm', False),
                help="Display the unprocessed output directly from the LLM"
            )
            show_processed = st.sidebar.checkbox(
                "Show Processing Steps", 
                value=getattr(st.session_state, 'show_processed', False),
                help="Display how the raw output gets processed through ContentBuffer"
            )
            show_timing = st.sidebar.checkbox(
                "Show Timing Info", 
                value=getattr(st.session_state, 'show_timing', False),
                help="Display timing information for each chunk"
            )
            
            st.session_state.show_raw_llm = show_raw_llm
            st.session_state.show_processed = show_processed
            st.session_state.show_timing = show_timing
        
        # Configuration section
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
        if validation_result is None:
            validation_result = config.validate()
        UIComponents._render_validation_status(validation_result)
        
        # Add some spacing
        st.sidebar.markdown("---")
        
        # Clear chat button
        if st.sidebar.button("🗑️ Clear Chat History", use_container_width=True):
            UIComponents.clear_chat_history()
        
        # Add helpful info at the bottom
        st.sidebar.markdown("---")
        st.sidebar.markdown("""
        **💡 Tips:**
        - **Chat Mode**: Normal conversation
        - **Code Assistant**: Generates code with explanations
        - **Debug Mode**: Shows processing details
        """)
        st.sidebar.markdown("*Made with ❤️ using Kebogyro*")
    
    @staticmethod
    def _render_validation_status(validation_result) -> None:
        """Render configuration validation status."""
        if validation_result.is_valid:
            st.sidebar.success("✅ Configuration is valid")
        else:
            st.sidebar.error("❌ Configuration issues found")
            
            if hasattr(validation_result, 'missing_vars') and validation_result.missing_vars:
                st.sidebar.error(f"Missing: {', '.join(validation_result.missing_vars)}")
            
            if hasattr(validation_result, 'errors') and validation_result.errors:
                for error in validation_result.errors:
                    st.sidebar.error(f"Error: {error}")
    
    @staticmethod
    def render_chat_interface() -> Optional[str]:
        """Render the chat interface and return user input."""
        # Show current mode indicator
        current_mode = getattr(st.session_state, 'current_mode', 'Chat')
        debug_enabled = getattr(st.session_state, 'debug_enabled', False)
        
        # Create a subtle indicator
        mode_color = "🟢" if current_mode == "Chat" else "🔧"
        debug_indicator = " 🔍" if debug_enabled else ""
        
        st.markdown(f"""
        <div style="text-align: center; margin-bottom: 10px; color: #666;">
            {mode_color} <strong>{current_mode} Mode</strong>{debug_indicator}
        </div>
        """, unsafe_allow_html=True)
        
        # Chat input (mode selection and debug options are now in sidebar)
        placeholder_text = "Ask me anything..." if current_mode == "Chat" else "Describe the code you need..."
        user_prompt = st.chat_input(placeholder_text)
        
        return user_prompt
    
    @staticmethod
    def render_chat_history() -> None:
        """Render the chat history from session state."""
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        for i, message in enumerate(st.session_state.messages):
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
                # Add copy functionality for assistant messages
                if message["role"] == "assistant":
                    with st.expander("📋 Copy", expanded=False):
                        st.text_area(
                            label="Copy content",
                            value=message["content"],
                            height=100,
                            key=f"history_copy_{i}_{hash(message['content'])}",
                            help="Select all (Ctrl+A) and copy (Ctrl+C)",
                            label_visibility="collapsed"
                        )
    
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
    def finalize_streaming_response(placeholder, content: str) -> None:
        """Finalize streaming response and add copy functionality."""
        # Clear the placeholder
        placeholder.empty()
        
        # Display the main content
        st.markdown(content)
        
        # Add copy functionality in an expander
        with st.expander("📋 Copy Response", expanded=False):
            st.write("Select all text below and copy (Ctrl+A, Ctrl+C):")
            # Use text_area for easy copying - readonly style
            st.text_area(
                label="Response Content",
                value=content,
                height=150,
                key=f"copy_area_{hash(content)}",
                help="Select all (Ctrl+A) and copy (Ctrl+C) to clipboard",
                label_visibility="collapsed"
            )
    
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
    
    @staticmethod
    def render_debug_information(debug_info, show_raw_llm: bool, show_processed: bool, show_timing: bool, final_result: Optional[str] = None) -> None:
        """Render debug information in the UI and log to server console."""
        if not debug_info:
            return
        
        # Get debug summary
        summary = debug_info.get_summary()
        
        # Create logger for debug information
        logger = logging.getLogger("debug_info")
        
        # Log debug information to server console based on what's checked
        logger.info("=" * 80)
        logger.info("🔍 DEBUG INFORMATION - Server Console Output")
        logger.info("=" * 80)
        
        # Always log summary stats
        logger.info(f"📊 SUMMARY STATS:")
        logger.info(f"  Raw Chunks: {summary['raw_chunks_count']}")
        logger.info(f"  Raw Chars: {summary['total_raw_chars']}")
        logger.info(f"  Processed Chunks: {summary['processed_chunks_count']}")
        logger.info(f"  Processed Chars: {summary['total_processed_chars']}")
        logger.info(f"  Chars Difference: {summary['chars_difference']}")
        
        # Log raw LLM output if checkbox is checked
        if show_raw_llm:
            logger.info(f"📥 RAW LLM OUTPUT:")
            if summary["raw_content"]:
                logger.info(f"Content:\n{summary['raw_content']}")
            else:
                logger.info("No raw content captured")
        
        # Log processed output if checkbox is checked
        if show_processed:
            logger.info(f"⚙️ PROCESSED OUTPUT:")
            if summary["processed_content"]:
                logger.info(f"Content:\n{summary['processed_content']}")
            else:
                logger.info("No processed content")
            
            # Log processing steps
            logger.info(f"🔧 PROCESSING STEPS:")
            if debug_info.buffer_states:
                for i, (raw_chunk, processed_chunk, buffer_state) in enumerate(zip(
                    debug_info.raw_chunks, debug_info.processed_chunks, debug_info.buffer_states
                )):
                    logger.info(f"  Step {i+1}:")
                    logger.info(f"    Raw: {repr(raw_chunk)}")
                    logger.info(f"    Processed: {repr(processed_chunk)}")
                    if buffer_state:
                        logger.info(f"    State: {buffer_state}")
            else:
                logger.info("No processing steps captured")
        
        # Log timing information if checkbox is checked
        if show_timing and debug_info.timing_info:
            logger.info(f"⏱️ TIMING INFORMATION:")
            start_time = min(t["timestamp"] for t in debug_info.timing_info) if debug_info.timing_info else 0
            for timing in debug_info.timing_info:
                relative_time = timing["timestamp"] - start_time
                logger.info(f"  Time: {relative_time:.3f}s, Type: {timing['type']}, Chunk Size: {timing['chunk_size']}")
        
        # Always log final result when debug is enabled
        if final_result is not None:
            logger.info(f"🎯 FINAL RESULT:")
            logger.info(f"Content:\n{final_result}")
        
        logger.info("=" * 80)
        
        # Display debug summary in an expander
        with st.expander("🔍 Debug Information", expanded=True):
            # Summary stats
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Raw Chunks", summary["raw_chunks_count"])
                st.metric("Raw Chars", summary["total_raw_chars"])
            with col2:
                st.metric("Processed Chunks", summary["processed_chunks_count"])
                st.metric("Processed Chars", summary["total_processed_chars"])
            with col3:
                chars_diff = summary["chars_difference"]
                st.metric("Chars Difference", chars_diff, delta=chars_diff)
                
                # Show status
                if chars_diff == 0:
                    st.success("✅ No content lost")
                elif chars_diff > 0:
                    st.warning(f"⚠️ {chars_diff} chars filtered/lost")
                else:
                    st.error(f"❌ Something wrong: gained {abs(chars_diff)} chars")
            
            # Raw LLM output
            if show_raw_llm:
                st.subheader("📥 Raw LLM Output")
                if summary["raw_content"]:
                    st.code(summary["raw_content"], language="text")
                else:
                    st.info("No raw content captured")
            
            # Processed output
            if show_processed:
                st.subheader("⚙️ Processed Output")
                if summary["processed_content"]:
                    st.code(summary["processed_content"], language="text")
                else:
                    st.info("No processed content")
                
                # Show processing steps
                st.subheader("🔧 Processing Steps")
                if debug_info.buffer_states:
                    for i, (raw_chunk, processed_chunk, buffer_state) in enumerate(zip(
                        debug_info.raw_chunks, debug_info.processed_chunks, debug_info.buffer_states
                    )):
                        with st.container():
                            st.write(f"**Step {i+1}:**")
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write(f"Raw: `{repr(raw_chunk)}`")
                            with col2:
                                st.write(f"Processed: `{repr(processed_chunk)}`")
                            if buffer_state:
                                st.write(f"State: {buffer_state}")
                            st.divider()
                else:
                    st.info("No processing steps captured")
            
            # Timing information
            if show_timing and debug_info.timing_info:
                st.subheader("⏱️ Timing Information")
                
                # Create timing chart data
                import pandas as pd
                
                timing_data = []
                start_time = min(t["timestamp"] for t in debug_info.timing_info) if debug_info.timing_info else 0
                
                for timing in debug_info.timing_info:
                    timing_data.append({
                        "Time (s)": timing["timestamp"] - start_time,
                        "Type": timing["type"],
                        "Chunk Size": timing["chunk_size"]
                    })
                
                if timing_data:
                    df = pd.DataFrame(timing_data)
                    st.line_chart(df.set_index("Time (s)")["Chunk Size"])
                    st.dataframe(df)
                else:
                    st.info("No timing data captured")
            
            # Final result
            if final_result is not None:
                st.subheader("🎯 Final Result")
                st.code(final_result, language="text")