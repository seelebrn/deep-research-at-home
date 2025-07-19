#!/usr/bin/env python3
"""
Research Knowledge Base - Persistent storage for research sources
Integrates with deep_research.py to provide local source caching and retrieval
"""

import chromadb
import logging
import hashlib
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Optional, Any
from urllib.parse import urlparse
import numpy as np

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResearchKnowledgeBase:
    """
    Persistent knowledge base for research sources using ChromaDB
    """
    
    def __init__(self, db_path: str = "./research_knowledge_db"):
        """Initialize ChromaDB client and collection"""
        self.db_path = db_path
        self.client = chromadb.PersistentClient(path=db_path)
        
        # Create or get collection
        self.collection = self.client.get_or_create_collection(
            name="research_sources",
            metadata={"description": "Research sources with embeddings for semantic search"}
        )
        
        logger.info(f"Knowledge base initialized at: {db_path}")
        logger.info(f"Current collection size: {self.collection.count()}")
   
    
    @staticmethod
    def list_knowledge_bases(base_path: str = "./DBs/") -> List[str]:
        """List all available knowledge base directories"""
        import os
        import glob
        
        # Look for directories ending with _knowledge_db
        pattern = os.path.join(base_path, "*_knowledge_db")
        db_dirs = glob.glob(pattern)
        
        # Extract just the database names (remove path and suffix)
        db_names = []
        for db_dir in db_dirs:
            basename = os.path.basename(db_dir)
            if basename.endswith("_knowledge_db"):
                db_name = basename[:-13]  # Remove "_knowledge_db" suffix
                db_names.append(db_name)
        
        return sorted(db_names)
    
    def _generate_source_id(self, url: str, title: str) -> str:
        """Generate unique ID for a source"""
        # Use URL as primary key, fallback to title hash if no URL
        if url and url.strip():
            return hashlib.md5(url.encode()).hexdigest()
        else:
            return hashlib.md5(title.encode()).hexdigest()
    
    def _clean_content(self, content: str, max_length: int = 10000) -> str:
        """Clean and truncate content for storage"""
        if not content:
            return ""
        
        # Remove excessive whitespace
        cleaned = " ".join(content.split())
        
        # Truncate if too long
        if len(cleaned) > max_length:
            cleaned = cleaned[:max_length] + "..."
        
        return cleaned
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            if url:
                return urlparse(url).netloc
            return "unknown"
        except:
            return "unknown"
    
    async def add_sources(self, sources: List[Dict], research_query: str = "", session_id: str = "") -> int:
        """
        Add multiple sources to the knowledge base
        
        Args:
            sources: List of source dictionaries with keys: url, title, content, etc.
            research_query: The original research query
            session_id: Unique identifier for this research session
            
        Returns:
            Number of sources successfully added
        """
        if not sources:
            return 0
            
        added_count = 0
        current_time = datetime.now().isoformat()
        
        # Prepare data for ChromaDB
        documents = []
        metadatas = []
        ids = []
        
        for source in sources:
            try:
                # Extract source data
                url = source.get("url", "")
                title = source.get("title", "Untitled")
                content = source.get("content", "")
                
                # Skip if no meaningful content
                if not content or len(content.strip()) < 100:
                    continue
                
                # Clean content
                clean_content = self._clean_content(content)
                
                # Generate unique ID
                source_id = self._generate_source_id(url, title)
                
                # Check if source already exists
                existing = await self.get_source_by_id(source_id)
                if existing:
                    logger.info(f"Source already exists, skipping: {title[:50]}...")
                    continue
                
                # Prepare metadata
                metadata = {
                    "title": title,
                    "url": url,
                    "domain": self._extract_domain(url),
                    "research_query": research_query,
                    "session_id": session_id,
                    "added_date": current_time,
                    "content_length": len(clean_content),
                    "source_type": source.get("source_type", "web"),
                    "tokens": source.get("tokens", 0),
                    "similarity": source.get("similarity", 0.0)
                }
                
                # Add to batch
                documents.append(clean_content)
                metadatas.append(metadata)
                ids.append(source_id)
                
                added_count += 1
                
            except Exception as e:
                logger.error(f"Error processing source {source.get('title', 'unknown')}: {e}")
                continue
        
        # Add batch to ChromaDB
        if documents:
            try:
                self.collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                logger.info(f"Successfully added {added_count} sources to knowledge base")
            except Exception as e:
                logger.error(f"Error adding sources to ChromaDB: {e}")
                return 0
        
        return added_count
    
    async def search_local(self, query: str, n_results: int = 10, min_similarity: float = 0.5) -> List[Dict]:
        """
        Search the local knowledge base for relevant sources
        
        Args:
            query: Search query
            n_results: Maximum number of results
            min_similarity: Minimum similarity threshold
            
        Returns:
            List of relevant sources
        """
        if not query or not query.strip():
            return []
        
        try:
            # Search ChromaDB
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            
            # Process results
            local_sources = []
            
            if results['documents'] and results['documents'][0]:
                for i, (doc, metadata, distance) in enumerate(zip(
                    results['documents'][0],
                    results['metadatas'][0],
                    results['distances'][0]
                )):
                    # Convert distance to similarity (ChromaDB uses L2 distance)
                    similarity = 1 / (1 + distance)
                    
                    # Filter by minimum similarity
                    if similarity < min_similarity:
                        continue
                    
                    source = {
                        "title": metadata.get("title", ""),
                        "url": metadata.get("url", ""),
                        "content": doc,
                        "similarity": similarity,
                        "domain": metadata.get("domain", ""),
                        "added_date": metadata.get("added_date", ""),
                        "source_type": metadata.get("source_type", "web"),
                        "tokens": metadata.get("tokens", 0),
                        "query": query,
                        "from_local_db": True
                    }
                    
                    local_sources.append(source)
            
            logger.info(f"Found {len(local_sources)} relevant sources in local knowledge base")
            return local_sources
            
        except Exception as e:
            logger.error(f"Error searching local knowledge base: {e}")
            return []
    
    async def get_source_by_id(self, source_id: str) -> Optional[Dict]:
        """Get a specific source by ID"""
        try:
            results = self.collection.get(
                ids=[source_id],
                include=["documents", "metadatas"]
            )
            
            if results['documents'] and results['documents'][0]:
                return {
                    "content": results['documents'][0],
                    "metadata": results['metadatas'][0]
                }
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving source {source_id}: {e}")
            return None
    
    async def get_stats(self) -> Dict:
        """Get knowledge base statistics"""
        try:
            count = self.collection.count()
            
            # Get sample of metadata for analysis
            sample = self.collection.get(
                limit=min(100, count),
                include=["metadatas"]
            )
            
            domains = {}
            queries = {}
            
            if sample['metadatas']:
                for metadata in sample['metadatas']:
                    domain = metadata.get("domain", "unknown")
                    query = metadata.get("research_query", "unknown")
                    
                    domains[domain] = domains.get(domain, 0) + 1
                    queries[query] = queries.get(query, 0) + 1
            
            return {
                "total_sources": count,
                "top_domains": sorted(domains.items(), key=lambda x: x[1], reverse=True)[:10],
                "recent_queries": sorted(queries.items(), key=lambda x: x[1], reverse=True)[:10],
                "database_path": self.db_path
            }
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"error": str(e)}
    
    async def cleanup_old_sources(self, days_old: int = 30) -> int:
        """Remove sources older than specified days"""
        try:
            # Get all sources
            all_sources = self.collection.get(include=["metadatas"])
            
            # Find old sources
            cutoff_date = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
            old_ids = []
            
            for i, metadata in enumerate(all_sources['metadatas']):
                added_date = metadata.get("added_date", "")
                try:
                    source_date = datetime.fromisoformat(added_date).timestamp()
                    if source_date < cutoff_date:
                        old_ids.append(all_sources['ids'][i])
                except:
                    continue
            
            # Delete old sources
            if old_ids:
                self.collection.delete(ids=old_ids)
                logger.info(f"Cleaned up {len(old_ids)} old sources")
            
            return len(old_ids)
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return 0

