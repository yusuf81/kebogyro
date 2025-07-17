#!/usr/bin/env python3

import sys
sys.path.insert(0, '/var/www/kebogyro')
sys.path.insert(0, '/var/www/kebogyro/src')

from web_ui.core_logic import ContentBuffer, _is_tool_call_json

def test_curly_braces():
    """Test if curly braces in f-strings are causing issues."""
    
    print("=== Testing curly braces detection ===")
    
    # Test various f-string patterns
    test_cases = [
        'print(f"Bilangan prima antara 2 dan',
        ' {',
        'limit',
        '}',
        ' adalah:")',
        'print(f"Hello {name}")',
        '{"name": "test"}',  # This should be filtered
        '{limit}',  # This should NOT be filtered
        'for i in range({start}, {end}):',
        '{"tool": "assistant"}'  # This should be filtered
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"\nTest {i+1}: '{test_case}'")
        print(f"  _is_tool_call_json: {_is_tool_call_json(test_case)}")
        
        # Test with ContentBuffer
        buffer = ContentBuffer()
        content, should_filter = buffer.add_chunk(test_case)
        print(f"  ContentBuffer result: content='{content}', should_filter={should_filter}")
    
    print(f"\n=== Testing f-string sequence ===")
    
    # Test the exact sequence that might be causing issues
    fstring_chunks = [
        'print(f"Bilangan prima antara 2 dan ',
        '{',
        'limit',
        '}',
        ' adalah:")'
    ]
    
    buffer = ContentBuffer()
    collected_chunks = []
    
    for i, chunk in enumerate(fstring_chunks):
        print(f"\nChunk {i+1}: '{chunk}'")
        content, should_filter = buffer.add_chunk(chunk)
        print(f"  Output: '{content}' (len={len(content)})")
        print(f"  Should filter: {should_filter}")
        print(f"  Buffer: '{buffer.buffer}' (len={len(buffer.buffer)})")
        
        if content and not should_filter:
            collected_chunks.append(content)
        elif should_filter:
            print(f"  🚨 FILTERED at chunk {i+1}!")
            break
    
    final_result = ''.join(collected_chunks)
    print(f"\nFinal result: '{final_result}'")
    print(f"Length: {len(final_result)}")

if __name__ == "__main__":
    test_curly_braces()