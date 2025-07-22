#!/usr/bin/env python3
"""
Knowledge Chat - Interactive chat with ChromaDB knowledge base
Uses your accumulated research data to answer questions with context.
"""

import asyncio
import aiohttp
import argparse
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
import sys


# Import the knowledge base from your main script
try:
    from deep_storage import ResearchKnowledgeBase
except ImportError:
    print("Error: Could not import ResearchKnowledgeBase from deep_storage.py")
    print("Make sure deep_storage.py is in the same directory.")
    sys.exit(1)


class KnowledgeChat:
    def __init__(self, 
                 lm_studio_url: str = "http://localhost:1234",
                 chat_model: str = "qwen2.5-7b-longpo-128k-i1",
                 embedding_model: str = "granite-embedding:30m",
                 max_context_sources: int = 5,
                 similarity_threshold: float = 0.3,
                 knowledge_db_name: str = "research"):
        
        self.lm_studio_url = lm_studio_url
        self.chat_model = chat_model
        self.embedding_model = embedding_model
        self.max_context_sources = max_context_sources
        self.similarity_threshold = similarity_threshold
        self.knowledge_db_name = knowledge_db_name
        
        # Set up knowledge base path
        if knowledge_db_name == "research":
            db_path = "./DBs/research_knowledge_db"
        else:
            db_path = f"./DBs/{knowledge_db_name}_knowledge_db"
            
        # Initialize knowledge base
        self.knowledge_base = ResearchKnowledgeBase(db_path=db_path)
        
        # Chat history
        self.conversation_history = []
        
    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding for text using the embedding model"""
        try:
            connector = aiohttp.TCPConnector(force_close=True)
            async with aiohttp.ClientSession(connector=connector) as session:
                payload = {
                    "model": self.embedding_model,
                    "input": text,
                }

                async with session.post(
                    f"{self.lm_studio_url}/v1/embeddings", 
                    json=payload, 
                    timeout=30
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if "data" in result and len(result["data"]) > 0:
                            return result["data"][0].get("embedding", [])
                    else:
                        print(f"⚠️  Embedding request failed with status {response.status}")
                        return None
                        
        except Exception as e:
            print(f"⚠️  Error getting embedding: {e}")
            return None

    async def search_knowledge_base(self, query: str) -> List[Dict]:
        """Search the knowledge base for relevant sources"""
        try:
            results = await self.knowledge_base.search_local(
                query, 
                n_results=self.max_context_sources,
                min_similarity=self.similarity_threshold
            )
            return results
        except Exception as e:
            print(f"⚠️  Error searching knowledge base: {e}")
            return []

    async def generate_response(self, user_message: str, context_sources: List[Dict]) -> str:
        """Generate response using the chat model with knowledge base context"""
        
        # Build context from sources
        context = ""
        if context_sources:
            context = "## Relevant Information from Knowledge Base:\n\n"
            for i, source in enumerate(context_sources, 1):
                title = source.get('title', 'Unknown Source')
                content = source.get('content', '')[:1000]  # Limit content length
                similarity = source.get('similarity', 0.0)
                
                context += f"**Source {i}** (relevance: {similarity:.2f}): {title}\n"
                context += f"{content}...\n\n"
        
        # Create system prompt
        system_prompt = {
            "role": "system",
            "content": f"""You are a knowledgeable research assistant with access to a comprehensive knowledge base of research documents and sources.

Use the provided context sources to answer the user's question accurately and thoroughly. When referencing information from the sources, mention which source you're drawing from.

If the context sources don't contain relevant information for the user's question, say so clearly and offer to help with what you do know or suggest how they might find the information.

