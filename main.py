import asyncio
import os
from dotenv import load_dotenv
import logging
import time
# Load environment variables
load_dotenv()
import argparse
# Import your research class
from deep_research import Pipe, User
from deep_storage import ResearchKnowledgeBase

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Deep Research System")
    parser.add_argument("--kn", "--knowledge", dest="knowledge_db", 
                       help="Knowledge database name to use (default: research)")
    parser.add_argument("--kn-list", "--knowledge-list", action="store_true",
                       help="List available knowledge databases and exit")
    return parser.parse_args()

class InteractiveResearchSession:
    def __init__(self, knowledge_db_name=None):
        self.pipe = Pipe()
        self.knowledge_db_name = knowledge_db_name or "research"
        self.user = User(id="standalone_user", name="Research User", email="user@example.com")
        self.setup_valves()
        # Initialize knowledge base with specified name
        self.pipe.initialize_knowledge_base(self.knowledge_db_name)
        
    def setup_valves(self):
        """Override valves with environment variables"""
        if os.getenv('LM_STUDIO_URL'):
            self.pipe.valves.OLLAMA_URL = os.getenv('LM_STUDIO_URL')
        if os.getenv('RESEARCH_MODEL'):
            self.pipe.valves.RESEARCH_MODEL = os.getenv('RESEARCH_MODEL')
        if os.getenv('SYNTHESIS_MODEL'):
            self.pipe.valves.SYNTHESIS_MODEL = os.getenv('SYNTHESIS_MODEL')
        if os.getenv('EMBEDDING_MODEL'):
            self.pipe.valves.EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL')
        if os.getenv('SEARCH_URL'):
            self.pipe.valves.SEARCH_URL = os.getenv('SEARCH_URL')
        if os.getenv('MAX_CYCLES'):
            self.pipe.valves.MAX_CYCLES = int(os.getenv('MAX_CYCLES'))
        if os.getenv('TEMPERATURE'):
            self.pipe.valves.TEMPERATURE = float(os.getenv('TEMPERATURE'))
        if os.getenv('ENABLED'):
            self.pipe.valves.ENABLED = os.getenv('ENABLED').lower() == 'true'
    
    async def mock_event_emitter(self, event_data):
        """Mock event emitter for standalone use"""
        if event_data.get('type') == 'message':
            print(f"📝 {event_data['data']['content']}")
        elif event_data.get('type') == 'status':
            status_data = event_data['data']
            status_icon = "✅" if status_data['status'] == 'complete' else "🔄"
            print(f"{status_icon} {status_data['description']}")
    
    async def mock_event_call(self, event_data):
        """Mock event call for standalone use"""
        return None
    
    async def run_research(self, query):
        """Run research with interactive feedback support"""
        print(f"\n🎯 Researching: {query}")
        self.original_query = query  # ← Add this line  
        print("=" * 50)
        # FORCE CLEAN START - Add this section
        print("🧹 Ensuring clean start...")
        fresh_pipe = Pipe()
        # Create completely new pipe instance
        fresh_pipe.valves = self.pipe.valves
        # Re-initialize knowledge base with same database name
        fresh_pipe.initialize_knowledge_base(self.knowledge_db_name)
        self.pipe = fresh_pipe
    
        print("   ✅ Created fresh pipe instance")
        print(f"   📚 Re-initialized knowledge base: {self.knowledge_db_name}")
        # Reset the pipe's conversation ID to force a new conversation
        if hasattr(self.pipe, 'conversation_id'):
            old_id = self.pipe.conversation_id
            self.pipe.conversation_id = f"fresh_{hash(query)}_{int(time.time())}"
            print(f"   Changed conversation ID: {old_id} → {self.pipe.conversation_id}")   


       
        # Prepare the message structure
        messages = [
            {
                "id": "msg_1",
                "content": query,
                "role": "user"
            }
        ]
        
        body = {
            "messages": messages
        }
        
        try:
            # Step 1: Run initial research (this sets up the pipe and user context)
            print("🔄 Starting initial research...")
            result = await self.pipe.pipe(
                body=body,
                __user__=self.user.__dict__,
                __event_emitter__=self.mock_event_emitter,
                __event_call__=self.mock_event_call,
                __task__=None,
                __model__="research",
                __request__=None
            )
            state = self.pipe.get_state()
            master_sources = state.get("master_source_table", {})
            results_history = state.get("results_history", [])
            research_dims = state.get("research_dimensions")

            print(f"🔍 DETAILED DEBUG after initial research:")
            print(f"   - Master sources: {len(master_sources)}")
            print(f"   - Results history: {len(results_history)}")
            content_cache = state.get("content_cache", {})
            print(f"   - Content cache: {len(content_cache)}")
            print(f"   - Research dimensions: {'✅' if research_dims else '❌'}")

            # Print first few sources if they exist
            if master_sources:
                print(f"   - Sample sources:")
                for i, (url, data) in enumerate(list(master_sources.items())[:3]):
                    print(f"     {i+1}. {data.get('id', 'no-id')}: {data.get('title', 'no-title')[:50]}...")

            # Print first few cached items  
            if content_cache:
                print(f"   - Sample cache:")
                for i, (url, data) in enumerate(list(content_cache.items())[:3]):
                    if isinstance(data, dict):
                        content_len = len(data.get("content", ""))
                        print(f"     {i+1}. {url[:50]}... ({content_len} chars)")

            if research_dims:
                coverage = research_dims.get("coverage", [])
                print(f"   - Dimensions coverage: {len(coverage)} dimensions")
            # Step 2: Check what happened after the initial call
            state = self.pipe.get_state()
            waiting_for_feedback = state.get("waiting_for_outline_feedback", False)
            research_completed = state.get("research_completed", False)
            
            print(f"\n🔍 DEBUG - After initial call:")
            print(f"   - Waiting for feedback: {waiting_for_feedback}")
            print(f"   - Research completed: {research_completed}")
            print(f"   - Results found: {len(state.get('results_history', []))}")
            print(f"   - State keys: {len(state.keys())} total")
            
            # Step 3: Handle feedback if needed
            if waiting_for_feedback:
                print("\n📋 FEEDBACK TIME!")
                user_feedback = input("Your feedback: ").strip()
                
                if not user_feedback:
                    user_feedback = "continue"
                
                print(f"📝 Processing feedback: '{user_feedback}'")
                
                # PRESERVE ORIGINAL CONTEXT
                feedback_messages = [
                    {
                        "id": "msg_1", 
                        "content": query,  # ← Keep original query!
                        "role": "user"
                    },
                    {
                        "id": "msg_2", 
                        "content": user_feedback,
                        "role": "user"
                    }
                ]
                
                feedback_body = {"messages": feedback_messages}
                
                # Step 4: Continue research with feedback
                print("🔄 Continuing research with your feedback...")
                result = await self.pipe.pipe(
                    body=feedback_body,
                    __user__=self.user.__dict__,
                    __event_emitter__=self.mock_event_emitter,
                    __event_call__=self.mock_event_call,
                    __task__=None,
                    __model__="research",
                    __request__=None
                )
                
                print("✅ Research continued successfully!")
                
            elif research_completed:
                print("✅ Research was completed in the initial call!")
                
            else:
                print("⚠️ Unexpected state - research may have encountered an issue")
                print(f"   Debug info: waiting={waiting_for_feedback}, completed={research_completed}")
            

            # Step 5: Final status check
            final_state = self.pipe.get_state()
            final_completed = final_state.get("research_completed", False)

            # FIX EXPORT DATA - Add this section
            if final_completed and hasattr(self, 'original_query'):
                print("🔧 Fixing export data...")
                
                # Update the research state with correct query
                research_state = final_state.get("research_state", {})
                research_state["user_message"] = self.original_query
                self.pipe.update_state("research_state", research_state)
                
                # Also ensure results_history has the correct query in results
                results_history = final_state.get("results_history", [])
                if results_history:
                    for result in results_history:
                        if not result.get("query") or result.get("query") == "continue":
                            result["query"] = self.original_query
                    self.pipe.update_state("results_history", results_history)
                
                print(f"   ✅ Fixed query: {self.original_query}")
                print(f"   ✅ Fixed {len(results_history)} results")


            if final_completed:
                print("\n" + "=" * 50)
                print("🎉 Research completed successfully!")
                
                if self.pipe.valves.EXPORT_RESEARCH_DATA:
                    print("📁 Research data exported to current directory")
                    
                # Show some stats
                results_count = len(final_state.get('results_history', []))
                print(f"📊 Total results processed: {results_count}")
                
            else:
                print("\n❌ Research did not complete successfully")
                print("   This might indicate an error or interruption")
                
        except Exception as e:
            print(f"\n💥 Error during research: {e}")
            print("Stack trace:")
            import traceback
            traceback.print_exc()
