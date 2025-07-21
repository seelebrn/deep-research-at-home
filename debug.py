import logging
import json
import math
import time
import asyncio
import re
import random
import numpy as np
import aiohttp
import concurrent.futures
from datetime import datetime
from typing import Dict, List, Callable, Awaitable, Optional, Any, Union, Set, Tuple
from pydantic import BaseModel, Field
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from deep_storage import ResearchKnowledgeBase, DeepResearchIntegration
from academia import AcademicAPIManager

name = "Debug - Deep Research by ~Cadenza"


def setup_logger():
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.set_name(name)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
    return logger

logger = setup_logger()

class DebugPipe:
    def __init__(self, main_pipe_instance):
        """Initialize with reference to main Pipe instance"""
        self.pipe = main_pipe_instance
        self.logger = logger

    async def test_quote_extraction(self, subtopic: str, sources_for_subtopic: Dict):
        """Test the quote extraction functionality"""
        
        logger.info(f"🧪 TESTING quote extraction for subtopic: {subtopic}")
        logger.info(f"📊 Testing with {len(sources_for_subtopic)} sources")
        
        # Test the schema creation
        try:
            schema = self.create_quote_extraction_schema()
            logger.info("✅ Schema creation successful")
        except Exception as e:
            logger.error(f"❌ Schema creation failed: {e}")
            return
        
        # Test quote extraction
        try:
            quotes = await self.extract_key_quotes_for_subtopic(
                subtopic, sources_for_subtopic, "test query"
            )
            logger.info(f"✅ Quote extraction successful: {len(quotes)} quotes")
            
            for i, quote in enumerate(quotes):
                logger.info(f"Quote {i+1}:")
                logger.info(f"  Source: [{quote['source_id']}] {quote['title']}")
                logger.info(f"  Quote: \"{quote['quote']}\"")
                logger.info(f"  Score: {quote.get('relevance_score', 0):.2f}")
                logger.info(f"  Type: {quote.get('quote_type', 'unknown')}")
                
        except Exception as e:
            logger.error(f"❌ Quote extraction failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
    # Test specific aspects
    async def debug_structured_output(self):
        """Debug the structured output functionality"""
        
        test_messages = [
            {"role": "system", "content": "Extract quotes from the given text."},
            {"role": "user", "content": "Test content: The study found that 85% of users prefer the new interface."}
        ]
        
        try:
            schema = self.create_quote_extraction_schema()
            response = await self.generate_structured_completion(
                self.get_research_model(),
                test_messages,
                response_format=schema,
                temperature=0.3
            )
            
            logger.info(f"🧪 Test response: {response}")
            
            if response and "choices" in response:
                content = response["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                logger.info(f"✅ Structured output test successful: {parsed}")
            else:
                logger.error("❌ No valid response from structured output")
                
        except Exception as e:
            logger.error(f"❌ Structured output test failed: {e}")
            import traceback
            logger.error(traceback.format_exc())

    async def debug_citation_sources(self):
        """Debug function to check citation source alignment"""
        state = self.get_state()
        master_source_table = state.get("master_source_table", {})
        global_citation_map = state.get("global_citation_map", {})
        
        logger.info(f"=== CITATION SOURCES DEBUG ===")
        logger.info(f"Master source table entries:")
        for url, source_data in master_source_table.items():
            logger.info(f"  {source_data.get('id', 'NO_ID')} -> {url} -> {source_data.get('title', 'NO_TITLE')}")
        
        logger.info(f"Global citation map entries:")
        for url, citation_data in global_citation_map.items():
            logger.info(f"  {citation_data.get('global_id', 'NO_ID')} -> {url} -> {citation_data.get('title', 'NO_TITLE')}")
        
        # Check for mismatches
        logger.info(f"Checking for mismatches:")
        for url in global_citation_map:
            if url not in master_source_table:
                logger.error(f"  MISMATCH: {url} in citation map but not in master table")
        
        for url in master_source_table:
            if url not in global_citation_map:
                logger.warning(f"  UNUSED: {url} in master table but not in citation map")
        
        logger.info(f"=== CITATION SOURCES DEBUG END ===")