Be conversational but informative. Cite specific sources when making claims."""
        }
        
        # Build conversation with context
        messages = [system_prompt]
        
        # Add recent conversation history (last 6 messages)
        recent_history = self.conversation_history[-6:] if len(self.conversation_history) > 6 else self.conversation_history
        messages.extend(recent_history)
        
        # Add current query with context
        user_message_with_context = user_message
        if context:
            user_message_with_context = f"{context}\n## User Question:\n{user_message}"
        
        messages.append({
            "role": "user", 
            "content": user_message_with_context
        })
        
        try:
            connector = aiohttp.TCPConnector(force_close=True)
            async with aiohttp.ClientSession(connector=connector) as session:
                payload = {
                    "model": self.chat_model,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 2000,
                }

                async with session.post(
                    f"{self.lm_studio_url}/v1/chat/completions",
                    json=payload,
                    timeout=60
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if 'choices' in result and len(result['choices']) > 0:
                            return result['choices'][0]['message']['content']
                    else:
                        return f"⚠️  Error: API request failed with status {response.status}"
                        
        except Exception as e:
            return f"⚠️  Error generating response: {e}"

    def display_sources(self, sources: List[Dict]):
        """Display the sources used for context"""
        if not sources:
            print("📄 No relevant sources found in knowledge base.")
            return
            
        print(f"📄 Found {len(sources)} relevant sources:")
        for i, source in enumerate(sources, 1):
            title = source.get('title', 'Unknown Source')
            url = source.get('url', 'No URL')
            similarity = source.get('similarity', 0.0)
            print(f"   {i}. {title} (relevance: {similarity:.2f})")
            if url != 'No URL':
                print(f"      URL: {url}")
        print()

    async def chat_loop(self):
        """Main chat loop"""
        print(f"🧠 Knowledge Chat - Database: {self.knowledge_db_name}")
        print("💡 Ask questions about topics in your accumulated research data.")
        print("📚 Type 'help' for commands, 'quit' to exit.\n")
        
        # Check if knowledge base has data
        try:
            stats = await self.knowledge_base.get_stats()
            if stats.get('total_sources', 0) == 0:
                print("⚠️  Knowledge base appears to be empty.")
                print("   Run some research queries first to populate it with data.\n")
            else:
                print(f"📊 Knowledge base contains {stats.get('total_sources', 0)} sources")
                print(f"   Last updated: {stats.get('last_updated', 'Unknown')}\n")
        except Exception as e:
            print(f"⚠️  Could not access knowledge base stats: {e}\n")

        while True:
            try:
                # Get user input
                user_input = input("🤔 Ask me anything: ").strip()
                
                if not user_input:
                    continue
                    
                # Handle commands
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                    
                elif user_input.lower() == 'help':
                    self.show_help()
                    continue
                    
                elif user_input.lower() == 'clear':
                    self.conversation_history.clear()
                    print("🧹 Conversation history cleared.")
                    continue
                    
                elif user_input.lower() == 'stats':
                    await self.show_stats()
                    continue
                
                # Search knowledge base
                print("🔍 Searching knowledge base...")
                context_sources = await self.search_knowledge_base(user_input)
                
                # Display sources found
                self.display_sources(context_sources)
                
                # Generate response
                print("🤖 Thinking...")
                response = await self.generate_response(user_input, context_sources)
                
                # Display response
                print(f"💬 Assistant: {response}\n")
                
                # Update conversation history
                self.conversation_history.append({"role": "user", "content": user_input})
                self.conversation_history.append({"role": "assistant", "content": response})
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"⚠️  Error: {e}")

    def show_help(self):
        """Show help information"""
        print("""
🔧 Available Commands:
   help    - Show this help message
   clear   - Clear conversation history
   stats   - Show knowledge base statistics
   quit    - Exit the chat

💡 Tips:
   - Ask specific questions about your research topics
   - Reference specific documents or studies
   - Ask for summaries or comparisons
   - The assistant will cite sources when available

🎯 Example questions:
   - "What did I find about methadone regulation?"
   - "Summarize the key points about quantum computing from my research"
   - "What sources discuss environmental impacts?"
        """)

    async def show_stats(self):
        """Show knowledge base statistics"""
        try:
            stats = await self.knowledge_base.get_stats()
            print(f"""
📊 Knowledge Base Statistics:
   📄 Total sources: {stats.get('total_sources', 0)}
   📅 Last updated: {stats.get('last_updated', 'Unknown')}
   💾 Database size: {stats.get('db_size', 'Unknown')}
            """)
        except Exception as e:
            print(f"⚠️  Could not retrieve stats: {e}")


async def main():
    parser = argparse.ArgumentParser(description="Chat with your research knowledge base")
    parser.add_argument("--lm-studio-url", default="http://localhost:1234", 
                       help="LMStudio server URL")
    parser.add_argument("--chat-model", default="qwen2.5-7b-longpo-128k-i1",
                       help="Chat model name")
    parser.add_argument("--embedding-model", default="granite-embedding:30m",
                       help="Embedding model name")
    parser.add_argument("--max-sources", type=int, default=5,
                       help="Maximum context sources to use")
    parser.add_argument("--similarity-threshold", type=float, default=0.3,
                       help="Minimum similarity threshold for sources")
    parser.add_argument("--kn", "--knowledge", dest="knowledge_db", 
                       help="Knowledge database name to use (default: research)")
    parser.add_argument("--kn-list", "--knowledge-list", action="store_true",
                       help="List available knowledge databases and exit")
   
    args = parser.parse_args()
    
    # Handle knowledge database listing
    if args.kn_list:
        print("🧠 Available Knowledge Databases:")
        print("=" * 50)
        
        db_list = ResearchKnowledgeBase.list_knowledge_bases("./DBs/")
        if db_list:
            for i, db_name in enumerate(db_list, 1):
                print(f"{i}. {db_name}")
        else:
            print("No knowledge databases found in ./DBs/ directory.")
        
        print("\nUse --kn <name> to specify a database")
        return
        
    # Load environment variables if available
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        # Override with environment variables if present
        lm_studio_url = os.getenv("LM_STUDIO_URL", args.lm_studio_url)
        chat_model = os.getenv("CHAT_MODEL", args.chat_model)
        embedding_model = os.getenv("EMBEDDING_MODEL", args.embedding_model)
    except ImportError:
        lm_studio_url = args.lm_studio_url
        chat_model = args.chat_model
        embedding_model = args.embedding_model

    # Use the knowledge database from command line args (no asking)
    selected_db = args.knowledge_db or "research"
    
    print(f"🧠 Knowledge Chat")
    print("=" * 50)
    print(f"📚 Database: {selected_db}")
    print()
    
    # Initialize and run chat directly
    chat = KnowledgeChat(
        lm_studio_url=lm_studio_url,
        chat_model=chat_model,
        embedding_model=embedding_model,
        max_context_sources=args.max_sources,
        similarity_threshold=args.similarity_threshold,
        knowledge_db_name=selected_db
    )
    
    await chat.chat_loop()


if __name__ == "__main__":
    asyncio.run(main())