async def main():
    """Main function to run the deep research system"""
    # Parse command line arguments
    args = parse_arguments()
    
    # Handle knowledge database listing
    if args.kn_list:
        print("🔬 Available Knowledge Databases:")
        print("=" * 50)
        
        db_list = ResearchKnowledgeBase.list_knowledge_bases()
        if db_list:
            for i, db_name in enumerate(db_list, 1):
                print(f"{i}. {db_name}")
        else:
            print("No knowledge databases found.")
        
        print("\nUse --kn <name> to specify a database")
        return
    
    print("🔬 Deep Research System")
    print("=" * 50)
    
    # Display selected knowledge database
    selected_db = args.knowledge_db or "research"
    print(f"📚 Knowledge Database: {selected_db}")
    
    # Create the session with specified knowledge database
    session = InteractiveResearchSession(selected_db)
    
    # CHECK THE CRITICAL SETTINGS
    print(f"🔧 INTERACTIVE_RESEARCH: {session.pipe.valves.INTERACTIVE_RESEARCH}")
    print(f"🔧 ENABLED: {session.pipe.valves.ENABLED}")
    # Test embedding before research
    print("🧪 Testing embedding API...")
    test_embedding = await session.pipe.get_embedding("test methadone france")
    if test_embedding and len(test_embedding) > 0:
        print(f"   ✅ Embedding API working: {len(test_embedding)} dimensions")
    else:
        print(f"   ❌ Embedding API failed")
    user_query = input("Enter your research question: ").strip()
    
    if not user_query:
        print("No query provided. Exiting.")
        return
    
    await session.run_research(user_query)

if __name__ == "__main__":
    asyncio.run(main())