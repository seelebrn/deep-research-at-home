#!/usr/bin/env python3
"""
Deep Research System Launcher
Main entry point for choosing between report generation and knowledge chat.
"""

import asyncio
import subprocess
import sys
import os
from typing import List, Optional
import knowledge_chat
import main

# Import knowledge base to list available databases
try:
    from deep_storage import ResearchKnowledgeBase
except ImportError:
    print("❌ Error: Could not import ResearchKnowledgeBase from deep_storage.py")
    print("   Make sure deep_storage.py is in the same directory.")
    sys.exit(1)


class DeepResearchLauncher:
    def __init__(self):
        self.available_dbs = []
        self.load_available_databases()
    
    def load_available_databases(self):
        """Load list of available knowledge databases"""
        try:
            self.available_dbs = ResearchKnowledgeBase.list_knowledge_bases("./DBs/")
            if not self.available_dbs:
                self.available_dbs = []
        except Exception as e:
            print(f"⚠️  Warning: Could not load database list: {e}")
            self.available_dbs = []
    
    def display_welcome(self):
        """Display welcome message and main options"""
        print("🔬 Deep Research System")
        print("=" * 50)
        print()
        print("Welcome! Choose your action:")
        print()
        print("1️⃣  Generate Research Report")
        print("   └ Start new research or continue existing research")
        print()
        print("2️⃣  Chat with Knowledge Database")
        print("   └ Ask questions about your accumulated research data")
        print()
        print("3️⃣  Exit")
        print()
    
    def get_user_choice(self) -> int:
        """Get user's main choice"""
        while True:
            try:
                choice = input("Enter your choice (1-3): ").strip()
                
                if choice in ['1', '2', '3']:
                    return int(choice)
                else:
                    print("❌ Please enter 1, 2, or 3")
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                sys.exit(0)
            except Exception:
                print("❌ Invalid input. Please enter 1, 2, or 3")
    
    def display_databases(self):
        """Display available knowledge databases"""
        print("\n📚 Available Knowledge Databases:")
        print("-" * 40)
        
        if not self.available_dbs:
            print("   (No existing databases found)")
        else:
            for i, db_name in enumerate(self.available_dbs, 1):
                print(f"   {i}. {db_name}")
        
        print(f"   {len(self.available_dbs) + 1}. research (default/general)")
        print()
        
    def get_database_choice(self, mode: str) -> str:
        """Get user's database choice"""
        self.display_databases()
        
        if mode == "chat" and not self.available_dbs:
            print("⚠️  No knowledge databases found!")
            print("   You need to run some research first to create databases.")
            print("   Would you like to generate a research report instead? (y/n): ", end="")
            
            response = input().strip().lower()
            if response in ['y', 'yes']:
                return self.get_database_choice("research")
            else:
                print("👋 Exiting...")
                sys.exit(0)
        
        total_options = len(self.available_dbs) + 1  # +1 for default "research"
        
        print(f"Enter database number (1-{total_options}), name, or press Enter for default:")
        
        while True:
            try:
                choice = input("Database choice: ").strip()
                
                # Empty input = default
                if not choice:
                    return "research"
                
                # Check if it's a number
                if choice.isdigit():
                    choice_num = int(choice)
                    if 1 <= choice_num <= len(self.available_dbs):
                        return self.available_dbs[choice_num - 1]
                    elif choice_num == len(self.available_dbs) + 1:
                        return "research"
                    else:
                        print(f"❌ Please enter a number between 1-{total_options}")
                        continue
                
                # Check if it's a valid database name
                if choice in self.available_dbs or choice == "research":
                    return choice
                
                # Ask if they want to create a new database (for research mode)
                if mode == "research":
                    print(f"📝 Database '{choice}' doesn't exist.")
                    create = input("   Create new database? (y/n): ").strip().lower()
                    if create in ['y', 'yes']:
                        return choice
                    else:
                        print("   Please choose an existing database or press Enter for default.")
                        continue
                else:
                    print(f"❌ Database '{choice}' not found. Please choose an existing database.")
                    continue
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                sys.exit(0)
            except Exception:
                print("❌ Invalid input. Please try again.")
    
    def run_research(self, database: str):
        """Launch the research report generator"""
        print(f"\n🚀 Launching Research Report Generator...")
        print(f"📚 Database: {database}")
        print("=" * 50)
        
        try:
            # Build command
            cmd = [sys.executable, "main.py"]
            if database != "research":
                cmd.extend(["--kn", database])
            
            # Run main.py with the selected database
            result = subprocess.run(cmd, check=False)
            
            if result.returncode != 0:
                print(f"\n❌ Research process exited with code {result.returncode}")
            else:
                print(f"\n✅ Research process completed successfully!")
                
        except FileNotFoundError:
            print("❌ Error: main.py not found in current directory")
        except Exception as e:
            print(f"❌ Error launching research: {e}")
    
    def run_chat(self, database: str):
        """Launch the knowledge chat interface"""
        print(f"\n🧠 Launching Knowledge Chat...")
        print(f"📚 Database: {database}")
        print("=" * 50)
        
        try:
            # Build command
            cmd = [sys.executable, "knowledge_chat.py"]
            if database != "research":
                cmd.extend(["--kn", database])
            
            # Run knowledge_chat.py with the selected database
            result = subprocess.run(cmd, check=False)
            
            if result.returncode != 0:
                print(f"\n❌ Chat process exited with code {result.returncode}")
            else:
                print(f"\n✅ Chat session completed!")
                
        except FileNotFoundError:
            print("❌ Error: knowledge_chat.py not found in current directory")
        except Exception as e:
            print(f"❌ Error launching chat: {e}")
    
    def run(self):
        """Main launcher logic"""
        try:
            while True:
                self.display_welcome()
                choice = self.get_user_choice()
                
                if choice == 1:
                    # Research Report Generation
                    print("\n🔬 Research Report Generation Mode")
                    database = self.get_database_choice("research")
                    self.run_research(database)
                    
                    # Ask if user wants to continue
                    print("\n" + "=" * 50)
                    continue_choice = input("Return to main menu? (y/n): ").strip().lower()
                    if continue_choice not in ['y', 'yes']:
                        break
                    print()  # Add spacing
                    
                elif choice == 2:
                    # Knowledge Chat
                    print("\n🧠 Knowledge Chat Mode")
                    database = self.get_database_choice("chat")
                    self.run_chat(database)
                    
                    # Ask if user wants to continue
                    print("\n" + "=" * 50)
                    continue_choice = input("Return to main menu? (y/n): ").strip().lower()
                    if continue_choice not in ['y', 'yes']:
                        break
                    print()  # Add spacing
                    
                elif choice == 3:
                    # Exit
                    print("👋 Thank you for using Deep Research System!")
                    break
                    
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            sys.exit(1)


def main():
    """Entry point"""
    launcher = DeepResearchLauncher()
    launcher.run()


if __name__ == "__main__":
    main()