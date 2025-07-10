#!/usr/bin/env python3
"""
API Connection Tester
Test connectivity to your local LLM API
"""

import asyncio
import aiohttp
import json
import sys

async def test_api_connection():
    """Test connection to local API"""
    
    # Test configurations
    test_configs = [
        {
            "name": "Ollama Standard",
            "base_url": "http://127.0.0.1:11434/v1",
            "api_key": "0000"
        },
        {
            "name": "Ollama Alternative",
            "base_url": "http://localhost:11434/v1", 
            "api_key": "0000"
        },
        {
            "name": "Ollama Direct",
            "base_url": "http://127.0.0.1:11434",
            "api_key": "0000"
        }
    ]
    
    print("🔍 Testing API Connections...")
    print("=" * 50)
    
    for config in test_configs:
        print(f"\n📡 Testing {config['name']}: {config['base_url']}")
        
        try:
            # Test basic connectivity
            connector = aiohttp.TCPConnector(force_close=True)
            async with aiohttp.ClientSession(connector=connector) as session:
                
                # Test 1: Basic endpoint
                try:
                    async with session.get(f"{config['base_url']}/models", timeout=5) as response:
                        print(f"   ✅ /models endpoint: {response.status}")
                        if response.status == 200:
                            models = await response.json()
                            print(f"   📋 Available models: {len(models.get('data', []))} found")
                except Exception as e:
                    print(f"   ❌ /models endpoint failed: {e}")
                
                # Test 2: Chat completions
                try:
                    headers = {
                        "Authorization": f"Bearer {config['api_key']}",
                        "Content-Type": "application/json"
                    }
                    
                    payload = {
                        "model": "gemma3n:e2b",
                        "messages": [{"role": "user", "content": "Hello"}],
                        "temperature": 0.7
                    }
                    
                    async with session.post(
                        f"{config['base_url']}/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=10
                    ) as response:
                        print(f"   ✅ /chat/completions: {response.status}")
                        if response.status == 200:
                            result = await response.json()
                            print(f"   💬 Chat response: {result['choices'][0]['message']['content'][:50]}...")
                        else:
                            error_text = await response.text()
                            print(f"   ❌ Chat error: {error_text[:100]}...")
                            
                except Exception as e:
                    print(f"   ❌ /chat/completions failed: {e}")
                
                # Test 3: Embeddings
                try:
                    headers = {
                        "Authorization": f"Bearer {config['api_key']}",
                        "Content-Type": "application/json"
                    }
                    
                    payload = {
                        "model": "DC1LEX/nomic-embed-text-v1.5-multimodal:latest",
                        "input": "test"
                    }
                    
                    async with session.post(
                        f"{config['base_url']}/embeddings",
                        headers=headers,
                        json=payload,
                        timeout=10
                    ) as response:
                        print(f"   ✅ /embeddings: {response.status}")
                        if response.status == 200:
                            result = await response.json()
                            print(f"   🔢 Embedding size: {len(result['data'][0]['embedding'])}")
                        else:
                            error_text = await response.text()
                            print(f"   ❌ Embedding error: {error_text[:100]}...")
                            
                except Exception as e:
                    print(f"   ❌ /embeddings failed: {e}")
                    
        except Exception as e:
            print(f"   ❌ Connection failed: {e}")
    
    print("\n" + "=" * 50)
    print("🔍 Testing Search Backend...")
    
    # Test search backend
    search_urls = [
        "http://localhost:8888/search?q=test",
        "http://127.0.0.1:8888/search?q=test"
    ]
    
    for search_url in search_urls:
        print(f"\n🔍 Testing: {search_url}")
        try:
            connector = aiohttp.TCPConnector(force_close=True)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(search_url, timeout=5) as response:
                    print(f"   ✅ Search endpoint: {response.status}")
                    if response.status == 200:
                        try:
                            results = await response.json()
                            print(f"   📋 Search results: {len(results)} found")
                        except:
                            text = await response.text()
                            print(f"   📄 Response type: {type(text)} ({len(text)} chars)")
                    else:
                        error_text = await response.text()
                        print(f"   ❌ Search error: {error_text[:100]}...")
        except Exception as e:
            print(f"   ❌ Search failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_api_connection())