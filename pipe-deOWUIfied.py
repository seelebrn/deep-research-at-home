#!/usr/bin/env python3
"""
Standalone Deep Research Tool
Full conversion from Open-WebUI pipe to work with any OpenAI-compatible API
Preserves all advanced research capabilities from the original 11k line script
"""

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
from datetime import datetime, timedelta
from typing import Dict, List, Callable, Awaitable, Optional, Any, Union, Set, Tuple
from pydantic import BaseModel, Field
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
import argparse
import sys
import os
import tempfile
import gzip
from urllib.parse import urlparse, quote
import io

def setup_logger():
    logger = logging.getLogger("DeepResearch")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
    return logger

logger = setup_logger()

class ResearchConfig:
    """Configuration class replacing Open-WebUI valves"""
    def __init__(self):
        # Core API settings
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
        self.OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        
        # Model settings
        self.ENABLED = True
        self.RESEARCH_MODEL = "gpt-3.5-turbo"
        self.SYNTHESIS_MODEL = ""  # Use RESEARCH_MODEL if empty
        self.EMBEDDING_MODEL = "text-embedding-ada-002"
        self.QUALITY_FILTER_MODEL = "gpt-3.5-turbo"

        # Quality filtering
        self.QUALITY_FILTER_ENABLED = True
        self.QUALITY_SIMILARITY_THRESHOLD = 0.60

        # Research cycles
        self.MAX_CYCLES = 15
        self.MIN_CYCLES = 10
        self.EXPORT_RESEARCH_DATA = True

        # Search parameters
        self.SEARCH_RESULTS_PER_QUERY = 3
        self.EXTRA_RESULTS_PER_QUERY = 3
        self.SUCCESSFUL_RESULTS_PER_QUERY = 1
        self.MAX_FAILED_RESULTS = 6

        # Content processing
        self.CHUNK_LEVEL = 2
        self.COMPRESSION_LEVEL = 4
        self.LOCAL_INFLUENCE_RADIUS = 3
        self.QUERY_WEIGHT = 0.5
        self.FOLLOWUP_WEIGHT = 0.5
        self.EXTRACT_CONTENT_ONLY = True
        self.PDF_MAX_PAGES = 25
        self.HANDLE_PDFS = True
        self.RELEVANCY_SNIPPET_LENGTH = 2000

        # Generation parameters
        self.TEMPERATURE = 0.7
        self.SYNTHESIS_TEMPERATURE = 0.6

        # Search backend
        self.SEARCH_URL = "http://localhost:8888/search?q="

        # Domain and content priorities
        self.DOMAIN_PRIORITY = ""
        self.CONTENT_PRIORITY = ""
        self.DOMAIN_MULTIPLIER = 1.3
        self.KEYWORD_MULTIPLIER_PER_MATCH = 1.1
        self.MAX_KEYWORD_MULTIPLIER = 2.0

        # Interactive and preference settings
        self.INTERACTIVE_RESEARCH = True  # Re-enabled for CLI
        self.USER_PREFERENCE_THROUGHOUT = True
        self.SEMANTIC_TRANSFORMATION_STRENGTH = 0.7
        self.TRAJECTORY_MOMENTUM = 0.6
        self.GAP_EXPLORATION_WEIGHT = 0.4

        # Advanced compression and synthesis
        self.STEPPED_SYNTHESIS_COMPRESSION = True
        self.MAX_RESULT_TOKENS = 4000
        self.COMPRESSION_SETPOINT = 4000
        self.REPEATS_BEFORE_EXPANSION = 3
        self.REPEAT_WINDOW_FACTOR = 0.95

        # Citation verification
        self.VERIFY_CITATIONS = True

        # Threading
        self.THREAD_WORKERS = 2

class EventEmitter:
    """Event emitter for progress updates"""
    def __init__(self, verbose=True):
        self.verbose = verbose
    
    async def emit_message(self, message: str):
        if self.verbose:
            print(message, end='')
    
    async def emit_status(self, level: str, message: str, done: bool = False):
        if self.verbose:
            status_prefix = {
                "info": "[INFO]",
                "success": "[SUCCESS]", 
                "error": "[ERROR]",
                "warning": "[WARNING]"
            }.get(level, "[INFO]")
            print(f"{status_prefix} {message}")

class EmbeddingCache:
    """Cache for embeddings to avoid redundant API calls"""
    def __init__(self, max_size=10000000):
        self.cache = {}
        self.max_size = max_size
        self.hit_count = 0
        self.miss_count = 0
        self.url_token_counts = {}

    def get(self, text_key):
        key = hash(text_key[:2000])
        result = self.cache.get(key)
        if result is not None:
            self.hit_count += 1
        return result

    def set(self, text_key, embedding):
        key = hash(text_key[:2000])
        self.cache[key] = embedding
        self.miss_count += 1

        if len(self.cache) > self.max_size:
            self.cache.pop(next(iter(self.cache)))

    def stats(self):
        total = self.hit_count + self.miss_count
        hit_rate = self.hit_count / total if total > 0 else 0
        return {
            "size": len(self.cache),
            "hits": self.hit_count,
            "misses": self.miss_count,
            "hit_rate": hit_rate,
        }

class TransformationCache:
    """Cache for transformed embeddings"""
    def __init__(self, max_size=2500000):
        self.cache = {}
        self.max_size = max_size
        self.hit_count = 0
        self.miss_count = 0

    def get(self, text, transform_id):
        key = f"{hash(text[:2000])}_{hash(str(transform_id))}"
        result = self.cache.get(key)
        if result is not None:
            self.hit_count += 1
        return result

    def set(self, text, transform_id, transformed_embedding):
        key = f"{hash(text[:2000])}_{hash(str(transform_id))}"
        self.cache[key] = transformed_embedding
        self.miss_count += 1

        if len(self.cache) > self.max_size:
            self.cache.pop(next(iter(self.cache)))

    def stats(self):
        total = self.hit_count + self.miss_count
        hit_rate = self.hit_count / total if total > 0 else 0
        return {
            "size": len(self.cache),
            "hits": self.hit_count,
            "misses": self.miss_count,
            "hit_rate": hit_rate,
        }

class ResearchStateManager:
    """Manages research state per conversation"""
    def __init__(self):
        self.conversation_states = {}

    def get_state(self, conversation_id):
        if conversation_id not in self.conversation_states:
            self.conversation_states[conversation_id] = {
                "research_completed": False,
                "prev_comprehensive_summary": "",
                "waiting_for_outline_feedback": False,
                "outline_feedback_data": None,
                "research_state": None,
                "follow_up_mode": False,
                "user_preferences": {"pdv": None, "strength": 0.0, "impact": 0.0},
                "research_dimensions": None,
                "research_trajectory": None,
                "pdv_alignment_history": [],
                "gap_coverage_history": [],
                "semantic_transformations": None,
                "section_synthesized_content": {},
                "section_citations": {},
                "url_selected_count": {},
                "url_considered_count": {},
                "url_token_counts": {},
                "master_source_table": {},
                "global_citation_map": {},
                "verified_citations": [],
                "flagged_citations": [],
                "citation_fixes": [],
                "memory_stats": {
                    "results_tokens": 0,
                    "section_tokens": {},
                    "synthesis_tokens": 0,
                    "total_tokens": 0,
                },
                "results_history": [],
                "search_history": [],
                "active_outline": [],
                "cycle_summaries": [],
                "completed_topics": set(),
                "irrelevant_topics": set(),
                "url_results_cache": {},
                "similarity_cache": {},
                "subtopic_relevance_cache": {},
                "topic_alignment_cache": {},
                "eigendecomposition_cache": {},
                "dimensions_translation_cache": {},
                "trajectory_cache": {},
                "domain_session_map": {},
                "topic_usage_counts": {},
                "verification_results": {},
                "vocabulary_embeddings": {},
                "subtopic_synthesized_content": {},
                "section_sources_map": {},
                "subtopic_sources": {},
                "latest_dimension_coverage": [],
            }
        return self.conversation_states[conversation_id]

    def update_state(self, conversation_id, key, value):
        state = self.get_state(conversation_id)
        state[key] = value

    def reset_state(self, conversation_id):
        if conversation_id in self.conversation_states:
            del self.conversation_states[conversation_id]

class TrajectoryAccumulator:
    """Efficiently accumulates research trajectory across cycles"""
    def __init__(self, embedding_dim=1536):  # OpenAI embeddings are 1536 dim
        self.query_sum = np.zeros(embedding_dim)
        self.result_sum = np.zeros(embedding_dim)
        self.count = 0
        self.embedding_dim = embedding_dim

    def add_cycle_data(self, query_embeddings, result_embeddings, weight=1.0):
        if not query_embeddings or not result_embeddings:
            return

        query_centroid = np.mean(query_embeddings, axis=0)
        result_centroid = np.mean(result_embeddings, axis=0)

        self.query_sum += query_centroid * weight
        self.result_sum += result_centroid * weight
        self.count += 1

    def get_trajectory(self):
        if self.count == 0:
            return None

        query_centroid = self.query_sum / self.count
        result_centroid = self.result_sum / self.count
        trajectory = result_centroid - query_centroid

        norm = np.linalg.norm(trajectory)
        if norm > 1e-10:
            return (trajectory / norm).tolist()
        else:
            return None