# Integration helper functions for deep_research.py
class DeepResearchIntegration:
    """Helper class to integrate with existing deep_research.py"""
    
    def __init__(self, knowledge_base: ResearchKnowledgeBase):
        self.kb = knowledge_base
    
    async def enhance_research_process(self, query: str, web_search_function, min_local_sources: int = 3):
        """
        Enhanced research process that checks local DB first
        
        Args:
            query: Research query
            web_search_function: Function to perform web search
            min_local_sources: Minimum local sources before web search
            
        Returns:
            Combined results from local and web sources
        """
        # Search local knowledge base first
        local_results = await self.kb.search_local(query, n_results=10)
        
        logger.info(f"Found {len(local_results)} sources in local knowledge base")
        
        # Determine if we need web search
        need_web_search = len(local_results) < min_local_sources
        
        if need_web_search:
            logger.info("Insufficient local sources, performing web search...")
            web_results = await web_search_function(query)
            
            # Store new web results in knowledge base
            if web_results:
                session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                await self.kb.add_sources(web_results, query, session_id)
            
            # Combine results
            combined_results = local_results + web_results
        else:
            logger.info("Sufficient local sources found, skipping web search")
            combined_results = local_results
        
        return combined_results
    
    async def store_research_session(self, results: List[Dict], query: str) -> int:
        """Store results from a research session"""
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return await self.kb.add_sources(results, query, session_id)

# Example usage and testing
async def main():
    """Test the knowledge base implementation"""
    
    # Initialize knowledge base
    kb = ResearchKnowledgeBase()
    
    # Test adding sources
    test_sources = [
        {
            "url": "https://example.com/article1",
            "title": "Test Article 1",
            "content": "This is test content about artificial intelligence and machine learning. It discusses various approaches to neural networks and deep learning algorithms.",
            "tokens": 100,
            "similarity": 0.8
        },
        {
            "url": "https://example.com/article2", 
            "title": "Test Article 2",
            "content": "This article covers natural language processing and its applications in modern AI systems. It explores transformer models and their impact on language understanding.",
            "tokens": 150,
            "similarity": 0.9
        }
    ]
    
    # Add sources
    added = await kb.add_sources(test_sources, "artificial intelligence research", "test_session")
    print(f"Added {added} sources")
    
    # Search local knowledge base
    results = await kb.search_local("machine learning algorithms", n_results=5)
    print(f"Found {len(results)} relevant sources")
    
    for result in results:
        print(f"- {result['title']} (similarity: {result['similarity']:.3f})")
    
    # Get stats
    stats = await kb.get_stats()
    print(f"Knowledge base stats: {stats}")

if __name__ == "__main__":
    asyncio.run(main())