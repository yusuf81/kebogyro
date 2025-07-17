#!/usr/bin/env python3

import sys
import asyncio
sys.path.insert(0, '/var/www/kebogyro')
sys.path.insert(0, '/var/www/kebogyro/src')

from web_ui.core_logic import process_chat_prompt, ContentBuffer

async def debug_truncation():
    """Debug exactly where truncation happens."""
    try:
        from web_ui.config import ConfigManager
        config = ConfigManager.load_from_env_file()
        
        prompt = "buatkan saya python untuk mencari bilangan prima"
        
        print("=== Testing ContentBuffer directly ===")
        
        # Simulate chunks that might cause issues
        test_chunks = [
            'Berikut adalah contoh program Python untuk mencari bilangan prima:\n\n```python\n',
            'def is_prime(num):\n    if num <= 1:\n        return False\n',
            '    for i in range(2, int(num**0.5) + 1):\n        if num % i == 0:\n            return False\n',
            '    return True\n\ndef find_primes(limit):\n    primes = []\n',
            '    for number in range(2, limit + 1):\n        if is_prime(number):\n            primes.append(number)\n',
            '    return primes\n\n# Contoh penggunaan\nlimit = int(input("Masukkan batas atas untuk mencari bilangan prima: "))\n',
            'primes = find_primes(limit)\n\nprint(f"Bilangan prima di antara 2 dan {limit} adalah:")\n',
            'for prime in primes:\n    print(prime, end=" ")\nprint()  # Untuk baris baru di akhir\n```\n\n',
            'Program ini memiliki dua fungsi utama:\n\n1. **`is_prime(num)`**: Fungsi untuk mengecek apakah suatu bilangan prima atau tidak\n',
            '2. **`find_primes(limit)`**: Fungsi untuk mencari semua bilangan prima dari 2 hingga batas yang ditentukan\n\n',
            'Anda dapat menjalankan program ini dan memasukkan batas atas yang diinginkan untuk mencari bilangan prima.'
        ]
        
        buffer = ContentBuffer()
        processed_chunks = []
        
        for i, chunk in enumerate(test_chunks):
            print(f"\n--- Processing chunk {i+1} ---")
            print(f"Input: '{chunk[:50]}{'...' if len(chunk) > 50 else ''}'")
            
            content, should_filter = buffer.add_chunk(chunk)
            
            print(f"Output: '{content[:50]}{'...' if len(content) > 50 else ''}' (len={len(content)})")
            print(f"Should filter: {should_filter}")
            print(f"Buffer after: '{buffer.buffer[:50]}{'...' if len(buffer.buffer) > 50 else ''}' (len={len(buffer.buffer)})")
            
            if content and not should_filter:
                processed_chunks.append(content)
            elif should_filter:
                print("🚨 CONTENT FILTERED!")
                break
        
        final_content = ''.join(processed_chunks)
        print(f"\n=== Final Result ===")
        print(f"Total processed: {len(final_content)} chars")
        print(f"Content: {final_content[:200]}...")
        if len(final_content) > 200:
            print(f"Ending: ...{final_content[-100:]}")
        
        # Test with actual streaming
        print(f"\n=== Testing actual chat processing ===")
        actual_chunks = []
        chunk_count = 0
        
        async for chunk in process_chat_prompt(prompt, config):
            chunk_count += 1
            if chunk:
                actual_chunks.append(chunk)
                print(f"Chunk {chunk_count}: '{chunk[:30]}...' (len={len(chunk)})")
            
            # Stop if we get too many chunks (avoid infinite loop)
            if chunk_count > 200:
                print("Stopping at 200 chunks to avoid infinite loop")
                break
        
        actual_content = ''.join(actual_chunks)
        print(f"\nActual streaming result: {len(actual_content)} chars")
        print(f"Content: {actual_content}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_truncation())