class DeepResearcher:
    """Main research class with all advanced capabilities"""
    
    def __init__(self, config: ResearchConfig, event_emitter: EventEmitter):
        self.config = config
        self.event_emitter = event_emitter
        self.state_manager = ResearchStateManager()
        self.conversation_id = "default"
        
        # Initialize caches and state
        self.embedding_cache = EmbeddingCache(max_size=10000000)
        self.transformation_cache = TransformationCache(max_size=2500000)
        self.vocabulary_cache = None
        self.vocabulary_embeddings = None
        self.is_pdf_content = False
        self.research_date = datetime.now().strftime("%Y-%m-%d")
        self.trajectory_accumulator = None
        
        # Initialize executor
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.config.THREAD_WORKERS
        )

    def get_state(self):
        return self.state_manager.get_state(self.conversation_id)

    def update_state(self, key, value):
        self.state_manager.update_state(self.conversation_id, key, value)

    def reset_state(self):
        self.state_manager.reset_state(self.conversation_id)
        self.trajectory_accumulator = None
        self.is_pdf_content = False
        logger.info(f"Full state reset for conversation: {self.conversation_id}")

    def get_research_model(self):
        return self.config.RESEARCH_MODEL

    def get_synthesis_model(self):
        if self.config.SYNTHESIS_MODEL:
            return self.config.SYNTHESIS_MODEL
        return self.config.RESEARCH_MODEL

    async def count_tokens(self, text: str) -> int:
        """Count tokens - simplified estimation"""
        if not text:
            return 0
        # OpenAI approximation: ~4 characters per token
        return max(1, len(text) // 4)

    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding using OpenAI API with caching"""
        if not text or not text.strip():
            return None

        text = text[:8000]  # OpenAI limit
        text = text.replace(":", " - ")

        # Check cache first
        cached_embedding = self.embedding_cache.get(text)
        if cached_embedding is not None:
            return cached_embedding

        try:
            headers = {
                "Authorization": f"Bearer {self.config.OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.config.EMBEDDING_MODEL,
                "input": text
            }

            connector = aiohttp.TCPConnector(force_close=True)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(
                    f"{self.config.OPENAI_BASE_URL}/embeddings",
                    headers=headers,
                    json=payload,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        embedding = result["data"][0]["embedding"]
                        if embedding:
                            self.embedding_cache.set(text, embedding)
                            return embedding
                    else:
                        logger.warning(f"Embedding request failed with status {response.status}")
                        return None

        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            return None

    async def get_transformed_embedding(self, text: str, transformation=None) -> Optional[List[float]]:
        """Get embedding with optional transformation"""
        if not text or not text.strip():
            return None

        if transformation is None:
            return await self.get_embedding(text)

        transform_id = (
            transformation.get("id", str(hash(str(transformation))))
            if isinstance(transformation, dict)
            else transformation
        )
        cached_transformed = self.transformation_cache.get(text, transform_id)
        if cached_transformed is not None:
            return cached_transformed

        base_embedding = await self.get_embedding(text)
        if not base_embedding:
            return None

        transformed = await self.apply_semantic_transformation(base_embedding, transformation)
        if transformed:
            self.transformation_cache.set(text, transform_id, transformed)

        return transformed

    async def generate_completion(
        self,
        model: str,
        messages: List[Dict],
        stream: bool = False,
        temperature: Optional[float] = None,
    ):
        """Generate completion using OpenAI API"""
        try:
            if temperature is None:
                temperature = self.config.TEMPERATURE

            headers = {
                "Authorization": f"Bearer {self.config.OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "stream": stream
            }

            connector = aiohttp.TCPConnector(force_close=True)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(
                    f"{self.config.OPENAI_BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=300
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"API request failed with status {response.status}")
                        error_text = await response.text()
                        return {"choices": [{"message": {"content": f"API Error {response.status}: {error_text}"}}]}

        except Exception as e:
            logger.error(f"Error generating completion: {e}")
            return {"choices": [{"message": {"content": f"Error: {str(e)}"}}]}

    def chunk_text(self, text: str) -> List[str]:
        """Split text into chunks based on configured chunk level"""
        chunk_level = self.config.CHUNK_LEVEL

        if chunk_level <= 0:
            return [text]

        if chunk_level == 1:  # Phrase-level
            paragraphs = text.split("\n")
            chunks = []
            for paragraph in paragraphs:
                if not paragraph.strip():
                    continue
                paragraph_phrases = re.split(r"(?<=[,;:])\s+", paragraph)
                for phrase in paragraph_phrases:
                    if phrase.strip():
                        chunks.append(phrase.strip())
            return chunks

        if chunk_level == 2:  # Sentence-level
            if self.is_pdf_content:
                chunks = []
                sentences = re.split(r"(?<=[.!?])\s+", text)
                for sentence in sentences:
                    if sentence.strip():
                        chunks.append(sentence.strip())
            else:
                paragraphs = text.split("\n")
                chunks = []
                for paragraph in paragraphs:
                    if not paragraph.strip():
                        continue
                    sentences = re.split(r"(?<=[.!?])\s+", paragraph)
                    for sentence in sentences:
                        if sentence.strip():
                            chunks.append(sentence.strip())
            return chunks

        # Level 3+: Paragraph-level chunking
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

        if chunk_level == 3:
            return paragraphs

        # Multi-paragraph chunking
        chunks = []
        paragraphs_per_chunk = chunk_level - 2
        for i in range(0, len(paragraphs), paragraphs_per_chunk):
            chunk = "\n".join(paragraphs[i:i + paragraphs_per_chunk])
            chunks.append(chunk)

        return chunks

    async def compress_content_with_local_similarity(
        self,
        content: str,
        query_embedding: List[float],
        summary_embedding: Optional[List[float]] = None,
        ratio: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Apply semantic compression with local similarity influence"""
        if len(content) < 100:
            return content

        if max_tokens:
            content_tokens = await self.count_tokens(content)
            if content_tokens <= max_tokens:
                return content
            if not ratio:
                ratio = max_tokens / content_tokens

        chunks = self.chunk_text(content)
        if len(chunks) <= 1:
            return content

        chunk_embeddings = []
        for chunk in chunks:
            embedding = await self.get_embedding(chunk)
            if embedding:
                chunk_embeddings.append(embedding)

        if len(chunk_embeddings) <= 1:
            return content

        if ratio is None:
            compress_ratios = {
                1: 0.9, 2: 0.8, 3: 0.7, 4: 0.6, 5: 0.5,
                6: 0.4, 7: 0.3, 8: 0.2, 9: 0.15, 10: 0.1
            }
            ratio = compress_ratios.get(self.config.COMPRESSION_LEVEL, 0.5)

        n_chunks = len(chunk_embeddings)
        n_keep = max(1, min(n_chunks - 1, int(n_chunks * ratio)))

        try:
            embeddings_array = np.array(chunk_embeddings)
            document_centroid = np.mean(embeddings_array, axis=0)

            # Calculate local similarity
            local_similarities = []
            local_radius = self.config.LOCAL_INFLUENCE_RADIUS

            for i in range(len(embeddings_array)):
                local_sim = 0.0
                count = 0

                for j in range(max(0, i - local_radius), i):
                    local_sim += cosine_similarity([embeddings_array[i]], [embeddings_array[j]])[0][0]
                    count += 1

                for j in range(i + 1, min(len(embeddings_array), i + local_radius + 1)):
                    local_sim += cosine_similarity([embeddings_array[i]], [embeddings_array[j]])[0][0]
                    count += 1

                if count > 0:
                    local_sim /= count

                local_similarities.append(local_sim)

            # Calculate importance scores
            importance_scores = []
            state = self.get_state()
            user_preferences = state.get("user_preferences", {"pdv": None, "strength": 0.0, "impact": 0.0})

            for i, embedding in enumerate(embeddings_array):
                if np.isnan(embedding).any() or np.isinf(embedding).any():
                    embedding = np.nan_to_num(embedding, nan=0.0, posinf=1.0, neginf=-1.0)

                doc_similarity = cosine_similarity([embedding], [document_centroid])[0][0]
                query_similarity = cosine_similarity([embedding], [query_embedding])[0][0]

                summary_similarity = 0.0
                if summary_embedding is not None:
                    summary_similarity = cosine_similarity([embedding], [summary_embedding])[0][0]
                    query_similarity = (query_similarity * self.config.FOLLOWUP_WEIGHT + 
                                      summary_similarity * (1.0 - self.config.FOLLOWUP_WEIGHT))

                local_influence = local_similarities[i]

                pdv_alignment = 0.5
                if (self.config.USER_PREFERENCE_THROUGHOUT and 
                    user_preferences["pdv"] is not None):
                    chunk_embedding_np = np.array(embedding)
                    pdv_np = np.array(user_preferences["pdv"])
                    alignment = np.dot(chunk_embedding_np, pdv_np)
                    pdv_alignment = (alignment + 1) / 2
                    pdv_influence = min(0.3, user_preferences["strength"] / 10)
                else:
                    pdv_influence = 0.0

                doc_weight = (1.0 - self.config.QUERY_WEIGHT) * 0.4
                local_weight = (1.0 - self.config.QUERY_WEIGHT) * 0.8
                query_weight = self.config.QUERY_WEIGHT * (1.0 - pdv_influence)

                final_score = (
                    (doc_similarity * doc_weight) +
                    (query_similarity * query_weight) +
                    (local_influence * local_weight) +
                    (pdv_alignment * pdv_influence)
                )

                importance_scores.append((i, final_score))

            importance_scores.sort(key=lambda x: x[1], reverse=True)
            selected_indices = [x[0] for x in importance_scores[:n_keep]]
            selected_indices.sort()
            selected_chunks = [chunks[i] for i in selected_indices if i < len(chunks)]

            chunk_level = self.config.CHUNK_LEVEL
            if chunk_level == 1:
                compressed_content = " ".join(selected_chunks)
            elif chunk_level == 2:
                processed_sentences = []
                for sentence in selected_chunks:
                    if not sentence.endswith((".", "!", "?", ":", ";")):
                        sentence += "."
                    processed_sentences.append(sentence)
                compressed_content = " ".join(processed_sentences)
            else:
                compressed_content = "\n".join(selected_chunks)

            if max_tokens:
                final_tokens = await self.count_tokens(compressed_content)
                if final_tokens > max_tokens:
                    new_ratio = max_tokens / final_tokens
                    compressed_content = await self.compress_content_with_local_similarity(
                        compressed_content, query_embedding, summary_embedding, ratio=new_ratio
                    )

            return compressed_content

        except Exception as e:
            logger.error(f"Error during compression: {e}")
            if max_tokens and content:
                content_tokens = await self.count_tokens(content)
                if content_tokens > max_tokens:
                    char_ratio = max_tokens / content_tokens
                    char_limit = int(len(content) * char_ratio)
                    return content[:char_limit]
            return content

    async def search_web(self, query: str) -> List[Dict]:
        """Perform web search - needs search backend implementation"""
        logger.debug(f"Searching for: {query}")
        
        # Get state for URL tracking
        state = self.get_state()
        url_selected_count = state.get("url_selected_count", {})

        # Calculate additional results based on repeat counts
        repeat_count = sum(1 for count in url_selected_count.values() 
                          if count >= self.config.REPEATS_BEFORE_EXPANSION)
        
        base_results = self.config.SEARCH_RESULTS_PER_QUERY
        additional_results = min(repeat_count, self.config.EXTRA_RESULTS_PER_QUERY)
        total_results = base_results + self.config.EXTRA_RESULTS_PER_QUERY + additional_results

        try:
            # Try SearXNG or other search backend
            encoded_query = quote(query)
            search_url = f"{self.config.SEARCH_URL}{encoded_query}"

            connector = aiohttp.TCPConnector(force_close=True)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(search_url, timeout=15.0) as response:
                    if response.status == 200:
                        try:
                            # Try JSON first
                            search_json = await response.json()
                            results = []

                            if isinstance(search_json, list):
                                for i, item in enumerate(search_json[:total_results]):
                                    results.append({
                                        "title": item.get("title", f"Result {i+1}"),
                                        "url": item.get("url", ""),
                                        "snippet": item.get("snippet", ""),
                                    })
                                return results
                            elif isinstance(search_json, dict) and "results" in search_json:
                                for i, item in enumerate(search_json["results"][:total_results]):
                                    results.append({
                                        "title": item.get("title", f"Result {i+1}"),
                                        "url": item.get("url", ""),
                                        "snippet": item.get("snippet", ""),
                                    })
                                return results
                        except (json.JSONDecodeError, aiohttp.ContentTypeError):
                            # Try HTML parsing
                            try:
                                from bs4 import BeautifulSoup
                                html_content = await response.text()
                                soup = BeautifulSoup(html_content, "html.parser")
                                results = []
                                result_elements = soup.select("article.result")

                                for i, element in enumerate(result_elements[:total_results]):
                                    try:
                                        title_element = element.select_one("h3 a")
                                        url_element = element.select_one("h3 a")
                                        snippet_element = element.select_one("p.content")

                                        title = title_element.get_text() if title_element else f"Result {i+1}"
                                        url = url_element.get("href") if url_element else ""
                                        snippet = snippet_element.get_text() if snippet_element else ""

                                        results.append({
                                            "title": title,
                                            "url": url,
                                            "snippet": snippet,
                                        })
                                    except Exception as e:
                                        logger.warning(f"Error parsing search result {i}: {e}")

                                if results:
                                    return results
                            except ImportError:
                                logger.warning("BeautifulSoup not available for HTML parsing")

        except Exception as e:
            logger.error(f"Search error: {e}")

        # Fallback - return minimal results
        return [{
            "title": f"No results for '{query}'",
            "url": "",
            "snippet": f"No search results were found for the query: {query}",
        }]

    async def fetch_content(self, url: str) -> str:
        """Fetch content from URL with anti-blocking measures"""
        try:
            state = self.get_state()
            url_considered_count = state.get("url_considered_count", {})
            url_results_cache = state.get("url_results_cache", {})
            master_source_table = state.get("master_source_table", {})
            domain_session_map = state.get("domain_session_map", {})

            url_considered_count[url] = url_considered_count.get(url, 0) + 1
            self.update_state("url_considered_count", url_considered_count)

            if url in url_results_cache:
                logger.info(f"Using cached content for URL: {url}")
                return url_results_cache[url]

            parsed_url = urlparse(url)
            domain = parsed_url.netloc

            # Domain-specific rate limiting
            if domain in domain_session_map:
                domain_info = domain_session_map[domain]
                last_access_time = domain_info.get("last_visit", 0)
                current_time = time.time()
                time_since_last_access = current_time - last_access_time

                if time_since_last_access < 3.0:
                    base_delay = 2.0
                    jitter = random.uniform(0.1, 1.0)
                    delay_time = max(0, base_delay - time_since_last_access + jitter)

                    if delay_time > 0.1:
                        logger.info(f"Rate limiting for domain {domain}: Delaying for {delay_time:.2f} seconds")
                        await asyncio.sleep(delay_time)

            # Rotate user agents
            try:
                from fake_useragent import UserAgent
                ua = UserAgent()
                random_user_agent = ua.random
            except ImportError:
                user_agents = [
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
                ]
                random_user_agent = random.choice(user_agents)

            headers = {
                "User-Agent": random_user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Cache-Control": "max-age=0",
            }

            # Update domain tracking
            if domain not in domain_session_map:
                domain_session_map[domain] = {
                    "cookies": {},
                    "last_visit": 0,
                    "visit_count": 0,
                }

            domain_session_map[domain]["visit_count"] += 1
            domain_session_map[domain]["last_visit"] = time.time()
            self.update_state("domain_session_map", domain_session_map)

            is_pdf = url.lower().endswith(".pdf")
            
            connector = aiohttp.TCPConnector(verify_ssl=False, force_close=True)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, headers=headers, timeout=20.0) as response:
                    if response.status == 200:
                        if is_pdf or "application/pdf" in response.headers.get("Content-Type", "").lower():
                            pdf_content = await response.read()
                            self.is_pdf_content = True
                            extracted_content = await self.extract_text_from_pdf(pdf_content)
                        else:
                            content = await response.text()
                            self.is_pdf_content = False
                            if self.config.EXTRACT_CONTENT_ONLY and content.strip().startswith("<"):
                                extracted_content = await self.extract_text_from_html(content)
                            else:
                                extracted_content = content

                        # Cache the content
                        if extracted_content:
                            tokens = await self.count_tokens(extracted_content)
                            token_limit = self.config.MAX_RESULT_TOKENS * 3
                            if tokens > token_limit:
                                char_limit = int(len(extracted_content) * (token_limit / tokens))
                                extracted_content_to_cache = extracted_content[:char_limit]
                            else:
                                extracted_content_to_cache = extracted_content
                            url_results_cache[url] = extracted_content_to_cache
                        else:
                            url_results_cache[url] = extracted_content

                        self.update_state("url_results_cache", url_results_cache)

                        # Add to master source table
                        if url not in master_source_table:
                            if is_pdf:
                                title = url.split("/")[-1].replace(".pdf", "").replace("-", " ").replace("_", " ")
                                source_type = "pdf"
                            else:
                                title_match = re.search(r"<title>(.*?)</title>", content if not is_pdf else "", re.IGNORECASE | re.DOTALL)
                                if title_match:
                                    title = title_match.group(1).strip()
                                else:
                                    title = parsed_url.netloc
                                source_type = "web"

                            source_id = f"S{len(master_source_table) + 1}"
                            master_source_table[url] = {
                                "id": source_id,
                                "title": title,
                                "content_preview": extracted_content[:500] if extracted_content else "",
                                "source_type": source_type,
                                "accessed_date": self.research_date,
                                "cited_in_sections": set(),
                            }
                            self.update_state("master_source_table", master_source_table)

                        return extracted_content or ""
                    else:
                        logger.error(f"Error fetching URL {url}: HTTP {response.status}")
                        return f"Error fetching content: HTTP status {response.status}"

        except Exception as e:
            logger.error(f"Error fetching content from {url}: {e}")
            return f"Error fetching content: {str(e)}"

    async def extract_text_from_html(self, html_content: str) -> str:
        """Extract meaningful text from HTML"""
        try:
            try:
                from bs4 import BeautifulSoup
                import html

                def extract_with_bs4():
                    unescaped_content = html.unescape(html_content)
                    soup = BeautifulSoup(unescaped_content, "html.parser")

                    # Remove unwanted elements
                    for element in soup(["script", "style", "head", "iframe", "noscript", 
                                       "nav", "header", "footer", "aside", "form"]):
                        element.decompose()

                    # Remove navigation classes
                    nav_patterns = ["menu", "nav", "header", "footer", "sidebar", "dropdown"]
                    for element in soup.find_all(class_=lambda c: c and any(x.lower() in c.lower() for x in nav_patterns)):
                        element.decompose()

                    text = soup.get_text(" ", strip=True)
                    text = re.sub(r" {2,}", " ", text)
                    text = re.sub(r"\.([A-Z])", ". \\1", text)

                    lines = text.split("\n")
                    processed_lines = [re.sub(r"\s+", " ", line).strip() for line in lines if line.strip()]
                    return "\n\n".join(processed_lines)

                loop = asyncio.get_event_loop()
                bs4_extraction_task = loop.run_in_executor(None, extract_with_bs4)
                bs4_result = await asyncio.wait_for(bs4_extraction_task, timeout=5.0)

                if bs4_result and len(bs4_result) > len(html_content) * 0.1:
                    return bs4_result

            except (ImportError, asyncio.TimeoutError, Exception) as e:
                logger.warning(f"BeautifulSoup extraction failed: {e}, using regex fallback")

            # Regex fallback
            import html
            unescaped_content = html.unescape(html_content) if isinstance(html_content, str) else html_content

            # Remove unwanted tags
            content = re.sub(r"<script[^>]*>.*?</script>", " ", unescaped_content, flags=re.DOTALL)
            content = re.sub(r"<style[^>]*>.*?</style>", " ", content, flags=re.DOTALL)
            content = re.sub(r"<head[^>]*>.*?</head>", " ", content, flags=re.DOTALL)
            content = re.sub(r"<nav[^>]*>.*?</nav>", " ", content, flags=re.DOTALL)
            content = re.sub(r"<header[^>]*>.*?</header>", " ", content, flags=re.DOTALL)
            content = re.sub(r"<footer[^>]*>.*?</footer>", " ", content, flags=re.DOTALL)
            content = re.sub(r"<[^>]*>", " ", content)
            content = re.sub(r"\.([A-Z])", ". \\1", content)
            content = re.sub(r"\s+", " ", content).strip()

            return content

        except Exception as e:
            logger.error(f"Error extracting text from HTML: {e}")
            try:
                import html
                unescaped = html.unescape(html_content) if isinstance(html_content, str) else html_content
                text = re.sub(r"<[^>]*>", " ", unescaped)
                text = re.sub(r"\s+", " ", text).strip()
                return text
            except:
                return html_content

    async def extract_text_from_pdf(self, pdf_content) -> str:
        """Extract text from PDF content"""
        if not self.config.HANDLE_PDFS:
            return "PDF processing is disabled in settings."

        if isinstance(pdf_content, str):
            if pdf_content.startswith("%PDF"):
                pdf_content = pdf_content.encode("utf-8", errors="ignore")
            else:
                return "Error: Invalid PDF content format"

        max_pages = self.config.PDF_MAX_PAGES

        try:
            # Try PyPDF2 first
            try:
                from PyPDF2 import PdfReader

                def extract_with_pypdf():
                    try:
                        pdf_file = io.BytesIO(pdf_content)
                        pdf_reader = PdfReader(pdf_file)
                        num_pages = len(pdf_reader.pages)
                        logger.info(f"PDF has {num_pages} pages, extracting up to {max_pages}")

                        text = []
                        for page_num in range(min(num_pages, max_pages)):
                            try:
                                page = pdf_reader.pages[page_num]
                                page_text = page.extract_text() or ""
                                if page_text.strip():
                                    text.append(f"Page {page_num + 1}:\n{page_text}")
                            except Exception as e:
                                logger.warning(f"Error extracting page {page_num}: {e}")

                        full_text = "\n\n".join(text)
                        if num_pages > max_pages:
                            full_text += f"\n\n[Note: This PDF has {num_pages} pages, but only the first {max_pages} were processed.]"

                        return full_text if full_text.strip() else None
                    except Exception as e:
                        logger.error(f"Error in PDF extraction with PyPDF2: {e}")
                        return None

                loop = asyncio.get_event_loop()
                pdf_extract_task = loop.run_in_executor(self.executor, extract_with_pypdf)
                full_text = await pdf_extract_task

                if full_text and full_text.strip():
                    logger.info(f"Successfully extracted text from PDF using PyPDF2: {len(full_text)} chars")
                    return full_text

            except ImportError:
                logger.warning("PyPDF2 not available, trying pdfplumber...")

            # Try pdfplumber as fallback
            try:
                import pdfplumber

                def extract_with_pdfplumber():
                    try:
                        pdf_file = io.BytesIO(pdf_content)
                        with pdfplumber.open(pdf_file) as pdf:
                            num_pages = len(pdf.pages)
                            text = []
                            for i, page in enumerate(pdf.pages[:max_pages]):
                                try:
                                    page_text = page.extract_text() or ""
                                    if page_text.strip():
                                        text.append(f"Page {i + 1}:\n{page_text}")
                                except Exception as page_error:
                                    logger.warning(f"Error extracting page {i} with pdfplumber: {page_error}")

                            full_text = "\n\n".join(text)
                            if num_pages > max_pages:
                                full_text += f"\n\n[Note: This PDF has {num_pages} pages, but only the first {max_pages} were processed.]"

                            return full_text
                    except Exception as e:
                        logger.error(f"Error in PDF extraction with pdfplumber: {e}")
                        return None

                loop = asyncio.get_event_loop()
                pdf_extract_task = loop.run_in_executor(self.executor, extract_with_pdfplumber)
                full_text = await pdf_extract_task

                if full_text and full_text.strip():
                    logger.info(f"Successfully extracted text from PDF using pdfplumber: {len(full_text)} chars")
                    return full_text

            except ImportError:
                logger.warning("pdfplumber not available")

            if pdf_content.startswith(b"%PDF"):
                logger.warning("PDF detected but text extraction failed. May be scanned or encrypted.")
                return "This appears to be a PDF document, but text extraction failed. The PDF may contain scanned images rather than text, or it may be encrypted/protected."

            return "Could not extract text from PDF. The file may not be a valid PDF or may contain security restrictions."

        except Exception as e:
            logger.error(f"PDF text extraction failed: {e}")
            return f"Error extracting text from PDF: {str(e)}"

    async def process_search_result(
        self,
        result: Dict,
        query: str,
        query_embedding: List[float],
        outline_embedding: List[float],
        summary_embedding: Optional[List[float]] = None,
    ) -> Dict:
        """Process a search result to extract and compress content"""
        title = result.get("title", "")
        url = result.get("url", "")
        snippet = result.get("snippet", "")

        if not url:
            return {
                "title": title or f"Result for '{query}'",
                "url": "",
                "content": "This result has no associated URL and cannot be processed.",
                "query": query,
                "valid": False,
            }

        await self.event_emitter.emit_status("info", f"Processing result: {title[:50]}...", False)

        try:
            state = self.get_state()
            url_selected_count = state.get("url_selected_count", {})
            url_token_counts = state.get("url_token_counts", {})
            master_source_table = state.get("master_source_table", {})

            repeat_count = url_selected_count.get(url, 0)

            if (not snippet or len(snippet) < 200) and url:
                await self.event_emitter.emit_status("info", f"Fetching content from URL: {url}...", False)
                content = await self.fetch_content(url)
                if content and len(content) > 200:
                    snippet = content
                else:
                    logger.warning(f"Failed to fetch useful content from URL: {url}")

            if not snippet or len(snippet) < 200:
                return {
                    "title": title or f"Result for '{query}'",
                    "url": url,
                    "content": snippet or "No substantial content available for this result.",
                    "query": query,
                    "valid": False,
                }

            if repeat_count > 0:
                snippet = await self.handle_repeated_content(snippet, url, query_embedding, repeat_count)

            content_tokens = await self.count_tokens(snippet)
            user_preferences = state.get("user_preferences", {})
            pdv = user_preferences.get("pdv")
            max_tokens = await self.scale_token_limit_by_relevance(result, query_embedding, pdv)

            if content_tokens > max_tokens:
                try:
                    await self.event_emitter.emit_status("info", "Truncating content to token limit...", False)
                    char_ratio = max_tokens / content_tokens
                    char_limit = int(len(snippet) * char_ratio)
                    padded_limit = min(len(snippet), int(char_limit * 1.1))
                    truncated_content = snippet[:padded_limit]

                    last_period = truncated_content.rfind(".")
                    if last_period > char_limit * 0.9:
                        truncated_content = truncated_content[:last_period + 1]

                    if truncated_content and len(truncated_content) > 100:
                        url_selected_count[url] = url_selected_count.get(url, 0) + 1
                        self.update_state("url_selected_count", url_selected_count)

                        if url not in url_token_counts:
                            url_token_counts[url] = content_tokens
                            self.update_state("url_token_counts", url_token_counts)

                        if url not in master_source_table:
                            source_type = "pdf" if (url.endswith(".pdf") or self.is_pdf_content) else "web"
                            if not title or title == f"Result for '{query}'":
                                parsed_url = urlparse(url)
                                if source_type == "pdf":
                                    file_name = parsed_url.path.split("/")[-1]
                                    title = file_name.replace(".pdf", "").replace("-", " ").replace("_", " ")
                                else:
                                    title = parsed_url.netloc

                            source_id = f"S{len(master_source_table) + 1}"
                            master_source_table[url] = {
                                "id": source_id,
                                "title": title,
                                "content_preview": truncated_content[:500],
                                "source_type": source_type,
                                "accessed_date": self.research_date,
                                "cited_in_sections": set(),
                            }
                            self.update_state("master_source_table", master_source_table)

                        tokens = await self.count_tokens(truncated_content)
                        result["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                        return {
                            "title": title,
                            "url": url,
                            "content": truncated_content,
                            "query": query,
                            "repeat_count": repeat_count,
                            "tokens": tokens,
                            "valid": True,
                        }
                except Exception as e:
                    logger.error(f"Error in token-based truncation: {e}")

            # Use original content with token limiting
            url_selected_count[url] = url_selected_count.get(url, 0) + 1
            self.update_state("url_selected_count", url_selected_count)

            if url not in url_token_counts:
                url_token_counts[url] = content_tokens
                self.update_state("url_token_counts", url_token_counts)

            if url not in master_source_table:
                source_type = "pdf" if (url.endswith(".pdf") or self.is_pdf_content) else "web"
                if not title or title == f"Result for '{query}'":
                    parsed_url = urlparse(url)
                    if source_type == "pdf":
                        file_name = parsed_url.path.split("/")[-1]
                        title = file_name.replace(".pdf", "").replace("-", " ").replace("_", " ")
                    else:
                        title = parsed_url.netloc

                source_id = f"S{len(master_source_table) + 1}"
                master_source_table[url] = {
                    "id": source_id,
                    "title": title,
                    "content_preview": snippet[:500],
                    "source_type": source_type,
                    "accessed_date": self.research_date,
                    "cited_in_sections": set(),
                }
                self.update_state("master_source_table", master_source_table)

            if content_tokens > max_tokens:
                char_ratio = max_tokens / content_tokens
                char_limit = int(len(snippet) * char_ratio)
                limited_content = snippet[:char_limit]
                tokens = await self.count_tokens(limited_content)
            else:
                limited_content = snippet
                tokens = content_tokens

            result["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            return {
                "title": title,
                "url": url,
                "content": limited_content,
                "query": query,
                "repeat_count": repeat_count,
                "tokens": tokens,
                "valid": True,
            }

        except Exception as e:
            logger.error(f"Unhandled error in process_search_result: {e}")
            error_msg = f"Error processing search result: {str(e)}\n\nOriginal snippet: {snippet[:1000] if snippet else 'No content available'}"
            tokens = await self.count_tokens(error_msg)

            return {
                "title": title or f"Error processing result for '{query}'",
                "url": url,
                "content": error_msg,
                "query": query,
                "repeat_count": repeat_count if "repeat_count" in locals() else 0,
                "tokens": tokens,
                "valid": False,
            }

    async def handle_repeated_content(
        self, content: str, url: str, query_embedding: List[float], repeat_count: int
    ) -> str:
        """Process repeated content with sliding window and adaptive shrinkage"""
        state = self.get_state()
        url_selected_count = state.get("url_selected_count", {})
        url_token_counts = state.get("url_token_counts", {})

        selected_count = url_selected_count.get(url, 0)
        if selected_count < 1:
            total_tokens = await self.count_tokens(content)
            url_token_counts[url] = total_tokens
            self.update_state("url_token_counts", url_token_counts)
            return content

        total_tokens = url_token_counts.get(url, 0)
        if total_tokens == 0:
            total_tokens = await self.count_tokens(content)
            url_token_counts[url] = total_tokens
            self.update_state("url_token_counts", url_token_counts)

        max_tokens = self.config.MAX_RESULT_TOKENS
        window_factor = self.config.REPEAT_WINDOW_FACTOR

        if total_tokens > max_tokens:
            window_start = int((repeat_count - 1) * window_factor * max_tokens)

            if window_start >= total_tokens:
                cycles_completed = window_start // total_tokens
                shrink_factor = 0.7**cycles_completed
                window_size = int(max_tokens * shrink_factor)
                window_size = max(200, window_size)
                window_start = window_start % total_tokens

                logger.info(f"Repeat URL {url} (count: {selected_count}): applying shrinkage after full cycle. "
                           f"Factor: {shrink_factor:.2f}, window size: {window_size} tokens")
            else:
                window_size = max_tokens
                logger.info(f"Repeat URL {url} (count: {selected_count}): sliding window, "
                           f"starting at token {window_start}, window size {window_size}")

            window_content = await self.extract_token_window(content, window_start, window_size)
            return window_content
        else:
            logger.info(f"Repeat URL {url} (count: {selected_count}): applying compression/centering")
            content_embedding = await self.get_embedding(content[:2000])
            if not content_embedding:
                return content

            try:
                chunks = self.chunk_text(content)
                if len(chunks) <= 3:
                    return content

                chunk_embeddings = []
                relevance_scores = []
                for i, chunk in enumerate(chunks):
                    chunk_embedding = await self.get_embedding(chunk[:2000])
                    if chunk_embedding:
                        chunk_embeddings.append(chunk_embedding)
                        relevance = cosine_similarity([chunk_embedding], [query_embedding])[0][0]
                        relevance_scores.append((i, relevance))

                relevance_scores.sort(key=lambda x: x[1], reverse=True)

                if relevance_scores:
                    most_relevant_idx = relevance_scores[0][0]
                    start_idx = max(0, most_relevant_idx - len(chunks) // 4)
                    end_idx = min(len(chunks), most_relevant_idx + len(chunks) // 4 + 1)
                    recentered_content = "\n".join(chunks[start_idx:end_idx])
                    return recentered_content

            except Exception as e:
                logger.error(f"Error re-centering window: {e}")

            return content

    async def extract_token_window(self, content: str, start_token: int, window_size: int) -> str:
        """Extract a window of tokens from content"""
        try:
            total_tokens = await self.count_tokens(content)
            chars_per_token = len(content) / max(1, total_tokens)

            start_char = int(start_token * chars_per_token)
            window_chars = int(window_size * chars_per_token)

            start_char = max(0, min(start_char, len(content) - 1))
            end_char = min(len(content), start_char + window_chars)

            window_content = content[start_char:end_char]

            if start_char > 0:
                first_period = window_content.find(". ")
                if first_period > 0 and first_period < len(window_content) // 10:
                    window_content = window_content[first_period + 2:]

            last_period = window_content.rfind(". ")
            if last_period > 0 and last_period > len(window_content) * 0.9:
                window_content = window_content[:last_period + 1]

            return window_content

        except Exception as e:
            logger.error(f"Error extracting token window: {e}")
            if len(content) > 0:
                safe_start = min(len(content) - 1, max(0, int(len(content) * (start_token / total_tokens))))
                safe_end = min(len(content), safe_start + window_size)
                return content[safe_start:safe_end]
            return content

    async def scale_token_limit_by_relevance(
        self,
        result: Dict,
        query_embedding: List[float],
        pdv: Optional[List[float]] = None,
    ) -> int:
        """Scale token limit based on relevance"""
        base_token_limit = self.config.MAX_RESULT_TOKENS

        if "similarity" not in result:
            return base_token_limit

        similarity = result.get("similarity", 0.5)

        pdv_alignment = 0.5
        if pdv is not None:
            try:
                content = result.get("content", "")
                content_embedding = await self.get_embedding(content[:2000])
                if content_embedding:
                    alignment = np.dot(content_embedding, pdv)
                    pdv_alignment = (alignment + 1) / 2
            except Exception as e:
                logger.error(f"Error calculating PDV alignment: {e}")

        combined_relevance = (similarity * 0.7) + (pdv_alignment * 0.3)
        scaling_factor = 0.5 + (combined_relevance * 1.0)
        scaled_limit = int(base_token_limit * scaling_factor)

        min_limit = int(base_token_limit * 0.5)
        max_limit = int(base_token_limit * 1.5)
        scaled_limit = max(min_limit, min(max_limit, scaled_limit))

        return scaled_limit

    async def process_query(
        self,
        query: str,
        query_embedding: List[float],
        outline_embedding: List[float],
        cycle_feedback: Optional[Dict] = None,
        summary_embedding: Optional[List[float]] = None,
    ) -> List[Dict]:
        """Process a single search query and get results"""
        await self.event_emitter.emit_status("info", f"Searching for: {query}", False)

        sanitized_query = await self.sanitize_query(query)
        search_results = await self.search_web(sanitized_query)
        
        if not search_results:
            await self.event_emitter.emit_message(f"*No results found for query: {query}*\n\n")
            return []

        search_results = await self.select_most_relevant_results(
            search_results, query, query_embedding, outline_embedding, summary_embedding
        )

        successful_results = []
        failed_count = 0

        state = self.get_state()
        all_topics = state.get("all_topics", [])
        rejected_results = []

        for result in search_results:
            if len(successful_results) >= self.config.SUCCESSFUL_RESULTS_PER_QUERY:
                break

            if failed_count >= self.config.MAX_FAILED_RESULTS:
                await self.event_emitter.emit_message(
                    f"*Skipping remaining results for query: {query} after {failed_count} failures*\n\n"
                )
                break

            try:
                processed_result = await self.process_search_result(
                    result, query, query_embedding, outline_embedding, summary_embedding
                )

                if "similarity" in result and "similarity" not in processed_result:
                    processed_result["similarity"] = result["similarity"]

                if (processed_result and processed_result.get("content") and 
                    len(processed_result.get("content", "")) > 200 and 
                    processed_result.get("valid", False) and processed_result.get("url", "")):
                    
                    if "tokens" not in processed_result:
                        processed_result["tokens"] = await self.count_tokens(processed_result["content"])

                    if processed_result["tokens"] < 200:
                        logger.info(f"Skipping result with only {processed_result['tokens']} tokens")
                        continue

                    if (self.config.QUALITY_FILTER_ENABLED and 
                        "similarity" in processed_result and 
                        processed_result["similarity"] < self.config.QUALITY_SIMILARITY_THRESHOLD):
                        
                        is_relevant = await self.check_result_relevance(processed_result, query, all_topics)
                        if not is_relevant:
                            rejected_results.append({
                                "url": processed_result.get("url", ""),
                                "title": processed_result.get("title", ""),
                                "similarity": processed_result.get("similarity", 0),
                                "processed_result": processed_result,
                            })
                            logger.warning(f"Rejected irrelevant result: {processed_result.get('url', '')}")
                            continue

                    successful_results.append(processed_result)

                    document_title = processed_result["title"]
                    if document_title == f"'{query}'" and processed_result["url"]:
                        parsed_url = urlparse(processed_result["url"])
                        path_parts = parsed_url.path.split("/")
                        if path_parts[-1]:
                            file_name = path_parts[-1]
                            if file_name.endswith(".pdf"):
                                document_title = file_name[:-4].replace("-", " ").replace("_", " ")
                            elif "." in file_name:
                                document_title = file_name.split(".")[0].replace("-", " ").replace("_", " ")
                            else:
                                document_title = file_name.replace("-", " ").replace("_", " ")
                        else:
                            document_title = parsed_url.netloc

                    token_count = processed_result.get("tokens", 0)
                    if token_count == 0:
                        token_count = await self.count_tokens(processed_result["content"])

                    if processed_result["url"]:
                        url = processed_result["url"]
                        if url.endswith(".pdf") or "application/pdf" in url or self.is_pdf_content:
                            prefix = "PDF: "
                        else:
                            prefix = "Site: "
                        result_text = f"#### {prefix}{url}\n**Tokens:** {token_count}\n\n"
                    else:
                        result_text = f"#### {document_title} [{token_count} tokens]\n\n"

                    result_text += f"*Search query: {query}*\n\n"

                    content_to_display = processed_result["content"][:self.config.MAX_RESULT_TOKENS]
                    formatted_content = await self.clean_text_formatting(content_to_display)
                    result_text += f"{formatted_content}...\n\n"

                    repeat_count = processed_result.get("repeat_count", 0)
                    if repeat_count > 1:
                        result_text += f"*Note: This URL has been processed {repeat_count} times*\n\n"

                    await self.event_emitter.emit_message(result_text)
                    failed_count = 0
                else:
                    failed_count += 1
                    logger.warning(f"Failed to get substantial content from result for query: {query}")

            except Exception as e:
                failed_count += 1
                logger.error(f"Error processing result for query '{query}': {e}")
                await self.event_emitter.emit_message(f"*Error processing a result for query: {query}*\n\n")

        if not successful_results and rejected_results:
            sorted_rejected = sorted(rejected_results, key=lambda x: x.get("similarity", 0), reverse=True)
            top_rejected = sorted_rejected[0]
            logger.info(f"Using top rejected result as fallback: {top_rejected.get('url', '')}")

            if "processed_result" in top_rejected:
                processed_result = top_rejected["processed_result"]
                successful_results.append(processed_result)

                document_title = processed_result.get("title", f"Result for '{query}'")
                token_count = processed_result.get("tokens", 0) or await self.count_tokens(processed_result["content"])
                url = processed_result.get("url", "")

                result_text = f"#### {document_title} [{token_count} tokens]\n\n"
                if url:
                    result_text = f"#### {'PDF: ' if url.endswith('.pdf') else 'Site: '}{url}\n**Tokens:** {token_count}\n\n"

                result_text += f"*Search query: {query}*\n\n"
                result_text += f"*Note: This result was initially filtered but is used as a fallback.*\n\n"

                content_to_display = processed_result["content"][:self.config.MAX_RESULT_TOKENS]
                formatted_content = await self.clean_text_formatting(content_to_display)
                result_text += f"{formatted_content}...\n\n"

                await self.event_emitter.emit_message(result_text)

        if not successful_results:
            logger.warning(f"No valid results obtained for query: {query}")
            await self.event_emitter.emit_message(f"*No valid results found for query: {query}*\n\n")

        await self.update_token_counts(successful_results)
        return successful_results

    async def sanitize_query(self, query: str) -> str:
        """Sanitize search query"""
        sanitized = query.replace('"', " ").replace('"', " ").replace('"', " ")
        sanitized = " ".join(sanitized.split())
        if len(sanitized) > 250:
            sanitized = sanitized[:250]
        return sanitized

    async def select_most_relevant_results(
        self,
        results: List[Dict],
        query: str,
        query_embedding: List[float],
        outline_embedding: List[float],
        summary_embedding: Optional[List[float]] = None,
    ) -> List[Dict]:
        """Select most relevant results using semantic analysis"""
        if not results:
            return results

        base_results_per_query = self.config.SEARCH_RESULTS_PER_QUERY
        if len(results) <= base_results_per_query:
            return results

        state = self.get_state()
        url_selected_count = state.get("url_selected_count", {})

        repeat_count = sum(1 for count in url_selected_count.values() 
                          if count >= self.config.REPEATS_BEFORE_EXPANSION)
        additional_results = min(repeat_count, self.config.EXTRA_RESULTS_PER_QUERY)
        results_to_select = base_results_per_query + additional_results

        relevance_scores = []
        transformation = state.get("semantic_transformations")
        similarity_cache = state.get("similarity_cache", {})

        # Process domain and content priorities
        priority_domains = []
        if self.config.DOMAIN_PRIORITY:
            domain_items = self.config.DOMAIN_PRIORITY.replace(",", " ").split()
            priority_domains = [item.strip().lower() for item in domain_items if item.strip()]

        priority_keywords = []
        if self.config.CONTENT_PRIORITY:
            def parse_keywords(text):
                keywords = []
                pattern = r"\'([^\']+)\'|\"([^\"]+)\"|(\S+)"
                matches = re.findall(pattern, text)
                for match in matches:
                    keyword = match[0] or match[1] or match[2]
                    if keyword:
                        keywords.append(keyword.lower())
                return keywords
            priority_keywords = parse_keywords(self.config.CONTENT_PRIORITY)

        domain_multiplier = self.config.DOMAIN_MULTIPLIER
        keyword_multiplier_per_match = self.config.KEYWORD_MULTIPLIER_PER_MATCH
        max_keyword_multiplier = self.config.MAX_KEYWORD_MULTIPLIER

        for i, result in enumerate(results):
            try:
                snippet = result.get("snippet", "")
                url = result.get("url", "")

                if len(snippet) < self.config.RELEVANCY_SNIPPET_LENGTH and url:
                    try:
                        await self.event_emitter.emit_status("info", f"Fetching snippet for relevance: {url[:50]}...", False)
                        content_preview = await self.fetch_content(url)
                        if content_preview:
                            snippet = content_preview[:self.config.RELEVANCY_SNIPPET_LENGTH]
                    except Exception as e:
                        logger.error(f"Error fetching content for relevance check: {e}")

                if snippet and len(snippet) > 100:
                    # Check for vocabulary lists
                    words = re.findall(r"\b\w+\b", snippet[:2000].lower())
                    if len(words) > 150:
                        unique_words = set(words)
                        unique_ratio = len(unique_words) / len(words)
                        if unique_ratio > 0.98:
                            logger.warning(f"Skipping likely vocabulary list: {unique_ratio:.3f} uniqueness ratio")
                            similarity = 0.01
                            relevance_scores.append((i, similarity))
                            result["similarity"] = similarity
                            continue

                    snippet_embedding = await self.get_embedding(snippet)
                    if snippet_embedding:
                        if transformation:
                            transformed_query = await self.apply_semantic_transformation(query_embedding, transformation)
                            similarity = cosine_similarity([snippet_embedding], [transformed_query])[0][0]
                        else:
                            similarity = cosine_similarity([snippet_embedding], [query_embedding])[0][0]

                        original_similarity = similarity

                        # Apply domain multiplier
                        if priority_domains and url:
                            url_lower = url.lower()
                            if any(domain in url_lower for domain in priority_domains):
                                similarity *= domain_multiplier
                                logger.debug(f"Applied domain multiplier {domain_multiplier}x to URL: {url}")

                        # Apply keyword multiplier
                        if priority_keywords and snippet:
                            snippet_lower = snippet.lower()
                            keyword_matches = [keyword for keyword in priority_keywords if keyword in snippet_lower]
                            keyword_count = len(keyword_matches)

                            if keyword_count > 0:
                                cumulative_multiplier = min(max_keyword_multiplier, 
                                                          keyword_multiplier_per_match**keyword_count)
                                similarity *= cumulative_multiplier
                                logger.debug(f"Applied keyword multiplier {cumulative_multiplier:.2f}x "
                                           f"({keyword_count} keywords matched) to result {i}")

                        similarity = min(0.99, similarity)
                        result["similarity"] = similarity

                        # Apply repeat penalty
                        repeat_penalty = 1.0
                        url_repeats = url_selected_count.get(url, 0)
                        if url_repeats > 0:
                            repeat_penalty = max(0.5, 1.0 - (0.1 * url_repeats))
                            logger.debug(f"Applied repeat penalty of {repeat_penalty} to URL: {url}")

                        similarity *= repeat_penalty
                        relevance_scores.append((i, similarity))
                        result["similarity"] = similarity

                        if similarity != original_similarity:
                            logger.info(f"Result {i} multiplied: {original_similarity:.3f} → {similarity:.3f}")
                    else:
                        relevance_scores.append((i, 0.1))
                        result["similarity"] = 0.1
                else:
                    relevance_scores.append((i, 0.0))
                    result["similarity"] = 0.0

            except Exception as e:
                logger.error(f"Error calculating relevance for result {i}: {e}")
                relevance_scores.append((i, 0.0))
                result["similarity"] = 0.0

        self.update_state("similarity_cache", similarity_cache)

        relevance_scores.sort(key=lambda x: x[1], reverse=True)
        selected_indices = [x[0] for x in relevance_scores[:results_to_select]]
        selected_results = [results[i] for i in selected_indices]

        logger.info(f"Selected {len(selected_results)} most relevant results from {len(results)} total")

        # Update dimension coverage
        state = self.get_state()
        dims = state.get("research_dimensions")
        if dims and "coverage" in dims:
            coverage = np.array(dims["coverage"])
            all_content = []
            for result in selected_results:
                content = result.get("content", "")[:2000]
                if content:
                    quality = 0.5
                    if "similarity" in result:
                        quality = 0.5 + (result["similarity"] * 0.5)
                    all_content.append((content, quality))

            if all_content:
                for content, quality in all_content:
                    embed = await self.get_embedding(content[:2000])
                    if not embed:
                        continue
                    projection = np.dot(embed, np.array(dims["eigenvectors"]).T)
                    contribution = np.abs(projection) * quality

                    for i in range(min(len(contribution), len(coverage))):
                        coverage[i] += contribution[i] * (1 - coverage[i] / 2)

                coverage = np.minimum(coverage, 3.0) / 3.0
                dims["coverage"] = coverage.tolist()
                self.update_state("research_dimensions", dims)
                self.update_state("latest_dimension_coverage", coverage.tolist())

        return selected_results

    async def check_result_relevance(
        self,
        result: Dict,
        query: str,
        outline_items: Optional[List[str]] = None,
    ) -> bool:
        """Check if result is relevant using quality filter"""
        if not self.config.QUALITY_FILTER_ENABLED:
            return True

        similarity = result.get("similarity", 0.0)
        if similarity >= self.config.QUALITY_SIMILARITY_THRESHOLD:
            logger.info(f"Result passed quality filter automatically with similarity {similarity:.3f}")
            return True

        content = result.get("content", "")
        title = result.get("title", "")
        url = result.get("url", "")

        if not content or len(content) < 200:
            logger.warning("Content too short for quality filtering, accepting by default")
            return True

        relevance_prompt = {
            "role": "system",
            "content": """You are evaluating the relevance of a search result to a research query. 
Your task is to determine if the content is actually relevant to what the user is researching.

Answer with ONLY "Yes" if the content is relevant to the research query or "No" if it is:
- Not related to the core topic
- An advertisement disguised as content
- About a different product/concept with similar keywords
- So general or vague that it provides no substantive information
- Littered with HTML or CSS to the point of being unreadable

Reply with JUST "Yes" or "No" - no explanation or other text.""",
        }

        context = f"Research Query: {query}\n\n"
        if outline_items and len(outline_items) > 0:
            context += "Research Outline Topics:\n"
            for item in outline_items[:5]:
                context += f"- {item}\n"
            context += "\n"

        context += f"Result Title: {title}\n"
        context += f"Result URL: {url}\n\n"
        context += f"Content:\n{content}\n\n"
        context += f"""Is the above content relevant to this query: "{query}"? Answer with ONLY 'Yes' or 'No'."""

        try:
            response = await self.generate_completion(
                self.config.QUALITY_FILTER_MODEL,
                [relevance_prompt, {"role": "user", "content": context}],
                temperature=self.config.TEMPERATURE * 0.2,
            )

            if response and "choices" in response and len(response["choices"]) > 0:
                answer = response["choices"][0]["message"]["content"].strip().lower()
                is_relevant = "yes" in answer.lower() and "no" not in answer.lower()
                logger.info(f"Quality check for result: {'RELEVANT' if is_relevant else 'NOT RELEVANT'} (sim={similarity:.3f})")
                return is_relevant
            else:
                logger.warning("Failed to get response from quality model, accepting by default")
                return True

        except Exception as e:
            logger.error(f"Error in quality filtering: {e}")
            return True

    async def clean_text_formatting(self, content: str) -> str:
        """Clean text formatting by merging short lines"""
        lines = content.split("\n")
        cleaned_lines = []

        for line in lines:
            # Handle repeated character patterns
            repeated_char_pattern = re.compile(r"((.)\2{4,})")
            matches = list(repeated_char_pattern.finditer(line))

            if matches:
                for match in reversed(matches):
                    char_sequence = match.group(1)
                    char = match.group(2)
                    if len(char_sequence) >= 5:
                        replacement = char * 2 + "(...)" + char * 2
                        start, end = match.span()
                        line = line[:start] + replacement + line[end:]

            cleaned_lines.append(line)

        lines = cleaned_lines
        merged_lines = []
        short_line_group = []
        mixed_case_pattern = re.compile(r"[a-z][A-Z]")

        i = 0
        while i < len(lines):
            current_line = lines[i].strip()
            word_count = len(current_line.split())

            if word_count <= 5 and current_line:
                is_numbered_item = False
                number_patterns = [r"^\d+[\.\)\:]", r"^[A-Za-z][\.\)\:]", r".*\d+[\.\)\:]$"]

                for pattern in number_patterns:
                    if re.search(pattern, current_line):
                        is_numbered_item = True
                        break

                if is_numbered_item:
                    if short_line_group:
                        for j, short_line in enumerate(short_line_group):
                            merged_lines.append(short_line)
                        short_line_group = []
                    merged_lines.append(current_line)
                else:
                    short_line_group.append(current_line)
            else:
                if short_line_group:
                    if len(short_line_group) >= 5:
                        mixed_case_count = 0
                        total_lc_to_uc = 0

                        for line in short_line_group:
                            for j in range(1, len(line)):
                                if j > 0 and line[j - 1].islower() and line[j].isupper():
                                    total_lc_to_uc += 1
                            if mixed_case_pattern.search(line):
                                mixed_case_count += 1

                        has_mixed_case = (mixed_case_count >= len(short_line_group) * 0.3) or (total_lc_to_uc >= 3)

                        if merged_lines:
                            for j in range(min(2, len(short_line_group))):
                                merged_lines[-1] += f". {short_line_group[j]}"

                            if has_mixed_case:
                                merged_lines.append("(Navigation menu removed)")
                            else:
                                merged_lines.append("(Headers removed)")

                            last_idx = len(short_line_group) - 2
                            if last_idx >= 2:
                                merged_lines.append(short_line_group[last_idx])
                                merged_lines.append(short_line_group[last_idx + 1])
                        else:
                            for j in range(min(2, len(short_line_group))):
                                merged_lines.append(short_line_group[j])

                            if has_mixed_case:
                                merged_lines.append("(Navigation menu removed)")
                            else:
                                merged_lines.append("(Headers removed)")

                            last_idx = len(short_line_group) - 2
                            if last_idx >= 2:
                                merged_lines.append(short_line_group[last_idx])
                                merged_lines.append(short_line_group[last_idx + 1])
                    else:
                        for j, short_line in enumerate(short_line_group):
                            if j == 0 and merged_lines:
                                merged_lines[-1] += f". {short_line}"
                            else:
                                merged_lines.append(short_line)

                    short_line_group = []

                if current_line:
                    merged_lines.append(current_line)
            i += 1

        # Handle remaining short line group
        if short_line_group:
            if len(short_line_group) >= 5:
                mixed_case_count = 0
                total_lc_to_uc = 0

                for line in short_line_group:
                    for j in range(1, len(line)):
                        if j > 0 and line[j - 1].islower() and line[j].isupper():
                            total_lc_to_uc += 1
                    if mixed_case_pattern.search(line):
                        mixed_case_count += 1

                has_mixed_case = (mixed_case_count >= len(short_line_group) * 0.3) or (total_lc_to_uc >= 3)

                if merged_lines:
                    for j in range(min(2, len(short_line_group))):
                        merged_lines[-1] += f". {short_line_group[j]}"

                    if has_mixed_case:
                        merged_lines.append("(Navigation menu removed)")
                    else:
                        merged_lines.append("(Headers removed)")

                    last_idx = len(short_line_group) - 2
                    if last_idx >= 2:
                        merged_lines.append(short_line_group[last_idx])
                        merged_lines.append(short_line_group[last_idx + 1])
            else:
                for j, short_line in enumerate(short_line_group):
                    if j == 0 and merged_lines:
                        merged_lines[-1] += f". {short_line}"
                    else:
                        merged_lines.append(short_line)

        return "\n".join(merged_lines)

    async def update_token_counts(self, new_results=None):
        """Update token counts consistently"""
        state = self.get_state()
        memory_stats = state.get("memory_stats", {
            "results_tokens": 0,
            "section_tokens": {},
            "synthesis_tokens": 0,
            "total_tokens": 0,
        })

        if new_results:
            for result in new_results:
                tokens = result.get("tokens", 0)
                if tokens == 0 and "content" in result:
                    tokens = await self.count_tokens(result["content"])
                    result["tokens"] = tokens
                memory_stats["results_tokens"] += tokens

        results_history = state.get("results_history", [])
        if memory_stats["results_tokens"] == 0 and results_history:
            total_tokens = 0
            for result in results_history:
                tokens = result.get("tokens", 0)
                if tokens == 0 and "content" in result:
                    tokens = await self.count_tokens(result["content"])
                    result["tokens"] = tokens
                total_tokens += tokens
            memory_stats["results_tokens"] = total_tokens

        section_tokens_sum = sum(memory_stats.get("section_tokens", {}).values())
        memory_stats["total_tokens"] = (
            memory_stats["results_tokens"] + 
            section_tokens_sum + 
            memory_stats.get("synthesis_tokens", 0)
        )

        self.update_state("memory_stats", memory_stats)
        return memory_stats

    async def apply_semantic_transformation(self, embedding, transformation):
        """Apply semantic transformation to an embedding"""
        if not transformation or not embedding:
            return embedding

        try:
            embedding_array = np.array(embedding)

            if isinstance(transformation, str):
                logger.warning(f"Transformation ID not found: {transformation}")
                return embedding

            transform_matrix = np.array(transformation["matrix"])

            if (np.isnan(embedding_array).any() or np.isnan(transform_matrix).any() or
                np.isinf(embedding_array).any() or np.isinf(transform_matrix).any()):
                logger.warning("Invalid values in embedding or transformation matrix")
                return embedding

            transformed = np.dot(embedding_array, transform_matrix)

            if np.isnan(transformed).any() or np.isinf(transformed).any():
                logger.warning("Transformation produced invalid values")
                return embedding

            norm = np.linalg.norm(transformed)
            if norm > 1e-10:
                transformed = transformed / norm
                return transformed.tolist()
            else:
                logger.warning("Transformation produced zero vector")
                return embedding
        except Exception as e:
            logger.error(f"Error applying semantic transformation: {e}")
            return embedding

    async def generate_bibliography_simple(self, results_history: List[Dict]) -> str:
        """Generate simple bibliography from results"""
        if not results_history:
            return "No sources were referenced in this research."
        
        bibliography = ""
        source_num = 1
        seen_urls = set()
        
        for result in results_history:
            url = result.get("url", "")
            title = result.get("title", "Untitled Source")
            
            if url and url not in seen_urls:
                seen_urls.add(url)
                if url.startswith("http"):
                    url_formatted = f"[{url}]({url})"
                else:
                    url_formatted = url
                
                bibliography += f"[{source_num}] {title}. {url_formatted}\n\n"
                source_num += 1
        
        return bibliography if bibliography else "No sources were referenced in this research."

    async def conduct_research(self, user_query: str) -> str:
        """Main research conductor method"""
        await self.event_emitter.emit_status("info", "Starting deep research...", False)
        await self.event_emitter.emit_message("## Deep Research Mode: Activated\n\n")
        await self.event_emitter.emit_message("I'll search for comprehensive information about your query. This might take a moment...\n\n")

        # Initialize research
        self.conversation_id = f"research_{hash(user_query)}"
        self.reset_state()

        # Generate initial search queries
        await self.event_emitter.emit_status("info", "Generating initial search queries...", False)

        initial_query_prompt = {
            "role": "system",
            "content": f"""You are a post-grad research assistant generating effective search queries.
The user has submitted a research query: "{user_query}".
Based on the user's input, generate 6 initial search queries to begin research and help us delineate the research topic.
Half of the queries should be broad, aimed at identifying and defining the main topic.
The other half should be more specific, designed to find detailed information.

Format your response as a valid JSON object with the following structure:
{{"queries": [
  "search query 1", 
  "search query 2",
  "search query 3",
  "search query 4",
  "search query 5",
  "search query 6"
]}}""",
        }

        query_response = await self.generate_completion(
            self.get_research_model(),
            [initial_query_prompt, {"role": "user", "content": f"Generate initial search queries for: {user_query}"}],
            temperature=self.config.TEMPERATURE,
        )
        query_content = query_response["choices"][0]["message"]["content"]

        try:
            query_json_str = query_content[query_content.find("{"):query_content.rfind("}") + 1]
            query_data = json.loads(query_json_str)
            initial_queries = query_data.get("queries", [])
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error parsing query JSON: {e}")
            initial_queries = [f"information about {user_query}", f"{user_query} details", f"{user_query} overview"]

        await self.event_emitter.emit_message(f"### Initial Research Queries\n\n")
        for i, query in enumerate(initial_queries):
            await self.event_emitter.emit_message(f"**Query {i+1}**: {query}\n\n")

        # Execute initial searches
        outline_embedding = await self.get_embedding(user_query)
        initial_results = []

        for query in initial_queries:
            try:
                query_embedding = await self.get_embedding(query)
                if not query_embedding:
                    query_embedding = [0] * 1536  # Default embedding size for OpenAI
            except Exception as e:
                logger.error(f"Error getting embedding: {e}")
                query_embedding = [0] * 1536

            results = await self.process_query(query, query_embedding, outline_embedding)
            initial_results.extend(results)

        # Generate research outline
        await self.event_emitter.emit_status("info", "Generating research outline...", False)

        outline_prompt = {
            "role": "system",
            "content": f"""You are a post-graduate academic scholar creating a structured research outline.
Based on the user's query and initial search results, create a comprehensive outline to address: "{user_query}".

The outline must:
1. Break down the query into key concepts that need research
2. Be organized hierarchically with main topics and subtopics
3. Include topics discovered in search results relevant to the query

Format your response as a valid JSON object:
{{"outline": [
  {{"topic": "Main topic 1", "subtopics": ["Subtopic 1.1", "Subtopic 1.2"]}},
  {{"topic": "Main topic 2", "subtopics": ["Subtopic 2.1", "Subtopic 2.2"]}}
]}}""",
        }

        outline_context = f"Original query: {user_query}\n\n### Initial Search Results:\n\n"
        for i, result in enumerate(initial_results):
            outline_context += f"Result {i+1}: {result['title']}\n"
            outline_context += f"Content: {result['content'][:500]}...\n\n"

        outline_response = await self.generate_completion(
            self.get_research_model(),
            [outline_prompt, {"role": "user", "content": outline_context}]
        )
        outline_content = outline_response["choices"][0]["message"]["content"]

        try:
            outline_json_str = outline_content[outline_content.find("{"):outline_content.rfind("}") + 1]
            outline_data = json.loads(outline_json_str)
            research_outline = outline_data.get("outline", [])
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error parsing outline JSON: {e}")
            research_outline = [
                {"topic": "Background Information", "subtopics": ["Overview", "Key Concepts"]},
                {"topic": "Detailed Analysis", "subtopics": ["Specific Aspects", "Examples"]},
            ]

        # Display outline
        outline_text = "### Research Outline\n\n"
        for topic in research_outline:
            outline_text += f"**{topic['topic']}**\n"
            for subtopic in topic.get("subtopics", []):
                outline_text += f"- {subtopic}\n"
            outline_text += "\n"

        await self.event_emitter.emit_message(outline_text)

        # Interactive outline feedback (re-enabled)
        if self.config.INTERACTIVE_RESEARCH:
            await self.event_emitter.emit_message("\n### 🔍 Research Outline Feedback\n\n")
            await self.event_emitter.emit_message("**Please provide feedback on this research outline.**\n\n")
            await self.event_emitter.emit_message("You can:\n")
            await self.event_emitter.emit_message("- Use commands like `/keep 1,3,5-7` or `/remove 2,4,8-10` to select specific items by number\n")
            await self.event_emitter.emit_message("- Or simply describe what topics you want to focus on or avoid in natural language\n\n")
            await self.event_emitter.emit_message("Examples:\n")
            await self.event_emitter.emit_message("- `/k 1,3,5-7` (keep only items 1,3,5,6,7)\n")
            await self.event_emitter.emit_message("- `/r 2,4,8-10` (remove items 2,4,8,9,10)\n")
            await self.event_emitter.emit_message('- "Focus on historical aspects and avoid technical details"\n')
            await self.event_emitter.emit_message('- "I\'m more interested in practical applications"\n\n')
            await self.event_emitter.emit_message("If you want to continue with all items, just press Enter or type 'continue'.\n\n")
            
            # Get user feedback
            try:
                print("💬 Your feedback: ", end='', flush=True)
                user_feedback = input().strip()
                
                if user_feedback and user_feedback.lower() != 'continue':
                    # Process the feedback
                    feedback_result = await self.process_outline_feedback_cli(
                        user_feedback, research_outline, all_topics, user_query
                    )
                    
                    if feedback_result:
                        # Update research outline based on feedback
                        research_outline = feedback_result.get("updated_outline", research_outline)
                        all_topics = feedback_result.get("updated_topics", all_topics)
                        
                        # Re-display updated outline
                        await self.event_emitter.emit_message("\n### ✅ Updated Research Outline\n\n")
                        for topic in research_outline:
                            await self.event_emitter.emit_message(f"**{topic['topic']}**\n")
                            for subtopic in topic.get("subtopics", []):
                                await self.event_emitter.emit_message(f"- {subtopic}\n")
                            await self.event_emitter.emit_message("\n")
                        
                        # Re-create outline embedding
                        outline_text = " ".join(all_topics)
                        outline_embedding = await self.get_embedding(outline_text)
                
                await self.event_emitter.emit_message("*Continuing with research outline...*\n\n")
                
            except (EOFError, KeyboardInterrupt):
                await self.event_emitter.emit_message("\n*No feedback provided, continuing with original outline...*\n\n")
        else:
            await self.event_emitter.emit_message("*Interactive research disabled, continuing with outline...*\n\n")

        # Create flat list of topics
        all_topics = []
        for topic_item in research_outline:
            all_topics.append(topic_item["topic"])
            all_topics.extend(topic_item.get("subtopics", []))

        # Initialize research state
        await self.initialize_research_state(user_query, research_outline, all_topics, outline_embedding, initial_results)

        # Conduct research cycles
        cycle = 1
        max_cycles = self.config.MAX_CYCLES
        min_cycles = self.config.MIN_CYCLES
        completed_topics = set()
        irrelevant_topics = set()
        search_history = []
        results_history = initial_results.copy()
        active_outline = all_topics.copy()
        cycle_summaries = []

        await self.event_emitter.emit_message("\n*Beginning comprehensive research cycles...*\n\n")

        while cycle < max_cycles and active_outline:
            cycle += 1
            await self.event_emitter.emit_status("info", f"Research cycle {cycle}/{max_cycles}: Generating queries...", False)

            # Generate queries for this cycle
            priority_topics = active_outline[:6]  # Focus on top topics
            
            cycle_queries = []
            for topic in priority_topics:
                query = f"{user_query} {topic}"
                cycle_queries.append({"query": query, "topic": topic})

            await self.event_emitter.emit_message(f"### Research Cycle {cycle}: Search Queries\n\n")
            for i, query_obj in enumerate(cycle_queries):
                query = query_obj.get("query", "")
                topic = query_obj.get("topic", "")
                await self.event_emitter.emit_message(f"**Query {i+1}**: {query}\n**Topic**: {topic}\n\n")

            # Execute searches
            cycle_results = []
            for query_obj in cycle_queries:
                query = query_obj.get("query", "")
                
                try:
                    query_embedding = await self.get_embedding(query)
                    if not query_embedding:
                        query_embedding = [0] * 1536
                except Exception as e:
                    logger.error(f"Error getting embedding: {e}")
                    query_embedding = [0] * 1536

                results = await self.process_query(query, query_embedding, outline_embedding)
                cycle_results.extend(results)
                results_history.extend(results)
                search_history.append(query)

            # Analyze results and update outline
            if cycle_results:
                await self.event_emitter.emit_status("info", "Analyzing search results...", False)
                
                analysis_prompt = {
                    "role": "system",
                    "content": f"""You are analyzing search results for cycle {cycle} of {max_cycles}.
Examine the results and classify topics as:
- COMPLETED: Topics adequately addressed with researched information
- PARTIAL: Topics with minimal information needing more research
- IRRELEVANT: Topics not relevant to the main query or distractions
- NEW: New topics discovered that should be added

Original query: "{user_query}"

Format as JSON:
{{
  "completed_topics": ["Topic 1"],
  "partial_topics": ["Topic 2"],
  "irrelevant_topics": ["Topic 3"],
  "new_topics": ["Topic 4"],
  "analysis": "Brief analysis of findings"
}}""",
                }

                analysis_context = f"Current topics: {', '.join(active_outline)}\n\n"
                analysis_context += "Latest results:\n"
                for i, result in enumerate(cycle_results):
                    analysis_context += f"Result {i+1}: {result['title']}\n"
                    analysis_context += f"Content: {result['content'][:300]}...\n\n"

                try:
                    analysis_response = await self.generate_completion(
                        self.get_research_model(),
                        [analysis_prompt, {"role": "user", "content": analysis_context}]
                    )
                    analysis_content = analysis_response["choices"][0]["message"]["content"]
                    
                    analysis_json_str = analysis_content[analysis_content.find("{"):analysis_content.rfind("}") + 1]
                    analysis_data = json.loads(analysis_json_str)

                    newly_completed = set(analysis_data.get("completed_topics", []))
                    completed_topics.update(newly_completed)
                    
                    newly_irrelevant = set(analysis_data.get("irrelevant_topics", []))
                    irrelevant_topics.update(newly_irrelevant)
                    
                    new_topics = analysis_data.get("new_topics", [])
                    for topic in new_topics:
                        if topic not in all_topics and topic not in completed_topics and topic not in irrelevant_topics:
                            active_outline.append(topic)
                            all_topics.append(topic)

                    active_outline = [topic for topic in active_outline 
                                    if topic not in completed_topics and topic not in irrelevant_topics]

                    cycle_summaries.append(analysis_data.get("analysis", f"Analysis for cycle {cycle}"))

                    # Display analysis
                    analysis_text = f"### Research Analysis (Cycle {cycle})\n\n"
                    analysis_text += f"{analysis_data.get('analysis', 'Analysis not available.')}\n\n"

                    if newly_completed:
                        analysis_text += "**Topics Completed:**\n"
                        for topic in newly_completed:
                            analysis_text += f"✓ {topic}\n"
                        analysis_text += "\n"

                    if analysis_data.get("partial_topics"):
                        partial_topics = analysis_data.get("partial_topics")
                        analysis_text += "**Topics Partially Addressed:**\n"
                        for topic in partial_topics[:5]:
                            analysis_text += f"⚪ {topic}\n"
                        if len(partial_topics) > 5:
                            analysis_text += f"...and {len(partial_topics) - 5} more\n"
                        analysis_text += "\n"

                    if newly_irrelevant:
                        analysis_text += "**Irrelevant Topics:**\n"
                        for topic in newly_irrelevant:
                            analysis_text += f"✗ {topic}\n"
                        analysis_text += "\n"

                    if new_topics:
                        analysis_text += "**New Topics Discovered:**\n"
                        for topic in new_topics:
                            analysis_text += f"+ {topic}\n"
                        analysis_text += "\n"

                    if active_outline:
                        analysis_text += "**Remaining Topics:**\n"
                        for topic in active_outline[:5]:
                            analysis_text += f"□ {topic}\n"
                        if len(active_outline) > 5:
                            analysis_text += f"...and {len(active_outline) - 5} more\n"
                        analysis_text += "\n"

                    await self.event_emitter.emit_message(analysis_text)

                except Exception as e:
                    logger.error(f"Error analyzing results: {e}")
                    # Mark one topic as completed to ensure progress
                    if active_outline:
                        completed_topic = active_outline[0]
                        completed_topics.add(completed_topic)
                        active_outline.remove(completed_topic)
                        await self.event_emitter.emit_message(f"**Topic Addressed:** {completed_topic}\n\n")
                        cycle_summaries.append(f"Completed topic: {completed_topic}")

            # Check termination criteria
            if not active_outline:
                await self.event_emitter.emit_status("info", "All research topics addressed!", False)
                break

            if cycle >= min_cycles and len(completed_topics) / len(all_topics) > 0.7:
                await self.event_emitter.emit_status("info", "Most topics addressed. Finalizing...", False)
                break

            if cycle >= max_cycles:
                await self.event_emitter.emit_status("info", f"Maximum cycles ({max_cycles}) reached. Finalizing...", False)
                break

            await self.event_emitter.emit_status("info", f"Cycle {cycle} complete. Moving to next cycle...", False)

        # Synthesis phase
        await self.event_emitter.emit_status("info", "Beginning synthesis...", False)
        await self.event_emitter.emit_message("\n\n---\n\n### Research Complete\n\n")

        # Generate synthesis outline
        synthesis_outline = await self.generate_synthesis_outline(research_outline, completed_topics, user_query, results_history)
        if not synthesis_outline:
            synthesis_outline = research_outline

        await self.event_emitter.emit_message("### Final Research Outline\n\n")
        for topic_item in synthesis_outline:
            topic = topic_item["topic"]
            subtopics = topic_item.get("subtopics", [])
            await self.event_emitter.emit_message(f"**{topic}**\n")
            for subtopic in subtopics:
                await self.event_emitter.emit_message(f"- {subtopic}\n")
            await self.event_emitter.emit_message("\n")

        # Generate final synthesis
        synthesis_model = self.get_synthesis_model()
        
        # Generate titles
        titles = await self.generate_titles(user_query, " ".join([r.get("content", "")[:500] for r in results_history]))
        
        # Create comprehensive answer
        comprehensive_answer = ""
        main_title = titles.get("main_title", f"Research Report: {user_query}")
        subtitle = titles.get("subtitle", "A Comprehensive Analysis")
        
        comprehensive_answer += f"# {main_title}\n\n## {subtitle}\n\n"
        
        # Generate abstract
        abstract = await self.generate_abstract(user_query, " ".join([r.get("content", "")[:200] for r in results_history]))
        comprehensive_answer += f"## Abstract\n\n{abstract}\n\n"
        
        # Generate introduction
        intro = await self.generate_introduction(user_query, synthesis_outline, results_history)
        comprehensive_answer += f"## Introduction\n\n{intro}\n\n"
        
        # Generate content for each section
        for topic_item in synthesis_outline:
            section_title = topic_item["topic"]
            subtopics = topic_item.get("subtopics", [])
            
            section_content = await self.generate_section_content(
                section_title, subtopics, user_query, results_history, synthesis_model
            )
            comprehensive_answer += f"## {section_title}\n\n{section_content}\n\n"
        
        # Generate conclusion
        conclusion = await self.generate_conclusion(user_query, comprehensive_answer, results_history)
        comprehensive_answer += f"## Conclusion\n\n{conclusion}\n\n"
        
        # Add bibliography
        bibliography = await self.generate_bibliography_simple(results_history)
        comprehensive_answer += f"## Bibliography\n\n{bibliography}\n\n"
        
        # Add research date
        comprehensive_answer += f"*Research conducted on: {self.research_date}*\n\n"
        
        # Store for potential follow-up
        self.update_state("prev_comprehensive_summary", comprehensive_answer)
        self.update_state("research_completed", True)
        
        await self.event_emitter.emit_status("success", "Deep research complete!", True)
        return comprehensive_answer

    async def initialize_research_state(self, user_message, research_outline, all_topics, outline_embedding, initial_results=None):
        """Initialize research state"""
        state = self.get_state()
        
        self.update_state("research_state", {
            "research_outline": research_outline,
            "all_topics": all_topics,
            "outline_embedding": outline_embedding,
            "user_message": user_message,
        })
        
        memory_stats = {
            "results_tokens": 0,
            "section_tokens": {},
            "synthesis_tokens": 0,
            "total_tokens": 0,
        }
        self.update_state("memory_stats", memory_stats)
        
        if initial_results:
            results_tokens = 0
            for result in initial_results:
                tokens = result.get("tokens", 0)
                if tokens == 0 and "content" in result:
                    tokens = await self.count_tokens(result["content"])
                    result["tokens"] = tokens
                results_tokens += tokens
            memory_stats["results_tokens"] = results_tokens
            self.update_state("memory_stats", memory_stats)
        
        self.update_state("results_history", initial_results or [])
        self.update_state("search_history", [])
        self.update_state("completed_topics", set())
        self.update_state("irrelevant_topics", set())
        self.update_state("active_outline", all_topics.copy())
        self.update_state("cycle_summaries", [])
        self.update_state("master_source_table", {})
        self.update_state("url_selected_count", {})
        
        logger.info(f"Research state initialized with {len(all_topics)} topics")

    async def generate_synthesis_outline(self, original_outline, completed_topics, user_query, research_results):
        """Generate refined outline for synthesis"""
        state = self.get_state()
        elapsed_cycles = len(state.get("cycle_summaries", []))
        
        synthesis_outline_prompt = {
            "role": "system",
            "content": f"""You are reorganizing a research outline for a comprehensive report.
Create a refined outline with approximately {round((elapsed_cycles * 0.25) + 2)} main topics and {round((elapsed_cycles * 0.8) + 5)} subtopics.

Original query: "{user_query}"

The outline must:
1. Incorporate relevant topics discovered during research
2. Focus on areas best supported by research results
3. Create logical narrative flow for the final report

Format as JSON:
{{"outline": [
  {{"topic": "Main topic 1", "subtopics": ["Subtopic 1.1", "Subtopic 1.2"]}},
  {{"topic": "Main topic 2", "subtopics": ["Subtopic 2.1", "Subtopic 2.2"]}}
]}}""",
        }

        outline_context = "### Original Outline:\n"
        for topic_item in original_outline:
            outline_context += f"- {topic_item['topic']}\n"
            for subtopic in topic_item.get("subtopics", []):
                outline_context += f"  - {subtopic}\n"

        outline_context += f"\n### Research Results Summary:\n"
        for i, result in enumerate(research_results[-10:]):  # Last 10 results
            outline_context += f"Result {i+1}: {result.get('title', 'Untitled')}\n"

        try:
            response = await self.generate_completion(
                self.get_synthesis_model(),
                [synthesis_outline_prompt, {"role": "user", "content": outline_context}],
                temperature=self.config.SYNTHESIS_TEMPERATURE
            )
            outline_content = response["choices"][0]["message"]["content"]
            
            json_start = outline_content.find("{")
            json_end = outline_content.rfind("}") + 1
            
            if json_start >= 0 and json_end > json_start:
                outline_json_str = outline_content[json_start:json_end]
                outline_data = json.loads(outline_json_str)
                synthesis_outline = outline_data.get("outline", [])
                if synthesis_outline:
                    return synthesis_outline
            
            return original_outline
            
        except Exception as e:
            logger.error(f"Error generating synthesis outline: {e}")
            return original_outline

    async def generate_titles(self, user_message, content_sample):
        """Generate main title and subtitle"""
        titles_prompt = {
            "role": "system",
            "content": """Create a main title and subtitle for a research report.
- Main title: 5-12 words, clear and focused
- Subtitle: 8-15 words, provides additional context

Format as JSON:
{
  "main_title": "Your proposed main title",
  "subtitle": "Your proposed subtitle"
}""",
        }

        titles_context = f"Research Query: {user_message}\n\nContent Summary: {content_sample[:1000]}..."

        try:
            response = await self.generate_completion(
                self.get_research_model(),
                [titles_prompt, {"role": "user", "content": titles_context}],
                temperature=0.7
            )
            titles_content = response["choices"][0]["message"]["content"]
            
            json_str = titles_content[titles_content.find("{"):titles_content.rfind("}") + 1]
            titles_data = json.loads(json_str)
            
            return {
                "main_title": titles_data.get("main_title", f"Research Report: {user_message}"),
                "subtitle": titles_data.get("subtitle", "A Comprehensive Analysis")
            }
        except Exception as e:
            logger.error(f"Error generating titles: {e}")
            return {
                "main_title": f"Research Report: {user_message[:50]}",
                "subtitle": "A Comprehensive Analysis and Synthesis"
            }

    async def generate_abstract(self, user_message, content_summary):
        """Generate abstract for the research report"""
        abstract_prompt = {
            "role": "system",
            "content": f"""Write a concise academic abstract (150-250 words) for a research report about: "{user_message}".

The abstract should:
1. Outline the research objective
2. Summarize key findings
3. Be self-contained and understandable
4. Use academic yet accessible tone

Respond with only the abstract text.""",
        }

        try:
            response = await self.generate_completion(
                self.get_synthesis_model(),
                [abstract_prompt, {"role": "user", "content": f"Research content: {content_summary}"}],
                temperature=self.config.SYNTHESIS_TEMPERATURE
            )
            return response["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Error generating abstract: {e}")
            return f"This research report addresses the query: '{user_message}'. It synthesizes information from multiple sources to provide a comprehensive analysis of the topic."

    async def generate_introduction(self, user_query, synthesis_outline, results_history):
        """Generate introduction section"""
        intro_prompt = {
            "role": "system",
            "content": f"""Write a concise introduction (2-3 paragraphs) for a research report about: "{user_query}".

The introduction should:
1. Set the stage for the subject matter
2. Introduce the research objective
3. Briefly outline the approach taken

Respond with only the introduction text.""",
        }

        context = f"Research Query: {user_query}\n\nOutline:\n"
        for section in synthesis_outline:
            context += f"- {section['topic']}\n"

        try:
            response = await self.generate_completion(
                self.get_synthesis_model(),
                [intro_prompt, {"role": "user", "content": context}],
                temperature=self.config.SYNTHESIS_TEMPERATURE * 0.8
            )
            return response["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Error generating introduction: {e}")
            return f"This research report addresses the query: '{user_query}'. The following sections present findings from a comprehensive investigation of this topic."

    async def generate_section_content(self, section_title, subtopics, user_query, research_results, synthesis_model):
        """Generate content for a section"""
        section_prompt = {
            "role": "system",
            "content": f"""Write comprehensive content for the section "{section_title}" covering these subtopics: {', '.join(subtopics)}.

The content should:
1. Address each subtopic thoroughly
2. Use information from the research results
3. Be well-structured with clear flow
4. Be 3-5 paragraphs in length

Focus on factual information and avoid speculation.""",
        }

        # Find relevant results for this section
        relevant_results = []
        section_keywords = section_title.lower().split()
        
        for result in research_results:
            content = result.get("content", "").lower()
            title = result.get("title", "").lower()
            
            # Simple relevance check
            if any(keyword in content or keyword in title for keyword in section_keywords):
                relevant_results.append(result)
        
        # Use top 5 most relevant results
        relevant_results = relevant_results[:5]
        
        context = f"Section: {section_title}\nSubtopics: {', '.join(subtopics)}\n\nRelevant Research Results:\n"
        for i, result in enumerate(relevant_results):
            context += f"Result {i+1}: {result.get('title', 'Untitled')}\n"
            context += f"Content: {result.get('content', '')[:800]}...\n\n"

        try:
            response = await self.generate_completion(
                synthesis_model,
                [section_prompt, {"role": "user", "content": context}],
                temperature=self.config.SYNTHESIS_TEMPERATURE
            )
            return response["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Error generating section content: {e}")
            return f"This section covers {section_title} with focus on {', '.join(subtopics)}. Content synthesis encountered an error."

    async def generate_conclusion(self, user_query, comprehensive_answer, results_history):
        """Generate conclusion section"""
        conclusion_prompt = {
            "role": "system",
            "content": f"""Write a comprehensive conclusion (2-4 paragraphs) for a research report about: "{user_query}".

The conclusion should:
1. Restate the research objective
2. Highlight the most important findings
3. Focus on what we know about the topic
4. Provide a definitive summary

Respond with only the conclusion text.""",
        }

        # Create compressed context from the comprehensive answer
        context_summary = comprehensive_answer[:2000] if comprehensive_answer else ""
        context = f"Research Query: {user_query}\n\nReport Summary: {context_summary}..."

        try:
            response = await self.generate_completion(
                self.get_synthesis_model(),
                [conclusion_prompt, {"role": "user", "content": context}],
                temperature=self.config.SYNTHESIS_TEMPERATURE
            )
            return response["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Error generating conclusion: {e}")
            return f"This research has provided comprehensive insights into {user_query}, synthesizing information from multiple authoritative sources to address the key aspects of this topic."

    async def process_outline_feedback_cli(self, user_input: str, outline_items: List[Dict], all_topics: List[str], original_query: str) -> Dict:
        """Process user feedback on research outline in CLI"""
        user_input = user_input.strip()
        
        # If user just wants to continue
        if user_input.lower() in ['continue', 'c', '']:
            return None
        
        # Create flat numbered list for processing
        flat_items = []
        numbered_outline = []
        item_num = 1
        
        for topic_item in outline_items:
            topic = topic_item.get("topic", "")
            subtopics = topic_item.get("subtopics", [])
            
            flat_items.append(topic)
            numbered_outline.append(f"{item_num}. {topic}")
            item_num += 1
            
            for subtopic in subtopics:
                flat_items.append(subtopic)
                numbered_outline.append(f"{item_num}. {subtopic}")
                item_num += 1
        
        # Process slash commands
        slash_keep_patterns = [r"^/k\s", r"^/keep\s"]
        slash_remove_patterns = [r"^/r\s", r"^/remove\s"]
        
        is_keep_cmd = any(re.match(pattern, user_input) for pattern in slash_keep_patterns)
        is_remove_cmd = any(re.match(pattern, user_input) for pattern in slash_remove_patterns)
        
        if is_keep_cmd or is_remove_cmd:
            # Extract indices/ranges
            if is_keep_cmd:
                items_part = re.sub(r"^(/k|/keep)\s+", "", user_input).replace(",", " ")
            else:
                items_part = re.sub(r"^(/r|/remove)\s+", "", user_input).replace(",", " ")
            
            selected_indices = set()
            for part in items_part.split():
                part = part.strip()
                if not part:
                    continue
                
                if "-" in part:
                    try:
                        start, end = map(int, part.split("-"))
                        if 1 <= start <= len(flat_items) and 1 <= end <= len(flat_items):
                            selected_indices.update(range(start-1, end))  # Convert to 0-indexed
                    except ValueError:
                        await self.event_emitter.emit_message(f"⚠️ Invalid range format: '{part}'\n")
                else:
                    try:
                        idx = int(part)
                        if 1 <= idx <= len(flat_items):
                            selected_indices.add(idx-1)  # Convert to 0-indexed
                    except ValueError:
                        await self.event_emitter.emit_message(f"⚠️ Invalid number: '{part}'\n")
            
            selected_indices = sorted(list(selected_indices))
            
            if is_keep_cmd:
                kept_indices = selected_indices
                removed_indices = [i for i in range(len(flat_items)) if i not in kept_indices]
            else:
                removed_indices = selected_indices
                kept_indices = [i for i in range(len(flat_items)) if i not in removed_indices]
            
            kept_items = [flat_items[i] for i in kept_indices]
            removed_items = [flat_items[i] for i in removed_indices]
            
        else:
            # Process natural language feedback
            nl_feedback = await self.process_natural_language_feedback(user_input, flat_items)
            kept_items = nl_feedback.get("kept_items", flat_items)
            removed_items = nl_feedback.get("removed_items", [])
            kept_indices = nl_feedback.get("kept_indices", list(range(len(flat_items))))
            removed_indices = nl_feedback.get("removed_indices", [])
        
        # Show what's happening
        if removed_items:
            await self.event_emitter.emit_message(f"\n✅ **Keeping {len(kept_items)} items, removing {len(removed_items)} items**\n\n")
            
            if len(removed_items) <= 10:  # Show details if not too many
                removed_list = "\n".join([f"✗ {item}" for item in removed_items])
                await self.event_emitter.emit_message(f"**Removed:**\n{removed_list}\n\n")
        
        # Calculate preference direction vector
        preference_vector = await self.calculate_preference_direction_vector(kept_items, removed_items, flat_items)
        self.update_state("user_preferences", preference_vector)
        
        # Generate replacement topics if needed
        if removed_items:
            await self.event_emitter.emit_message("🔄 **Generating replacement topics...**\n\n")
            replacement_topics = await self.generate_replacement_topics_simple(
                original_query, kept_items, removed_items, len(removed_items)
            )
            
            if replacement_topics:
                await self.event_emitter.emit_message("**New topics:**\n")
                for topic in replacement_topics:
                    await self.event_emitter.emit_message(f"+ {topic}\n")
                await self.event_emitter.emit_message("\n")
                
                # Add new topics to kept items
                kept_items.extend(replacement_topics)
        
        # Rebuild outline structure
        new_outline = await self.rebuild_outline_structure(kept_items, original_query)
        new_all_topics = kept_items.copy()
        
        return {
            "updated_outline": new_outline,
            "updated_topics": new_all_topics,
            "kept_items": kept_items,
            "removed_items": removed_items,
            "preference_vector": preference_vector
        }

    async def process_natural_language_feedback(self, user_message: str, flat_items: List[str]) -> Dict:
        """Process natural language feedback to determine which topics to keep/remove"""
        interpret_prompt = {
            "role": "system",
            "content": """You are analyzing user feedback on a research outline.
Based on the user's natural language input, determine which research topics should be kept or removed.

Analyze the user's message to identify:
1. Which topics align with their interests (keep)
2. Which topics should be removed based on their preferences (remove)

Provide your response as a JSON object with two lists: "keep" for indices to keep, and "remove" for indices to remove.
Indices should be 0-based (first item is index 0).""",
        }

        topics_list = "\n".join([f"{i}. {topic}" for i, topic in enumerate(flat_items)])
        context = f"""Research outline topics:
{topics_list}

User feedback: "{user_message}"

Based on this feedback, categorize each topic (by index) as either "keep" or "remove"."""

        try:
            response = await self.generate_completion(
                self.get_research_model(),
                [interpret_prompt, {"role": "user", "content": context}],
                temperature=self.config.TEMPERATURE * 0.3,
            )

            result_content = response["choices"][0]["message"]["content"]
            
            try:
                json_str = result_content[result_content.find("{"):result_content.rfind("}") + 1]
                result_data = json.loads(json_str)
                
                keep_indices = result_data.get("keep", [])
                remove_indices = result_data.get("remove", [])
                
                if not isinstance(keep_indices, list):
                    keep_indices = []
                if not isinstance(remove_indices, list):
                    remove_indices = []
                
                # Ensure all indices are covered
                all_indices = set(range(len(flat_items)))
                missing_indices = all_indices - set(keep_indices) - set(remove_indices)
                keep_indices.extend(missing_indices)
                
                kept_items = [flat_items[i] for i in keep_indices if i < len(flat_items)]
                removed_items = [flat_items[i] for i in remove_indices if i < len(flat_items)]
                
                return {
                    "kept_items": kept_items,
                    "removed_items": removed_items,
                    "kept_indices": keep_indices,
                    "removed_indices": remove_indices,
                }
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Error parsing feedback interpretation: {e}")
                return {
                    "kept_items": flat_items,
                    "removed_items": [],
                    "kept_indices": list(range(len(flat_items))),
                    "removed_indices": [],
                }

        except Exception as e:
            logger.error(f"Error interpreting natural language feedback: {e}")
            return {
                "kept_items": flat_items,
                "removed_items": [],
                "kept_indices": list(range(len(flat_items))),
                "removed_indices": [],
            }

    async def calculate_preference_direction_vector(self, kept_items: List[str], removed_items: List[str], all_topics: List[str]) -> Dict:
        """Calculate preference direction vector from kept/removed items"""
        if not kept_items or not removed_items:
            return {"pdv": None, "strength": 0.0, "impact": 0.0}

        try:
            # Get embeddings for kept and removed items
            kept_embeddings = []
            for item in kept_items:
                embedding = await self.get_embedding(item)
                if embedding:
                    kept_embeddings.append(embedding)

            removed_embeddings = []
            for item in removed_items:
                embedding = await self.get_embedding(item)
                if embedding:
                    removed_embeddings.append(embedding)

            if not kept_embeddings or not removed_embeddings:
                return {"pdv": None, "strength": 0.0, "impact": 0.0}

            # Calculate mean vectors
            kept_mean = np.mean(kept_embeddings, axis=0)
            removed_mean = np.mean(removed_embeddings, axis=0)

            if (np.isnan(kept_mean).any() or np.isnan(removed_mean).any() or
                np.isinf(kept_mean).any() or np.isinf(removed_mean).any()):
                return {"pdv": None, "strength": 0.0, "impact": 0.0}

            # Calculate preference direction vector
            pdv = kept_mean - removed_mean
            pdv_norm = np.linalg.norm(pdv)
            
            if pdv_norm < 1e-10:
                return {"pdv": None, "strength": 0.0, "impact": 0.0}

            pdv = pdv / pdv_norm
            strength = np.linalg.norm(kept_mean - removed_mean)
            impact = len(removed_items) / len(all_topics) if all_topics else 0.0

            return {"pdv": pdv.tolist(), "strength": float(strength), "impact": impact}
            
        except Exception as e:
            logger.error(f"Error calculating PDV: {e}")
            return {"pdv": None, "strength": 0.0, "impact": 0.0}

    async def generate_replacement_topics_simple(self, query: str, kept_items: List[str], removed_items: List[str], num_replacements: int) -> List[str]:
        """Generate replacement topics using simple approach"""
        replacement_prompt = {
            "role": "system",
            "content": f"""Generate {num_replacements} replacement research topics for a research outline.
Based on the kept topics and original query, generate new topics that:
1. Are directly relevant to the original query
2. Are conceptually aligned with the kept topics  
3. Avoid concepts related to removed topics
4. Are specific and actionable for research

Generate EXACTLY {num_replacements} replacement topics in a numbered list.""",
        }

        content = f"""Original query: {query}

Kept topics (preferred): {', '.join(kept_items)}
Removed topics (to avoid): {', '.join(removed_items)}

Generate {num_replacements} replacement research topics."""

        try:
            response = await self.generate_completion(
                self.get_research_model(),
                [replacement_prompt, {"role": "user", "content": content}],
                temperature=self.config.TEMPERATURE * 1.1,
            )

            generated_text = response["choices"][0]["message"]["content"]
            lines = generated_text.split("\n")
            replacements = []

            for line in lines:
                match = re.search(r"^\s*\d+\.\s*(.+)$", line)
                if match:
                    topic = match.group(1).strip()
                    if topic and len(topic) > 10:
                        replacements.append(topic)

            if len(replacements) > num_replacements:
                replacements = replacements[:num_replacements]
            elif len(replacements) < num_replacements:
                while len(replacements) < num_replacements:
                    replacements.append(f"Additional research aspect {len(replacements)+1} for {query}")

            return replacements

        except Exception as e:
            logger.error(f"Error generating replacement topics: {e}")
            return [f"Alternative research topic {i+1} for {query}" for i in range(num_replacements)]

    async def rebuild_outline_structure(self, kept_items: List[str], original_query: str) -> List[Dict]:
        """Rebuild outline structure from flat list of kept items"""
        if len(kept_items) <= 3:
            # Simple structure for few items
            return [{"topic": "Research Summary", "subtopics": kept_items}]

        # Group items into topics and subtopics
        rebuild_prompt = {
            "role": "system", 
            "content": f"""Organize these research topics into a hierarchical outline for the query: "{original_query}".

Create main topics with subtopics underneath. Aim for 2-4 main topics with 2-5 subtopics each.

Format as JSON:
{{"outline": [
  {{"topic": "Main topic 1", "subtopics": ["Subtopic 1.1", "Subtopic 1.2"]}},
  {{"topic": "Main topic 2", "subtopics": ["Subtopic 2.1", "Subtopic 2.2"]}}
]}}""",
        }

        items_text = "\n".join([f"- {item}" for item in kept_items])
        context = f"Query: {original_query}\n\nTopics to organize:\n{items_text}"

        try:
            response = await self.generate_completion(
                self.get_research_model(),
                [rebuild_prompt, {"role": "user", "content": context}],
                temperature=self.config.TEMPERATURE * 0.8,
            )

            result_content = response["choices"][0]["message"]["content"]
            json_str = result_content[result_content.find("{"):result_content.rfind("}") + 1]
            result_data = json.loads(json_str)
            
            new_outline = result_data.get("outline", [])
            if new_outline:
                return new_outline

        except Exception as e:
            logger.error(f"Error rebuilding outline: {e}")

        # Fallback: simple grouping
        chunk_size = max(2, len(kept_items) // 3)
        outline = []
        for i in range(0, len(kept_items), chunk_size):
            chunk = kept_items[i:i + chunk_size]
            outline.append({
                "topic": f"Research Area {len(outline) + 1}",
                "subtopics": chunk
            })
        
        return outline
        if not results_history:
            return "No sources were referenced in this research."

        bibliography = ""
        source_num = 1
        seen_urls = set()

        for result in results_history:
            url = result.get("url", "")
            title = result.get("title", "Untitled Source")
            
            if url and url not in seen_urls:
                seen_urls.add(url)
                if url.startswith("http"):
                    url_formatted = f"[{url}]({url})"
                else:
                    url_formatted = url
                
                bibliography += f"[{source_num}] {title}. {url_formatted}\n\n"
                source_num += 1

        return bibliography if bibliography else "No sources were referenced in this research."


async def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(description="Deep Research Tool - Standalone Version")
    parser.add_argument("query", help="Research query")
    parser.add_argument("--api-key", help="OpenAI API key", default=os.getenv("OPENAI_API_KEY"))
    parser.add_argument("--base-url", help="OpenAI API base URL", default="https://api.openai.com/v1")
    parser.add_argument("--model", help="Model to use", default="gpt-3.5-turbo")
    parser.add_argument("--embedding-model", help="Embedding model", default="text-embedding-ada-002")
    parser.add_argument("--verbose", action="store_true", help="Verbose output", default=True)
    parser.add_argument("--search-url", help="Search backend URL", default="http://localhost:8888/search?q=")
    parser.add_argument("--max-cycles", type=int, help="Maximum research cycles", default=15)
    parser.add_argument("--output", help="Output file for results", default=None)
    
    args = parser.parse_args()
    
    if not args.api_key:
        print("Error: OpenAI API key required. Set OPENAI_API_KEY environment variable or use --api-key")
        sys.exit(1)
    
    # Configure research tool
    config = ResearchConfig()
    config.OPENAI_API_KEY = args.api_key
    config.OPENAI_BASE_URL = args.base_url
    config.RESEARCH_MODEL = args.model
    config.EMBEDDING_MODEL = args.embedding_model
    config.SEARCH_URL = args.search_url
    config.MAX_CYCLES = args.max_cycles
    
    # Create event emitter
    event_emitter = EventEmitter(verbose=args.verbose)
    
    # Initialize researcher
    researcher = DeepResearcher(config, event_emitter)
    
    try:
        print(f"🔍 Starting deep research on: {args.query}")
        print(f"📡 Using API: {args.base_url}")
        print(f"🤖 Model: {args.model}")
        print(f"🔍 Search: {args.search_url}")
        print("="*80)
        
        # Conduct research
        result = await researcher.conduct_research(args.query)
        
        print("\n" + "="*80)
        print("📊 RESEARCH RESULTS")
        print("="*80)
        print(result)
        
        # Save to file if requested
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(result)
            print(f"\n💾 Results saved to: {args.output}")
        
        # Display statistics
        cache_stats = researcher.embedding_cache.stats()
        print(f"\n📈 Cache Statistics:")
        print(f"   Embedding cache hits: {cache_stats['hits']}")
        print(f"   Cache hit rate: {cache_stats['hit_rate']:.2%}")
        
    except KeyboardInterrupt:
        print("\n⚠️ Research interrupted by user")
    except Exception as e:
        print(f"❌ Error during research: {e}")
        logger.error(f"Research error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
