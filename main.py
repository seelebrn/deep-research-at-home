import asyncio
import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Import your research class
from deep_research import Pipe, User

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class InteractiveResearchSession:
    def __init__(self):
        self.pipe = Pipe()
        self.user = User(id="standalone_user", name="Research User", email="user@example.com")
        self.setup_valves()
        
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
        print("=" * 50)
        
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
            # Run initial research
            result = await self.pipe.pipe(
                body=body,
                __user__=self.user.__dict__,
                __event_emitter__=self.mock_event_emitter,
                __event_call__=self.mock_event_call,
                __task__=None,
                __model__="research",
                __request__=None
            )
            
            # Check if we're waiting for outline feedback
            state = self.pipe.get_state()
            waiting_for_feedback = state.get("waiting_for_outline_feedback", False)
            
            if waiting_for_feedback:
                # Get user feedback
                print("\n" + "=" * 50)
                user_feedback = input("Your feedback: ").strip()
                
                # Continue with feedback
                feedback_messages = messages + [
                    {
                        "id": "msg_2", 
                        "content": user_feedback,
                        "role": "user"
                    }
                ]
                
                feedback_body = {
                    "messages": feedback_messages
                }
                
                # Process feedback and continue research
                await self.pipe.pipe(
                    body=feedback_body,
                    __user__=self.user.__dict__,
                    __event_emitter__=self.mock_event_emitter,
                    __event_call__=self.mock_event_call,
                    __task__=None,
                    __model__="research",
                    __request__=None
                )
            
            print("\n" + "=" * 50)
            print("✅ Research completed successfully!")
            if self.pipe.valves.EXPORT_RESEARCH_DATA:
                print("📁 Check current directory for exported research files.")
                
        except Exception as e:
            print(f"\n❌ Error during research: {e}")
            logging.exception("Research failed")

async def main():
    """Main function to run the deep research system"""
    print("🔬 Deep Research System")
    print("=" * 50)
    
    user_query = input("Enter your research question: ").strip()
    
    if not user_query:
        print("No query provided. Exiting.")
        return
    
    session = InteractiveResearchSession()
    await session.run_research(user_query)

if __name__ == "__main__":
    asyncio.run(main())