#!/usr/bin/env python3

import sys
import asyncio
import time
sys.path.insert(0, '/var/www/kebogyro')
sys.path.insert(0, '/var/www/kebogyro/src')

from web_ui.core_logic import process_chat_prompt, process_code_assistance_prompt
from web_ui.config import ConfigManager
from web_ui.session_manager import SessionManager

async def debug_streaming_issue():
    """Debug the streaming response truncation issue."""
    try:
        config = ConfigManager.load_from_env_file()
        
        # Test with the exact prompt that's causing issues
        prompt = "buatkan saya python untuk mencari bilangan prima"
        
        print("=== Debug Streaming Issue ===")
        print(f"Prompt: {prompt}")
        
        print("\n--- Testing Raw LLM Response ---")
        session_manager = SessionManager(config)
        llm_client = session_manager.get_chat_client()
        
        raw_chunks = []
        start_time = time.time()
        chunk_count = 0
        
        try:
            async for event_type, data in llm_client.chat_completion_with_tools(
                user_message_content=prompt,
                stream=True
            ):
                elapsed = time.time() - start_time
                print(f"[{elapsed:.2f}s] Event: {event_type}")
                
                if event_type == "messages":
                    message_chunk = data[0]
                    if hasattr(message_chunk, 'content') and message_chunk.content:
                        chunk_count += 1
                        content = message_chunk.content
                        raw_chunks.append(content)
                        print(f"  Chunk {chunk_count}: '{content[:50]}{'...' if len(content) > 50 else ''}' (len={len(content)})")
                elif event_type == "error":
                    print(f"  ERROR: {data}")
                    break
                else:
                    print(f"  Data: {str(data)[:100]}...")
        
        except Exception as e:
            print(f"Raw LLM error: {e}")
            import traceback
            traceback.print_exc()
        
        raw_content = ''.join(raw_chunks)
        print(f"\nRaw content total: {len(raw_content)} chars, {chunk_count} chunks")
        print(f"Raw content preview: {raw_content[:200]}...")
        if len(raw_content) > 200:
            print(f"Raw content ending: ...{raw_content[-100:]}")
        
        print("\n--- Testing Processed Response (Chat Mode) ---")
        processed_chunks = []
        start_time = time.time()
        chunk_count = 0
        
        try:
            async for chunk in process_chat_prompt(prompt, config):
                elapsed = time.time() - start_time
                chunk_count += 1
                if chunk:
                    processed_chunks.append(chunk)
                    print(f"[{elapsed:.2f}s] Processed chunk {chunk_count}: '{chunk[:50]}{'...' if len(chunk) > 50 else ''}' (len={len(chunk)})")
                else:
                    print(f"[{elapsed:.2f}s] Empty chunk {chunk_count}")
        
        except Exception as e:
            print(f"Processed response error: {e}")
            import traceback
            traceback.print_exc()
        
        processed_content = ''.join(processed_chunks)
        print(f"\nProcessed content total: {len(processed_content)} chars, {chunk_count} chunks")
        print(f"Processed content preview: {processed_content[:200]}...")
        if len(processed_content) > 200:
            print(f"Processed content ending: ...{processed_content[-100:]}")
        
        print("\n--- Testing Code Assistant Mode ---")
        code_chunks = []
        start_time = time.time()
        chunk_count = 0
        
        try:
            async for chunk in process_code_assistance_prompt(prompt, config):
                elapsed = time.time() - start_time
                chunk_count += 1
                if chunk:
                    code_chunks.append(chunk)
                    print(f"[{elapsed:.2f}s] Code chunk {chunk_count}: '{chunk[:50]}{'...' if len(chunk) > 50 else ''}' (len={len(chunk)})")
                else:
                    print(f"[{elapsed:.2f}s] Empty chunk {chunk_count}")
        
        except Exception as e:
            print(f"Code assistant error: {e}")
            import traceback
            traceback.print_exc()
        
        code_content = ''.join(code_chunks)
        print(f"\nCode assistant content total: {len(code_content)} chars, {chunk_count} chunks")
        print(f"Code assistant content preview: {code_content[:200]}...")
        if len(code_content) > 200:
            print(f"Code assistant content ending: ...{code_content[-100:]}")
        
        print("\n=== Summary ===")
        print(f"Raw LLM: {len(raw_content)} chars")
        print(f"Chat processed: {len(processed_content)} chars")
        print(f"Code assistant: {len(code_content)} chars")
        
        if len(raw_content) > len(processed_content):
            print("⚠️  ISSUE: Content is being truncated in chat processing!")
        elif len(raw_content) > len(code_content):
            print("⚠️  ISSUE: Content is being truncated in code assistant processing!")
        else:
            print("✅ No truncation detected")
        
    except Exception as e:
        print(f"Debug error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_streaming_issue())