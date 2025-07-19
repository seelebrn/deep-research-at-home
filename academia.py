import xml.etree.ElementTree as ET
import urllib.parse
from typing import Dict, List, Optional, Any
import re
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
import spacy
import re
from collections import Counter
from typing import List, Dict
import asyncio
import aiohttp
import logging

class AdvancedKeywordExtractor:
    def __init__(self):
        """Initialize with French model, fallback to English"""
        self.nlp = None
        try:
            # Try French model first (better for Université de Lille)
            self.nlp = spacy.load("fr_core_news_sm")
            logger.info("Loaded French spaCy model")
        except OSError:
            try:
                # Fallback to English
                self.nlp = spacy.load("en_core_web_sm")
                logger.info("Loaded English spaCy model")
            except OSError:
                logger.error("No spaCy models found. Install with: python -m spacy download fr_core_news_sm")
                raise
    
    def extract_keywords(self, query: str, max_keywords: int = 6) -> str:
        """Extract keywords using NLP techniques"""
        if not self.nlp:
            return self._fallback_extraction(query)
        
        # Process the text
        doc = self.nlp(query)
        
        keywords = []
        
        # 1. Extract Named Entities (people, organizations, locations, etc.)
        for ent in doc.ents:
            if ent.label_ in ['PERSON', 'ORG', 'MISC', 'LOC', 'EVENT', 'PRODUCT']:
                # Clean and add entity
                entity_text = re.sub(r'[^\w\s-]', '', ent.text.lower().strip())
                if len(entity_text) > 2:
                    keywords.append(entity_text)
        
        # 2. Extract important nouns, adjectives, and verbs
        for token in doc:
            if (token.pos_ in ['NOUN', 'ADJ', 'VERB'] and 
                not token.is_stop and 
                not token.is_punct and 
                not token.is_space and
                len(token.text) > 2):
                
                # Use lemma (base form) for better matching
                lemma = token.lemma_.lower()
                
                # Skip common academic question words
                if lemma not in ['allow', 'permet', 'person', 'personne', 'certain', 'what', 'comment']:
                    keywords.append(lemma)
        
        # 3. Handle compound terms and technical phrases
        keywords = self._handle_compound_terms(keywords, doc)
        
        # 4. Count frequency and get most important terms
        keyword_counts = Counter(keywords)
        
        # Prioritize longer, more specific terms
        weighted_keywords = []
        for keyword, count in keyword_counts.items():
            # Give bonus to longer terms and hyphenated terms
            weight = count
            if len(keyword) > 6:
                weight += 1
            if '-' in keyword:
                weight += 1
            weighted_keywords.append((keyword, weight))
        
        # Sort by weight and take top keywords
        weighted_keywords.sort(key=lambda x: x[1], reverse=True)
        top_keywords = [kw for kw, weight in weighted_keywords[:max_keywords]]
        
        result = ' '.join(top_keywords)
        logger.info(f"Extracted keywords: {result}")
        return result
    
    def _handle_compound_terms(self, keywords: List[str], doc) -> List[str]:
        """Identify and create compound terms from the original text"""
        text = doc.text.lower()
        
        # Comprehensive academic compound patterns - Mental Health & Psychiatry Focus
        compound_patterns = [
            # Self-diagnosis / Auto-diagnostic
            (r'self[\s-]?diagnos\w*', 'self-diagnosis'),
            (r'auto[\s-]?diagnos\w*', 'auto-diagnostic'),
            
            # Cognitive & Neurological Terms
            (r'cognitive[\s-]?trouble\w*', 'cognitive-troubles'),
            (r'trouble\w*[\s-]?cognitif\w*', 'troubles-cognitifs'),
            (r'cognitive[\s-]?disorder\w*', 'cognitive-disorders'),
            (r'cognitive[\s-]?dysfunction\w*', 'cognitive-dysfunction'),
            (r'cognitive[\s-]?impairment\w*', 'cognitive-impairment'),
            (r'cognitive[\s-]?decline\w*', 'cognitive-decline'),
            (r'cognitive[\s-]?assessment\w*', 'cognitive-assessment'),
            (r'cognitive[\s-]?rehabilitation\w*', 'cognitive-rehabilitation'),
            (r'neurocognitive[\s-]?disorder\w*', 'neurocognitive-disorders'),
            
            # Mental Health General
            (r'mental[\s-]?health', 'mental-health'),
            (r'santé[\s-]?mentale', 'santé-mentale'),
            (r'mental[\s-]?disorder\w*', 'mental-disorders'),
            (r'mental[\s-]?illness\w*', 'mental-illness'),
            (r'psychological[\s-]?disorder\w*', 'psychological-disorders'),
            (r'psychiatric[\s-]?disorder\w*', 'psychiatric-disorders'),
            (r'psychopatholog\w*', 'psychopathology'),
            
            # Mood Disorders
            (r'mood[\s-]?disorder\w*', 'mood-disorders'),
            (r'trouble\w*[\s-]?de[\s-]?l[\s-]?humeur', 'troubles-humeur'),
            (r'bipolar[\s-]?disorder\w*', 'bipolar-disorder'),
            (r'trouble[\s-]?bipolaire', 'trouble-bipolaire'),
            (r'major[\s-]?depression\w*', 'major-depression'),
            (r'depression[\s-]?majeure', 'dépression-majeure'),
            (r'seasonal[\s-]?affective[\s-]?disorder', 'seasonal-affective-disorder'),
            (r'dysthymi\w*', 'dysthymia'),
            
            # Anxiety Disorders
            (r'anxiety[\s-]?disorder\w*', 'anxiety-disorders'),
            (r'trouble\w*[\s-]?anxieux', 'troubles-anxieux'),
            (r'panic[\s-]?disorder\w*', 'panic-disorder'),
            (r'trouble[\s-]?panique', 'trouble-panique'),
            (r'social[\s-]?anxiety', 'social-anxiety'),
            (r'anxiété[\s-]?sociale', 'anxiété-sociale'),
            (r'generalized[\s-]?anxiety', 'generalized-anxiety'),
            (r'anxiété[\s-]?généralisée', 'anxiété-généralisée'),
            (r'agoraphob\w*', 'agoraphobia'),
            (r'claustrophob\w*', 'claustrophobia'),
            
            # Trauma & Stress
            (r'post[\s-]?traumatic[\s-]?stress', 'post-traumatic-stress'),
            (r'stress[\s-]?post[\s-]?traumatique', 'stress-post-traumatique'),
            (r'acute[\s-]?stress', 'acute-stress'),
            (r'stress[\s-]?aigu', 'stress-aigu'),
            (r'complex[\s-]?trauma', 'complex-trauma'),
            (r'trauma[\s-]?complexe', 'trauma-complexe'),
            
            # Personality Disorders
            (r'personality[\s-]?disorder\w*', 'personality-disorders'),
            (r'trouble\w*[\s-]?de[\s-]?personnalité', 'troubles-personnalité'),
            (r'borderline[\s-]?personality', 'borderline-personality'),
            (r'personnalité[\s-]?borderline', 'personnalité-borderline'),
            (r'antisocial[\s-]?personality', 'antisocial-personality'),
            (r'narcissistic[\s-]?personality', 'narcissistic-personality'),
            
            # Psychotic Disorders
            (r'psychotic[\s-]?disorder\w*', 'psychotic-disorders'),
            (r'trouble\w*[\s-]?psychotique\w*', 'troubles-psychotiques'),
            (r'schizophreni\w*', 'schizophrenia'),
            (r'schizophréni\w*', 'schizophrénie'),
            (r'delusional[\s-]?disorder\w*', 'delusional-disorder'),
            (r'trouble[\s-]?délirant', 'trouble-délirant'),
            (r'brief[\s-]?psychotic', 'brief-psychotic'),
            
            # Eating Disorders
            (r'eating[\s-]?disorder\w*', 'eating-disorders'),
            (r'trouble\w*[\s-]?alimentaire\w*', 'troubles-alimentaires'),
            (r'anorexia[\s-]?nervosa', 'anorexia-nervosa'),
            (r'anorexie[\s-]?mentale', 'anorexie-mentale'),
            (r'bulimia[\s-]?nervosa', 'bulimia-nervosa'),
            (r'boulimi\w*', 'boulimie'),
            (r'binge[\s-]?eating', 'binge-eating'),
            
            # Substance Use Disorders
            (r'substance[\s-]?use[\s-]?disorder\w*', 'substance-use-disorders'),
            (r'addiction[\s-]?disorder\w*', 'addiction-disorders'),
            (r'alcohol[\s-]?use[\s-]?disorder', 'alcohol-use-disorder'),
            (r'drug[\s-]?addiction', 'drug-addiction'),
            (r'toxicomani\w*', 'toxicomanie'),
            (r'alcoolism\w*', 'alcoholism'),
            (r'alcoolisme', 'alcoolisme'),
            
            # ADHD & Neurodevelopmental
            (r'attention[\s-]?deficit', 'attention-deficit'),
            (r'déficit[\s-]?attention', 'déficit-attention'),
            (r'hyperactivity[\s-]?disorder', 'hyperactivity-disorder'),
            (r'trouble[\s-]?hyperactivité', 'trouble-hyperactivité'),
            (r'autism[\s-]?spectrum', 'autism-spectrum'),
            (r'spectre[\s-]?autist\w*', 'spectre-autistique'),
            (r'asperger\w*', 'asperger'),
            
            # Sleep Disorders
            (r'sleep[\s-]?disorder\w*', 'sleep-disorders'),
            (r'trouble\w*[\s-]?du[\s-]?sommeil', 'troubles-sommeil'),
            (r'insomni\w*', 'insomnia'),
            (r'sleep[\s-]?apnea', 'sleep-apnea'),
            (r'apnée[\s-]?sommeil', 'apnée-sommeil'),
            (r'narcoleps\w*', 'narcolepsy'),
            
            # Therapeutic Approaches
            (r'cognitive[\s-]?behavioral[\s-]?therapy', 'cognitive-behavioral-therapy'),
            (r'thérapie[\s-]?cognitive[\s-]?comportementale', 'thérapie-cognitive-comportementale'),
            (r'psychodynamic[\s-]?therapy', 'psychodynamic-therapy'),
            (r'psychothérapie[\s-]?psychodynamique', 'psychothérapie-psychodynamique'),
            (r'group[\s-]?therapy', 'group-therapy'),
            (r'thérapie[\s-]?de[\s-]?groupe', 'thérapie-groupe'),
            (r'family[\s-]?therapy', 'family-therapy'),
            (r'thérapie[\s-]?familiale', 'thérapie-familiale'),
            (r'dialectical[\s-]?behavior[\s-]?therapy', 'dialectical-behavior-therapy'),
            (r'mindfulness[\s-]?based', 'mindfulness-based'),
            (r'pleine[\s-]?conscience', 'pleine-conscience'),
            
            # Assessment & Diagnosis
            (r'psychiatric[\s-]?assessment', 'psychiatric-assessment'),
            (r'évaluation[\s-]?psychiatrique', 'évaluation-psychiatrique'),
            (r'psychological[\s-]?evaluation', 'psychological-evaluation'),
            (r'clinical[\s-]?interview', 'clinical-interview'),
            (r'entretien[\s-]?clinique', 'entretien-clinique'),
            (r'diagnostic[\s-]?criteria', 'diagnostic-criteria'),
            (r'critères[\s-]?diagnostiques', 'critères-diagnostiques'),
            
            # Other Academic Fields (for versatility)
            (r'machine[\s-]?learning', 'machine-learning'),
            (r'artificial[\s-]?intelligence', 'artificial-intelligence'),
            (r'intelligence[\s-]?artificielle', 'intelligence-artificielle'),
            (r'deep[\s-]?learning', 'deep-learning'),
            (r'data[\s-]?science', 'data-science'),
            (r'climate[\s-]?change', 'climate-change'),
            (r'changement[\s-]?climatique', 'changement-climatique'),
        ]
        
        # Check for compound terms in original text
        found_compounds = []
        for pattern, replacement in compound_patterns:
            if re.search(pattern, text):
                found_compounds.append(replacement)
                # Remove individual components if compound is found
                keywords = [k for k in keywords if k not in replacement.split('-')]
        
        return found_compounds + keywords
    
    def _fallback_extraction(self, query: str) -> str:
        """Fallback method if spaCy is not available"""
        logger.warning("Using fallback keyword extraction")
        
        # Remove question words and common phrases
        stop_patterns = [
            r'\b(what|how|why|when|where|who|which|allows?|certain|persons?|people|some|many)\b',
            r'\b(que|qui|quoi|comment|pourquoi|quand|où|permet|permettent|certaines?|personnes?)\b',
            r'\b(is|are|was|were|can|could|should|would|may|might|will|shall|must)\b',
            r'\b(est|sont|était|étaient|peut|pourrait|devrait|voudrait|pourra|doit)\b'
        ]
        
        cleaned = query.lower()
        for pattern in stop_patterns:
            cleaned = re.sub(pattern, ' ', cleaned, flags=re.IGNORECASE)
        
        # Extract meaningful words (3+ characters)
        words = re.findall(r'\b[a-zA-ZÀ-ÿ]{3,}\b', cleaned)
        
        # Remove duplicates while preserving order
        unique_words = []
        seen = set()
        for word in words:
            if word not in seen:
                unique_words.append(word)
                seen.add(word)
        
        return ' '.join(unique_words[:6])

# Updated search function
async def search_pepite(self, query: str, max_results: int = 5) -> List[Dict]:
    """Search PEPITE (Université de Lille) repository using NLP-extracted keywords"""
    
    try:
        # Extract keywords using advanced NLP
        if not hasattr(self, 'keyword_extractor'):
            self.keyword_extractor = AdvancedKeywordExtractor()
        
        search_keywords = self.keyword_extractor.extract_keywords(query)
        
        logger.info(f"Original query: {query}")
        logger.info(f"NLP-extracted keywords: {search_keywords}")
        
        # If no keywords extracted, use fallback
        if not search_keywords.strip():
            search_keywords = query
            logger.warning("No keywords extracted, using original query")
        
        # Set strict timeout to prevent hanging
        timeout = aiohttp.ClientTimeout(total=20)
        
        # Use the actual Pepite search URL
        base_search_url = "https://pepite.univ-lille.fr/ori-oai-search/advanced-search.html"
        
        # Parameters for the search
        params = {
            "search": "true",
            "userChoices[simple_all].simpleValueRequestType": "default",
            "submenuKey": "advanced", 
            "menuKey": "all",
            "userChoices[simple_all].simpleValue": search_keywords,
            "resultsPerPage": str(max_results)
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0"
        }
        
        logger.info(f"Searching PEPITE with NLP keywords: {search_keywords}")
        
        connector = aiohttp.TCPConnector(force_close=True)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            try:
                async with session.get(base_search_url, params=params, headers=headers) as response:
                    if response.status == 200:
                        html_content = await response.text()
                        logger.info(f"PEPITE search successful, parsing results...")
                        
                        results = await self.parse_pepite_oai_results(html_content, query)
                        
                        if results:
                            logger.info(f"PEPITE search successful: {len(results)} results")
                            return results
                        else:
                            logger.info("PEPITE search returned no parseable results")
                            return []
                    else:
                        logger.warning(f"PEPITE search returned status {response.status}")
                        return []
                        
            except asyncio.TimeoutError:
                logger.warning("PEPITE search timed out")
                return []
            except Exception as e:
                logger.warning(f"PEPITE search request failed: {e}")
                return []
        
    except Exception as e:
        logger.error(f"PEPITE search completely failed: {e}")
        return []


def setup_logger():
    logger = logging.getLogger("academia")
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.set_name("academia")
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
    return logger

logger = setup_logger()

class AcademicAPIManager:
    """Manages API calls to academic databases"""
    
    def __init__(self, pipe_instance):
        self.pipe = pipe_instance
        self.api_cache = {}
        
    async def search_academic_databases(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search academic databases in priority order - FIXED VERSION"""
        return await self.search_academic_databases_with_priority(query, max_results)
    
    async def search_pubmed(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search PubMed using E-utilities API"""
        base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        
        # First, search for PMIDs
        search_url = f"{base_url}esearch.fcgi"
        search_params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json"
        }
        
        try:
            connector = aiohttp.TCPConnector(force_close=True)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(search_url, params=search_params, timeout=15) as response:
                    if response.status == 200:
                        search_data = await response.json()
                        pmids = search_data.get("esearchresult", {}).get("idlist", [])
                        
                        if not pmids:
                            return []
                        
                        # Get detailed information for each PMID
                        return await self.fetch_pubmed_details(pmids, session)
                    
        except Exception as e:
            logger.error(f"PubMed search error: {e}")
            return []
    
    async def fetch_pubmed_details(self, pmids: List[str], session) -> List[Dict]:
        """Fetch detailed information for PubMed articles"""
        if not pmids:
            return []
            
        base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        fetch_url = f"{base_url}efetch.fcgi"
        
        # Join PMIDs with commas
        pmid_string = ",".join(pmids)
        
        fetch_params = {
            "db": "pubmed",
            "id": pmid_string,
            "retmode": "xml"
        }
        
        try:
            async with session.get(fetch_url, params=fetch_params, timeout=20) as response:
                if response.status == 200:
                    xml_content = await response.text()
                    return self.parse_pubmed_xml(xml_content)
                    
        except Exception as e:
            logger.error(f"PubMed fetch error: {e}")
            return []
    
    def parse_pubmed_xml(self, xml_content: str) -> List[Dict]:
        """Parse PubMed XML response"""
        results = []
        
        try:
            root = ET.fromstring(xml_content)
            
            for article in root.findall(".//PubmedArticle"):
                try:
                    # Extract PMID
                    pmid_elem = article.find(".//PMID")
                    pmid = pmid_elem.text if pmid_elem is not None else ""
                    
                    # Extract title
                    title_elem = article.find(".//ArticleTitle")
                    title = title_elem.text if title_elem is not None else ""
                    
                    # Extract authors
                    authors = []
                    for author in article.findall(".//Author"):
                        lastname = author.find("LastName")
                        firstname = author.find("ForeName")
                        if lastname is not None and firstname is not None:
                            authors.append(f"{firstname.text} {lastname.text}")
                    
                    # Extract publication date
                    pub_date = ""
                    date_elem = article.find(".//PubDate")
                    if date_elem is not None:
                        year = date_elem.find("Year")
                        month = date_elem.find("Month")
                        if year is not None:
                            pub_date = year.text
                            if month is not None:
                                pub_date = f"{month.text} {pub_date}"
                    
                    # Extract abstract
                    abstract = ""
                    abstract_elem = article.find(".//AbstractText")
                    if abstract_elem is not None:
                        abstract = abstract_elem.text or ""
                    
                    # Extract journal
                    journal = ""
                    journal_elem = article.find(".//Title")
                    if journal_elem is not None:
                        journal = journal_elem.text or ""
                    
                    # Create URL
                    url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""
                    
                    # Create structured result
                    result = {
                        "title": title,
                        "authors": authors,
                        "publication_date": pub_date,
                        "journal": journal,
                        "abstract": abstract,
                        "url": url,
                        "pmid": pmid,
                        "source": "PubMed",
                        "content": f"Title: {title}\nAuthors: {'; '.join(authors)}\nJournal: {journal}\nDate: {pub_date}\nAbstract: {abstract}",
                        "query": "",  # Will be set by calling function
                        "valid": True,
                        "tokens": 0  # Will be calculated later
                    }
                    
                    results.append(result)
                    
                except Exception as e:
                    logger.error(f"Error parsing PubMed article: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error parsing PubMed XML: {e}")
            
        return results
    
    async def search_hal(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search HAL (French academic repository)"""
        base_url = "https://api.archives-ouvertes.fr/search/"
        
        params = {
            "q": query,
            "rows": max_results,
            "fl": "title_s,authFullName_s,producedDate_s,abstract_s,uri_s,journalTitle_s,docType_s",
            "wt": "json"
        }
        
        try:
            connector = aiohttp.TCPConnector(force_close=True)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(base_url, params=params, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self.parse_hal_response(data, query)
                        
        except Exception as e:
            logger.error(f"HAL search error: {e}")
            return []
    
    def parse_hal_response(self, data: Dict, query: str) -> List[Dict]:
        """Parse HAL API response"""
        results = []
        
        docs = data.get("response", {}).get("docs", [])
        
        for doc in docs:
            try:
                title = doc.get("title_s", [""])[0] if doc.get("title_s") else ""
                authors = doc.get("authFullName_s", [])
                date = doc.get("producedDate_s", [""])[0] if doc.get("producedDate_s") else ""
                abstract = doc.get("abstract_s", [""])[0] if doc.get("abstract_s") else ""
                url = doc.get("uri_s", [""])[0] if doc.get("uri_s") else ""
                journal = doc.get("journalTitle_s", [""])[0] if doc.get("journalTitle_s") else ""
                doc_type = doc.get("docType_s", [""])[0] if doc.get("docType_s") else ""
                
                result = {
                    "title": title,
                    "authors": authors,
                    "publication_date": date,
                    "journal": journal,
                    "abstract": abstract,
                    "url": url,
                    "document_type": doc_type,
                    "source": "HAL",
                    "content": f"Title: {title}\nAuthors: {'; '.join(authors)}\nJournal: {journal}\nDate: {date}\nAbstract: {abstract}",
                    "query": query,
                    "valid": True,
                    "tokens": 0
                }
                
                results.append(result)
                
            except Exception as e:
                logger.error(f"Error parsing HAL document: {e}")
                continue
                
        return results
    
    async def search_sudoc(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search SUDOC (French university catalog)"""
        # Note: SUDOC doesn't have a direct API, but we can use their SRU interface
        base_url = "https://www.sudoc.fr/services/sru/"
        
        params = {
            "operation": "searchRetrieve",
            "version": "1.2",
            "query": f'dc.title="{query}" or dc.subject="{query}"',
            "recordSchema": "marcxml",
            "maximumRecords": max_results
        }
        
        try:
            connector = aiohttp.TCPConnector(force_close=True)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(base_url, params=params, timeout=15) as response:
                    if response.status == 200:
                        xml_content = await response.text()
                        return self.parse_sudoc_xml(xml_content, query)
                        
        except Exception as e:
            logger.error(f"SUDOC search error: {e}")
            return []
    
    def parse_sudoc_xml(self, xml_content: str, query: str) -> List[Dict]:
        """Parse SUDOC XML response"""
        results = []
        
        try:
            root = ET.fromstring(xml_content)
            
            for record in root.findall(".//{http://www.loc.gov/MARC21/slim}record"):
                try:
                    title = ""
                    authors = []
                    date = ""
                    
                    # Extract title (field 245)
                    title_field = record.find(".//{http://www.loc.gov/MARC21/slim}datafield[@tag='245']")
                    if title_field is not None:
                        title_sub = title_field.find(".//{http://www.loc.gov/MARC21/slim}subfield[@code='a']")
                        if title_sub is not None:
                            title = title_sub.text or ""
                    
                    # Extract authors (field 700)
                    for author_field in record.findall(".//{http://www.loc.gov/MARC21/slim}datafield[@tag='700']"):
                        author_sub = author_field.find(".//{http://www.loc.gov/MARC21/slim}subfield[@code='a']")
                        if author_sub is not None:
                            authors.append(author_sub.text or "")
                    
                    # Extract publication date (field 008 or 260)
                    date_field = record.find(".//{http://www.loc.gov/MARC21/slim}datafield[@tag='260']")
                    if date_field is not None:
                        date_sub = date_field.find(".//{http://www.loc.gov/MARC21/slim}subfield[@code='c']")
                        if date_sub is not None:
                            date = date_sub.text or ""
                    
                    # Create URL (basic SUDOC URL)
                    url = f"https://www.sudoc.fr/cbs/xslt/DB=2.1//CMD?ACT=SRCHA&IKT=1016&SRT=RLV&TRM={urllib.parse.quote(query)}"
                    
                    result = {
                        "title": title,
                        "authors": authors,
                        "publication_date": date,
                        "journal": "",
                        "abstract": "",
                        "url": url,
                        "source": "SUDOC",
                        "content": f"Title: {title}\nAuthors: {'; '.join(authors)}\nDate: {date}",
                        "query": query,
                        "valid": True,
                        "tokens": 0
                    }
                    
                    results.append(result)
                    
                except Exception as e:
                    logger.error(f"Error parsing SUDOC record: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error parsing SUDOC XML: {e}")
            
        return results
    
    async def search_arxiv(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search arXiv"""
        base_url = "http://export.arxiv.org/api/query"
        
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": max_results
        }
        
        try:
            connector = aiohttp.TCPConnector(force_close=True)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(base_url, params=params, timeout=15) as response:
                    if response.status == 200:
                        xml_content = await response.text()
                        return self.parse_arxiv_xml(xml_content, query)
                        
        except Exception as e:
            logger.error(f"arXiv search error: {e}")
            return []
    
    def parse_arxiv_xml(self, xml_content: str, query: str) -> List[Dict]:
        """Parse arXiv XML response"""
        results = []
        
        try:
            root = ET.fromstring(xml_content)
            
            for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry"):
                try:
                    # Extract title
                    title_elem = entry.find(".//{http://www.w3.org/2005/Atom}title")
                    title = title_elem.text.strip() if title_elem is not None else ""
                    
                    # Extract authors
                    authors = []
                    for author in entry.findall(".//{http://www.w3.org/2005/Atom}author"):
                        name_elem = author.find(".//{http://www.w3.org/2005/Atom}name")
                        if name_elem is not None:
                            authors.append(name_elem.text)
                    
                    # Extract publication date
                    pub_date = ""
                    date_elem = entry.find(".//{http://www.w3.org/2005/Atom}published")
                    if date_elem is not None:
                        pub_date = date_elem.text[:10]  # Just the date part
                    
                    # Extract abstract
                    abstract = ""
                    abstract_elem = entry.find(".//{http://www.w3.org/2005/Atom}summary")
                    if abstract_elem is not None:
                        abstract = abstract_elem.text.strip()
                    
                    # Extract URL
                    url = ""
                    id_elem = entry.find(".//{http://www.w3.org/2005/Atom}id")
                    if id_elem is not None:
                        url = id_elem.text
                    
                    result = {
                        "title": title,
                        "authors": authors,
                        "publication_date": pub_date,
                        "journal": "arXiv",
                        "abstract": abstract,
                        "url": url,
                        "source": "arXiv",
                        "content": f"Title: {title}\nAuthors: {'; '.join(authors)}\nDate: {pub_date}\nAbstract: {abstract}",
                        "query": query,
                        "valid": True,
                        "tokens": 0
                    }
                    
                    results.append(result)
                    
                except Exception as e:
                    logger.error(f"Error parsing arXiv entry: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error parsing arXiv XML: {e}")
            
        return results
    
    async def search_crossref(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search CrossRef for academic papers"""
        base_url = "https://api.crossref.org/works"
        
        params = {
            "query": query,
            "rows": max_results,
            "select": "title,author,published-print,published-online,abstract,URL,container-title,DOI"
        }
        
        headers = {
            "User-Agent": "Deep Research Bot (mailto:research@example.com)"  # CrossRef requests a contact email
        }
        
        try:
            connector = aiohttp.TCPConnector(force_close=True)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(base_url, params=params, headers=headers, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self.parse_crossref_response(data, query)
                        
        except Exception as e:
            logger.error(f"CrossRef search error: {e}")
            return []
    
    def parse_crossref_response(self, data: Dict, query: str) -> List[Dict]:
        """Parse CrossRef API response"""
        results = []
        
        items = data.get("message", {}).get("items", [])
        
        for item in items:
            try:
                # Extract title
                title = ""
                if item.get("title"):
                    title = item["title"][0]
                
                # Extract authors
                authors = []
                if item.get("author"):
                    for author in item["author"]:
                        given = author.get("given", "")
                        family = author.get("family", "")
                        if given and family:
                            authors.append(f"{given} {family}")
                        elif family:
                            authors.append(family)
                
                # Extract publication date
                pub_date = ""
                if item.get("published-print"):
                    date_parts = item["published-print"].get("date-parts", [])
                    if date_parts and date_parts[0]:
                        pub_date = "-".join(str(part) for part in date_parts[0])
                elif item.get("published-online"):
                    date_parts = item["published-online"].get("date-parts", [])
                    if date_parts and date_parts[0]:
                        pub_date = "-".join(str(part) for part in date_parts[0])
                
                # Extract journal
                journal = ""
                if item.get("container-title"):
                    journal = item["container-title"][0]
                
                # Extract abstract (if available)
                abstract = item.get("abstract", "")
                
                # Extract URL
                url = item.get("URL", "")
                if not url and item.get("DOI"):
                    url = f"https://doi.org/{item['DOI']}"
                
                result = {
                    "title": title,
                    "authors": authors,
                    "publication_date": pub_date,
                    "journal": journal,
                    "abstract": abstract,
                    "url": url,
                    "doi": item.get("DOI", ""),
                    "source": "CrossRef",
                    "content": f"Title: {title}\nAuthors: {'; '.join(authors)}\nJournal: {journal}\nDate: {pub_date}\nAbstract: {abstract}",
                    "query": query,
                    "valid": True,
                    "tokens": 0
                }
                
                results.append(result)
                
            except Exception as e:
                logger.error(f"Error parsing CrossRef item: {e}")
                continue
                
        return results


    # Add these methods to your existing Pipe class:

    async def search_with_academic_priority(self, query: str, max_results: int = 10) -> List[Dict]:
        """Enhanced search that prioritizes academic databases"""
        
        # Initialize academic API manager if not exists
        if not hasattr(self, 'academic_api'):
            self.academic_api = AcademicAPIManager(self)
        
        all_results = []
        
        # Step 1: Search academic databases first
        academic_results = await self.academic_api.search_academic_databases(query, max_results // 2)
        
        # Process academic results
        for result in academic_results:
            # Calculate tokens
            content = result.get("content", "")
            result["tokens"] = await self.count_tokens(content)
            result["query"] = query
            
            # Add to results
            all_results.append(result)
        
        # Step 2: If we need more results, use regular web search
        remaining_needed = max_results - len(all_results)
        if remaining_needed > 0:
            await self.emit_message(f"*Supplementing with {remaining_needed} web search results...*\n")
            
            # Use existing web search method
            web_results = await self.search_web(query)
            
            # Process and add web results
            for result in web_results[:remaining_needed]:
                processed_result = await self.process_search_result(
                    result, query, 
                    await self.get_embedding(query),
                    await self.get_embedding(query)  # placeholder for outline_embedding
                )
                
                if processed_result.get("valid", False):
                    all_results.append(processed_result)
        
        return all_results

    # Modify your existing process_query method to use academic priority:

    async def process_query_with_academic_priority(
        self,
        query: str,
        query_embedding: List[float],
        outline_embedding: List[float],
        cycle_feedback: Optional[Dict] = None,
        summary_embedding: Optional[List[float]] = None,
    ) -> List[Dict]:
        """Modified process_query that prioritizes academic sources"""
        
        await self.emit_status("info", f"Searching academic databases for: {query}", False)
        
        # Use academic priority search
        search_results = await self.search_with_academic_priority(query, self.valves.SEARCH_RESULTS_PER_QUERY + 3)
        
        if not search_results:
            await self.emit_message(f"*No results found for query: {query}*\n\n")
            return []
        
        # Continue with existing logic for result processing
        search_results = await self.select_most_relevant_results(
            search_results, query, query_embedding, outline_embedding, summary_embedding
        )
        
        # Process results as before
        successful_results = []
        for result in search_results:
            if len(successful_results) >= self.valves.SUCCESSFUL_RESULTS_PER_QUERY:
                break
            
            # Check if this is already a processed academic result
            if result.get("source") in ["PubMed", "HAL", "SUDOC", "arXiv", "CrossRef"]:
                # Academic results are already processed
                successful_results.append(result)
                
                # Display academic result
                await self.display_academic_result(result)
            else:
                # Process web results as before
                processed_result = await self.process_search_result(
                    result, query, query_embedding, outline_embedding, summary_embedding
                )
                
                if processed_result.get("valid", False):
                    successful_results.append(processed_result)
                    # Display regular result (existing code)
        
        return successful_results

    async def display_academic_result(self, result: Dict):
        """Display academic result in a formatted way"""
        source = result.get("source", "Academic")
        title = result.get("title", "Untitled")
        authors = result.get("authors", [])
        journal = result.get("journal", "")
        date = result.get("publication_date", "")
        url = result.get("url", "")
        abstract = result.get("abstract", "")
        
        # Format authors
        authors_str = "; ".join(authors[:3])  # Show first 3 authors
        if len(authors) > 3:
            authors_str += " et al."
        
        # Create formatted display
        result_text = f"#### {source}: {title}\n"
        if authors_str:
            result_text += f"**Authors:** {authors_str}\n"
        if journal:
            result_text += f"**Journal:** {journal}\n"
        if date:
            result_text += f"**Date:** {date}\n"
        if url:
            result_text += f"**URL:** {url}\n"
        
        result_text += f"**Tokens:** {result.get('tokens', 0)}\n\n"
        
        if abstract:
            result_text += f"**Abstract:** {abstract[:500]}{'...' if len(abstract) > 500 else ''}\n\n"
        
        await self.emit_message(result_text)
    async def search_pepite(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search PEPITE (Université de Lille) repository using actual search URL"""
        
        try:
            # Set strict timeout to prevent hanging
            timeout = aiohttp.ClientTimeout(total=20)  # 20 second max for OAI search
            
            # Use the actual Pepite search URL you provided
            base_search_url = "https://pepite.univ-lille.fr/ori-oai-search/advanced-search.html"
            
            # Parameters based on the URL structure you found
            params = {
                "search": "true",
                "userChoices[simple_all].simpleValueRequestType": "default",
                "submenuKey": "advanced", 
                "menuKey": "all",
                "userChoices[simple_all].simpleValue": query,
                # Add results limit if the interface supports it
                "resultsPerPage": str(max_results)
            }
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Cache-Control": "max-age=0"
            }
            
            logger.info(f"Searching PEPITE with actual search URL for: {query}")
            
            connector = aiohttp.TCPConnector(force_close=True)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                try:
                    async with session.get(base_search_url, params=params, headers=headers) as response:

                        if response.status == 200:
                            html_content = await response.text()
                            logger.info(f"PEPITE search successful, parsing results...")
                            
                            results = await self.parse_pepite_oai_results(html_content, query)
                            
                            if results:
                                logger.info(f"PEPITE search successful: {len(results)} results")
                                return results
                            else:
                                logger.info("PEPITE search returned no parseable results")
                                return []
                        else:
                            logger.warning(f"PEPITE search returned status {response.status}")
                            return []
                            
                except asyncio.TimeoutError:
                    logger.warning("PEPITE search timed out")
                    return []
                except Exception as e:
                    logger.warning(f"PEPITE search request failed: {e}")
                    return []
            
        except Exception as e:
            logger.error(f"PEPITE search completely failed: {e}")
            return []

    async def parse_pepite_oai_results(self, html_content: str, query: str) -> List[Dict]:
        """Parse PEPITE OAI search results - improved for actual search interface"""
        
        results = []
        
        try:
            # Check if BeautifulSoup is available
            try:
                from bs4 import BeautifulSoup
            except ImportError:
                logger.error("BeautifulSoup not available for PEPITE parsing")
                return []
            
            # Limit content size to prevent memory issues
            if len(html_content) > 200000:  # 200KB limit
                html_content = html_content[:200000]
                logger.warning("PEPITE HTML content truncated due to size")
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # OAI search interfaces typically use specific patterns
            # Look for common OAI result patterns
            result_selectors = [
                # OAI-PMH common patterns
                'div.result-item',
                'div.search-result', 
                'div.record',
                'div.oai-record',
                'tr.result-row',
                'div.document-result',
                # Generic patterns
                'div.item',
                'article.result',
                '.result-container .result',
                # Table-based results
                'table.results tr',
                'tbody tr'
            ]
            
            found_results = []
            for selector in result_selectors:
                try:
                    found_results = soup.select(selector)
                    if found_results and len(found_results) > 1:  # Need more than just header
                        logger.info(f"PEPITE: Found {len(found_results)} results with selector: {selector}")
                        break
                except Exception as e:
                    logger.warning(f"PEPITE selector {selector} failed: {e}")
                    continue
            
            # If no structured results, try to find any links that look like documents
            if not found_results:
                logger.info("PEPITE: No structured results found, looking for document links")
                # Look for links that might be documents
                doc_links = soup.find_all('a', href=True)
                potential_results = []
                
                for link in doc_links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    # Look for links that seem like documents
                    if (href and text and len(text) > 10 and 
                        ('handle' in href or 'document' in href or 'record' in href or 
                         href.startswith('/') or 'pepite' in href)):
                        potential_results.append(link.parent or link)
                
                if potential_results:
                    found_results = potential_results[:max_results * 2]
                    logger.info(f"PEPITE: Found {len(found_results)} potential document links")
            
            if not found_results:
                logger.warning("PEPITE: No results found with any method")
                return []
            
            # Process found results
            processed_count = 0
            for i, result_element in enumerate(found_results):
                if processed_count >= max_results:
                    break
                    
                try:
                    # Extract title - try multiple approaches
                    title = ""
                    title_selectors = [
                        'h3 a', 'h4 a', 'h2 a', 'h1 a',
                        '.title a', '.document-title a', '.record-title a',
                        'a[href*="handle"]', 'a[href*="document"]', 'a[href*="record"]',
                        '.result-title', '.title', 'h3', 'h4', 'h2'
                    ]
                    
                    for title_sel in title_selectors:
                        title_elem = result_element.select_one(title_sel)
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            if len(title) > 5:  # Must be substantial
                                break
                    
                    # If still no title, try getting any prominent text
                    if not title or len(title) < 5:
                        title_elem = result_element.find('a')
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                    
                    # Extract URL
                    url = ""
                    url_selectors = [
                        'a[href*="handle"]', 'a[href*="document"]', 'a[href*="record"]',
                        'h3 a', 'h4 a', 'h2 a', '.title a', '.document-title a'
                    ]
                    
                    for url_sel in url_selectors:
                        url_elem = result_element.select_one(url_sel)
                        if url_elem and url_elem.get('href'):
                            url = url_elem.get('href')
                            # Make absolute URL if needed
                            if url.startswith('/'):
                                url = f"https://pepite.univ-lille.fr{url}"
                            elif not url.startswith('http'):
                                url = f"https://pepite.univ-lille.fr/{url}"
                            break
                    
                    # Extract metadata (authors, date, etc.)
                    authors = []
                    date = ""
                    abstract = ""
                    
                    # Look for author information
                    author_selectors = [
                        '.author', '.creator', '.dc-creator', 
                        '[class*="author"]', '[class*="creator"]'
                    ]
                    for auth_sel in author_selectors:
                        author_elems = result_element.select(auth_sel)
                        for auth_elem in author_elems[:3]:  # Max 3 authors
                            author_text = auth_elem.get_text(strip=True)
                            if author_text and len(author_text) > 2:
                                authors.append(author_text)
                    
                    # Look for date
                    date_selectors = [
                        '.date', '.publication-date', '.dc-date',
                        '[class*="date"]'
                    ]
                    for date_sel in date_selectors:
                        date_elem = result_element.select_one(date_sel)
                        if date_elem:
                            date_text = date_elem.get_text(strip=True)
                            # Look for year pattern
                            import re
                            year_match = re.search(r'\b(19|20)\d{2}\b', date_text)
                            if year_match:
                                date = year_match.group(0)
                                break
                    
                    # Look for abstract/description
                    desc_selectors = [
                        '.abstract', '.description', '.summary', 
                        '.dc-description', '[class*="abstract"]'
                    ]
                    for desc_sel in desc_selectors:
                        desc_elem = result_element.select_one(desc_sel)
                        if desc_elem:
                            desc_text = desc_elem.get_text(strip=True)
                            if len(desc_text) > 20:  # Substantial description
                                abstract = desc_text[:500]  # Limit length
                                break
                    
                    # Only add if we have at least a title
                    if title and len(title) > 5:
                        result = {
                            "title": title,
                            "authors": authors,
                            "publication_date": date,
                            "journal": "PEPITE - Université de Lille",
                            "abstract": abstract,
                            "url": url or f"https://pepite.univ-lille.fr/ori-oai-search/advanced-search.html?search=true&userChoices%5Bsimple_all%5D.simpleValue={query}",
                            "source": "PEPITE", 
                            "content": f"Title: {title}\nAuthors: {'; '.join(authors)}\nDate: {date}\nAbstract: {abstract}",
                            "query": query,
                            "valid": True,
                            "tokens": 0,
                            "repository": "Université de Lille"
                        }
                        
                        results.append(result)
                        processed_count += 1
                        
                except Exception as e:
                    logger.warning(f"PEPITE: Error parsing result {i}: {e}")
                    continue
            
            logger.info(f"PEPITE: Successfully parsed {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"PEPITE: Error parsing OAI results: {e}")
            return []

    # ALTERNATIVE: If the above doesn't work, try the API approach
    
    
    async def search_pepite_with_detailed_logging(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search PEPITE with detailed logging for debugging"""
        
        logger.info(f"=== PEPITE SEARCH DEBUG START for query: '{query}' ===")
        
        try:
            timeout = aiohttp.ClientTimeout(total=20)
            base_search_url = "https://pepite.univ-lille.fr/ori-oai-search/advanced-search.html"
            
            params = {
                "search": "true",
                "userChoices[simple_all].simpleValueRequestType": "default",
                "submenuKey": "advanced", 
                "menuKey": "all",
                "userChoices[simple_all].simpleValue": query,
                "resultsPerPage": str(max_results)
            }
            
            # Log the full URL being requested
            from urllib.parse import urlencode
            full_url = f"{base_search_url}?{urlencode(params)}"
            logger.info(f"PEPITE: Requesting URL: {full_url}")
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
            }
            
            connector = aiohttp.TCPConnector(force_close=True)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                start_time = time.time()
                
                try:
                    async with session.get(base_search_url, params=params, headers=headers) as response:
                        request_time = time.time() - start_time
                        logger.info(f"PEPITE: Response received in {request_time:.2f}s, status: {response.status}")
                        
                        if response.status == 200:
                            html_content = await response.text()
                            content_length = len(html_content)
                            logger.info(f"PEPITE: Received {content_length} characters of HTML")
                            
                            # Log a snippet of the content for debugging
                            snippet = html_content[:500].replace('\n', ' ').replace('\r', ' ')
                            logger.debug(f"PEPITE: HTML snippet: {snippet}...")
                            
                            # Check for obvious signs of success/failure
                            if "no results" in html_content.lower() or "aucun résultat" in html_content.lower():
                                logger.info("PEPITE: HTML indicates no results found")
                                return []
                            elif "error" in html_content.lower() or "erreur" in html_content.lower():
                                logger.warning("PEPITE: HTML indicates an error occurred")
                                return []
                            
                            results = await self.parse_pepite_oai_results(html_content, query)
                            
                            if results:
                                logger.info(f"PEPITE: SUCCESS - Parsed {len(results)} results")
                                for i, result in enumerate(results):
                                    logger.info(f"PEPITE Result {i+1}: {result.get('title', 'No title')[:50]}...")
                            else:
                                logger.warning("PEPITE: FAILED - No results could be parsed from HTML")
                                
                                # Save HTML for debugging if needed
                                if content_length > 1000:  # Only if we got substantial content
                                    debug_file = f"pepite_debug_{int(time.time())}.html"
                                    try:
                                        with open(debug_file, 'w', encoding='utf-8') as f:
                                            f.write(html_content)
                                        logger.info(f"PEPITE: Saved debug HTML to {debug_file}")
                                    except Exception as e:
                                        logger.warning(f"PEPITE: Could not save debug file: {e}")
                            
                            return results
                        else:
                            logger.error(f"PEPITE: HTTP error {response.status}")
                            return []
                            
                except asyncio.TimeoutError:
                    logger.error("PEPITE: Request timed out")
                    return []
                except Exception as e:
                    logger.error(f"PEPITE: Request failed: {e}")
                    return []
            
        except Exception as e:
            logger.error(f"PEPITE: Complete failure: {e}")
            return []
        finally:
            logger.info("=== PEPITE SEARCH DEBUG END ===")
        
        
    async def search_academic_databases_with_priority(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search academic databases with ArXiv as fallback only"""
        
        all_results = []
        
        primary_sources = [
            ("pubmed", self.search_pubmed),
            ("hal", self.search_hal),
            ("openedition", self.search_openedition),    # NEW: OpenEdition for humanities/social sciences
            ("pepite", self.search_pepite_with_detailed_logging),
            ("crossref", self.search_crossref),
        ]
        
        # SECONDARY SOURCES (theses, preprints, institutional)
        secondary_sources = [
            ("theses", self.search_theses_fr),
            ("cairn", self.search_cairn),
            ("sudoc", self.search_sudoc),
            ("arxiv", self.search_arxiv),
        ]
        
        # Filter based on enabled databases
        enabled_databases = getattr(self.pipe.valves, 'ACADEMIC_DATABASES', 'pubmed,hal,openedition,pepite,theses,cairn,arxiv,crossref').split(',')
        enabled_databases = [db.strip().lower() for db in enabled_databases]
            
        # Filter sources
        enabled_primary = [(name, func) for name, func in primary_sources if name in enabled_databases]
        enabled_secondary = [(name, func) for name, func in secondary_sources if name in enabled_databases]
        
        logger.info(f"Academic search strategy: {len(enabled_primary)} primary + {len(enabled_secondary)} secondary sources")
        
        # PHASE 1: Search primary sources first
        target_per_primary = max(2, max_results // len(enabled_primary)) if enabled_primary else 0
        
        for source_name, search_func in enabled_primary:
            if len(all_results) >= max_results:
                break
                
            try:
                await self.pipe.emit_status("info", f"Searching {source_name.upper()} (primary)...", False)
                logger.info(f"PRIMARY: Starting search in {source_name}")
                
                search_task = asyncio.create_task(search_func(query, target_per_primary))
                
                try:
                    results = await asyncio.wait_for(search_task, timeout=30)
                    
                    if results:
                        logger.info(f"PRIMARY: {source_name.upper()} returned {len(results)} results")
                        await self.pipe.emit_message(f"*Found {len(results)} results from {source_name.upper()}*\n")
                        all_results.extend(results)
                        
                        # Special logging for Pepite to track success/failure
                        if source_name == "pepite":
                            if results:
                                logger.info("✅ PEPITE: Working correctly!")
                            else:
                                logger.warning("❌ PEPITE: No results returned")
                    else:
                        logger.info(f"PRIMARY: {source_name.upper()} returned no results")
                        
                except asyncio.TimeoutError:
                    logger.warning(f"PRIMARY: {source_name} timed out")
                    await self.pipe.emit_message(f"*{source_name.upper()} search timed out*\n")
                    
            except Exception as e:
                logger.error(f"PRIMARY: Error searching {source_name}: {e}")
                await self.pipe.emit_message(f"*Error searching {source_name.upper()}*\n")
        
        # PHASE 2: Only search secondary sources if we don't have enough results
        current_count = len(all_results)
        needed = max_results - current_count
        
        if needed > 0 and enabled_secondary:
            logger.info(f"SECONDARY: Need {needed} more results, searching secondary sources...")
            await self.pipe.emit_message(f"*Searching additional sources for {needed} more results...*\n")
            
            target_per_secondary = max(2, needed // len(enabled_secondary))
            
            for source_name, search_func in enabled_secondary:
                if len(all_results) >= max_results:
                    break
                    
                try:
                    await self.pipe.emit_status("info", f"Searching {source_name.upper()} (secondary)...", False)
                    logger.info(f"SECONDARY: Starting search in {source_name}")
                    
                    search_task = asyncio.create_task(search_func(query, target_per_secondary))
                    
                    try:
                        results = await asyncio.wait_for(search_task, timeout=30)
                        
                        if results:
                            logger.info(f"SECONDARY: {source_name.upper()} returned {len(results)} results")
                            await self.pipe.emit_message(f"*Found {len(results)} additional results from {source_name.upper()}*\n")
                            all_results.extend(results)
                        else:
                            logger.info(f"SECONDARY: {source_name.upper()} returned no results")
                            
                    except asyncio.TimeoutError:
                        logger.warning(f"SECONDARY: {source_name} timed out")
                        
                except Exception as e:
                    logger.error(f"SECONDARY: Error searching {source_name}: {e}")
        else:
            logger.info(f"SECONDARY: Have {current_count} results, skipping secondary sources")
        
        logger.info(f"Academic search completed: {len(all_results)} total results")
        return all_results[:max_results]
        
    async def test_pepite_search(self, test_query: str = "machine learning"):
        """Simple test function to check if Pepite is working"""
        
        logger.info(f"🧪 TESTING PEPITE with query: '{test_query}'")
        
        try:
            results = await self.search_pepite_with_detailed_logging(test_query, 3)
            
            if results:
                logger.info(f"✅ PEPITE TEST PASSED: Got {len(results)} results")
                for i, result in enumerate(results):
                    logger.info(f"   Result {i+1}: {result.get('title', 'No title')}")
                return True
            else:
                logger.warning("❌ PEPITE TEST FAILED: No results returned")
                return False
                
        except Exception as e:
            logger.error(f"❌ PEPITE TEST ERROR: {e}")
            return False    
        
        
    async def search_pepite_api_fallback(self, query: str, max_results: int = 5) -> List[Dict]:
        """Fallback: Try to find PEPITE OAI-PMH API endpoint"""
        
        try:
            # Many OAI repositories have an API endpoint
            api_endpoints = [
                "https://pepite.univ-lille.fr/oai/request",  # Common OAI-PMH endpoint
                "https://pepite.univ-lille.fr/oai",
                "https://pepite.univ-lille.fr/ori-oai-search/oai",
            ]
            
            for api_url in api_endpoints:
                try:
                    params = {
                        "verb": "ListRecords",
                        "metadataPrefix": "oai_dc",
                        "set": query  # This might work for some repositories
                    }
                    
                    timeout = aiohttp.ClientTimeout(total=15)
                    connector = aiohttp.TCPConnector(force_close=True)
                    
                    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                        async with session.get(api_url, params=params) as response:
                            if response.status == 200:
                                xml_content = await response.text()
                                # Parse OAI-PMH XML response
                                results = await self.parse_oai_xml(xml_content, query)
                                if results:
                                    logger.info(f"PEPITE API successful: {len(results)} results")
                                    return results
                            
                except Exception as e:
                    logger.debug(f"PEPITE API endpoint {api_url} failed: {e}")
                    continue
            
            return []
            
        except Exception as e:
            logger.error(f"PEPITE API fallback failed: {e}")
            return []


    async def search_pepite_main_form(self, query: str, max_results: int, base_url: str) -> List[Dict]:
        """Search PEPITE using main search form"""
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": base_url,
                "Referer": base_url
            }
            
            # Form data for search
            form_data = {
                "query": query,
                "q": query,
                "search": "Rechercher",
                "scope": "",
                "rpp": str(max_results)
            }
            
            connector = aiohttp.TCPConnector(force_close=True)
            async with aiohttp.ClientSession(connector=connector) as session:
                # First get the main page to check for CSRF tokens or form structure
                async with session.get(base_url, headers=headers, timeout=15) as response:
                    if response.status == 200:
                        main_page = await response.text()
                        
                        # Look for search form action and any hidden fields
                        import re
                        
                        # Try to find the search form action
                        form_action_match = re.search(r'<form[^>]*action=["\']([^"\']*search[^"\']*)["\']', main_page, re.IGNORECASE)
                        if form_action_match:
                            search_action = form_action_match.group(1)
                            if not search_action.startswith('http'):
                                search_action = f"{base_url.rstrip('/')}/{search_action.lstrip('/')}"
                        else:
                            search_action = f"{base_url}/simple-search"
                        
                        # Look for hidden form fields (CSRF tokens, etc.)
                        hidden_fields = re.findall(r'<input[^>]*type=["\']hidden["\'][^>]*name=["\']([^"\']*)["\'][^>]*value=["\']([^"\']*)["\']', main_page, re.IGNORECASE)
                        for field_name, field_value in hidden_fields:
                            form_data[field_name] = field_value
                        
                        # Submit the search form
                        async with session.post(search_action, data=form_data, headers=headers, timeout=20) as search_response:
                            if search_response.status == 200:
                                search_html = await search_response.text()
                                return await self.parse_pepite_html(search_html, query, base_url)
                            
        except Exception as e:
            logger.error(f"PEPITE form search failed: {e}")
            return []

    async def parse_pepite_html(self, html_content: str, query: str, base_url: str) -> List[Dict]:
        """Parse PEPITE search results from HTML - FIXED VERSION"""
        
        results = []
        
        try:
            # Check if BeautifulSoup is available
            try:
                from bs4 import BeautifulSoup
            except ImportError:
                logger.error("BeautifulSoup not available for PEPITE parsing")
                return []
            
            # Limit content size to prevent memory issues
            if len(html_content) > 100000:  # 100KB limit
                html_content = html_content[:100000]
                logger.warning("PEPITE HTML content truncated due to size")
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Common patterns for DSpace and similar repository systems
            result_selectors = [
                'div.artifact-description',
                'div.discovery-result', 
                'div.ds-artifact-item',
                'tr.ds-table-row',
                'tr.odd, tr.even',
                'div.browse-item'
            ]
            
            found_results = []
            for selector in result_selectors:
                try:
                    found_results = soup.select(selector)
                    if found_results:
                        logger.info(f"PEPITE: Found {len(found_results)} results with selector: {selector}")
                        break
                except Exception as e:
                    logger.warning(f"PEPITE selector {selector} failed: {e}")
                    continue
            
            if not found_results:
                logger.warning("PEPITE: No results found with any selector")
                return []
            
            # Limit results to prevent processing too many
            found_results = found_results[:max_results * 2]  # Process at most double the requested amount
            
            for i, result_element in enumerate(found_results[:max_results]):
                try:
                    # Extract title
                    title = ""
                    title_selectors = [
                        'h3 a', 'h4 a', 'h2 a', 'a.artifact-title', 
                        '.artifact-title a', 'span.artifact-title',
                        '.item-title a', '.title a'
                    ]
                    
                    for title_sel in title_selectors:
                        title_elem = result_element.select_one(title_sel)
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            break
                    
                    # Extract URL
                    url = ""
                    for url_sel in title_selectors:
                        url_elem = result_element.select_one(url_sel)
                        if url_elem and url_elem.get('href'):
                            url = url_elem.get('href')
                            if not url.startswith('http'):
                                url = f"{base_url.rstrip('/')}/{url.lstrip('/')}"
                            break
                    
                    # Extract basic metadata
                    authors = []
                    date = ""
                    abstract = ""
                    
                    # Only add if we have at least a title
                    if title and len(title) > 5:
                        result = {
                            "title": title,
                            "authors": authors,
                            "publication_date": date,
                            "journal": "PEPITE - Université de Lille",
                            "abstract": abstract,
                            "url": url,
                            "source": "PEPITE",
                            "content": f"Title: {title}\nAuthors: {'; '.join(authors)}\nDate: {date}\nAbstract: {abstract}",
                            "query": query,
                            "valid": True,
                            "tokens": 0,
                            "repository": "Université de Lille"
                        }
                        
                        results.append(result)
                        
                except Exception as e:
                    logger.warning(f"PEPITE: Error parsing result {i}: {e}")
                    continue
            
            logger.info(f"PEPITE: Successfully parsed {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"PEPITE: Error parsing HTML: {e}")
            return []

# 3. Fixed search_with_academic_priority method
    async def search_with_academic_priority(self, query: str, max_results: int = 10) -> List[Dict]:
        """Enhanced search that prioritizes academic databases - FIXED VERSION"""
        
        # Initialize academic API manager if not exists
        if not hasattr(self, 'academic_api') or self.academic_api is None:
            try:
                self.academic_api = AcademicAPIManager(self)
                logger.info("Academic API manager initialized")
            except Exception as e:
                logger.error(f"Failed to initialize academic API manager: {e}")
                # Fall back to web search only
                return await self.search_web(query)
        
        all_results = []
        
        try:
            # Step 1: Search academic databases first with timeout
            logger.info(f"Starting academic search for: {query}")
            
            # Set a reasonable timeout for academic searches
            academic_task = asyncio.create_task(
                self.academic_api.search_academic_databases(query, max_results // 2)
            )
            
            try:
                academic_results = await asyncio.wait_for(academic_task, timeout=60)  # 60 second timeout
                logger.info(f"Academic search completed: {len(academic_results)} results")
            except asyncio.TimeoutError:
                logger.warning("Academic search timed out, continuing with web search")
                academic_results = []
            except Exception as e:
                logger.error(f"Academic search failed: {e}")
                academic_results = []
            
            # Process academic results
            for result in academic_results:
                try:
                    # Calculate tokens
                    content = result.get("content", "")
                    if content:
                        result["tokens"] = await self.count_tokens(content)
                    else:
                        result["tokens"] = 0
                    result["query"] = query
                    
                    # Ensure result is marked as valid
                    result["valid"] = True
                    
                    # Add to results
                    all_results.append(result)
                except Exception as e:
                    logger.error(f"Error processing academic result: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error in academic search: {e}")
            # Continue with web search even if academic search fails
        
        # Step 2: If we need more results, use regular web search
        remaining_needed = max_results - len(all_results)
        if remaining_needed > 0:
            logger.info(f"Supplementing with {remaining_needed} web search results")
            
            try:
                # Use existing web search method
                web_results = await self.search_web(query)
                
                # Add web results (they'll be processed later in the pipeline)
                for result in web_results[:remaining_needed]:
                    all_results.append(result)
                    
            except Exception as e:
                logger.error(f"Error in web search: {e}")
        
        logger.info(f"Academic priority search completed: {len(all_results)} total results")
        return all_results
    async def search_theses_fr(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search theses.fr for French academic theses"""
        results = []
        try:
            connector = aiohttp.TCPConnector(force_close=True)
            async with aiohttp.ClientSession(connector=connector) as session:
                # theses.fr search URL (they don't have a public API, so we scrape)
                search_url = f"https://theses.fr/fr/?q={urllib.parse.quote(query)}"
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
                }
                
                async with session.get(search_url, headers=headers, timeout=30) as response:
                    if response.status == 200:
                        html_content = await response.text()
                        
                        try:
                            from bs4 import BeautifulSoup
                            soup = BeautifulSoup(html_content, 'html.parser')
                            
                            # Parse theses.fr results
                            thesis_items = soup.select('div.item-result, div.notice')
                            
                            for i, item in enumerate(thesis_items[:max_results]):
                                try:
                                    # Extract title
                                    title_elem = item.select_one('h3 a, .title a, a.title')
                                    title = title_elem.get_text(strip=True) if title_elem else "Untitled Thesis"
                                    
                                    # Extract URL
                                    url = ""
                                    if title_elem and title_elem.get('href'):
                                        url = title_elem.get('href')
                                        if not url.startswith('http'):
                                            url = f"https://theses.fr{url}"
                                    
                                    # Extract author
                                    author_elem = item.select_one('.author, .auteur')
                                    author = author_elem.get_text(strip=True) if author_elem else "Unknown Author"
                                    
                                    # Extract date
                                    date_elem = item.select_one('.date, .annee')
                                    date = date_elem.get_text(strip=True) if date_elem else ""
                                    
                                    # Extract university
                                    univ_elem = item.select_one('.university, .etablissement')
                                    university = univ_elem.get_text(strip=True) if univ_elem else ""
                                    
                                    # Extract discipline
                                    disc_elem = item.select_one('.discipline')
                                    discipline = disc_elem.get_text(strip=True) if disc_elem else ""
                                    
                                    result = {
                                        'title': title,
                                        'authors': [author] if author != "Unknown Author" else [],
                                        'abstract': f"Thèse de doctorat - {discipline}" if discipline else "Thèse de doctorat",
                                        'url': url or search_url,
                                        'publication_date': date,
                                        'source': 'Theses.fr',
                                        'content': f"Title: {title}\nAuthor: {author}\nUniversity: {university}\nDate: {date}\nDiscipline: {discipline}",
                                        'tokens': 0,
                                        'university': university,
                                        'discipline': discipline,
                                        'query': query,
                                        'valid': True
                                    }
                                    results.append(result)
                                    
                                except Exception as e:
                                    logger.warning(f"Error parsing theses.fr result {i}: {e}")
                                    continue
                                    
                        except ImportError:
                            logger.error("BeautifulSoup not available for theses.fr parsing")
                            
        except Exception as e:
            logger.error(f"Error searching theses.fr: {e}")
            
        return results
    async def search_cairn(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search Cairn.info for social sciences publications"""
        results = []
        try:
            connector = aiohttp.TCPConnector(force_close=True)
            async with aiohttp.ClientSession(connector=connector) as session:
                # Cairn search URL
                search_url = f"https://www.cairn.info/resultats_recherche.php"
                
                params = {
                    'searchTerm': query,
                    'searchField': 'all',
                    'searchType': 'basic'
                }
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
                }
                
                async with session.get(search_url, params=params, headers=headers, timeout=30) as response:
                    if response.status == 200:
                        html_content = await response.text()
                        
                        try:
                            from bs4 import BeautifulSoup
                            soup = BeautifulSoup(html_content, 'html.parser')
                            
                            # Parse Cairn results
                            article_items = soup.select('div.result-item, article.result')
                            
                            for i, item in enumerate(article_items[:max_results]):
                                try:
                                    # Extract title
                                    title_elem = item.select_one('h3 a, .title a, h2 a')
                                    title = title_elem.get_text(strip=True) if title_elem else "Untitled Article"
                                    
                                    # Extract URL
                                    url = ""
                                    if title_elem and title_elem.get('href'):
                                        url = title_elem.get('href')
                                        if not url.startswith('http'):
                                            url = f"https://www.cairn.info{url}"
                                    
                                    # Extract authors
                                    author_elems = item.select('.author, .auteur')
                                    authors = [elem.get_text(strip=True) for elem in author_elems]
                                    
                                    # Extract journal
                                    journal_elem = item.select_one('.journal, .revue')
                                    journal = journal_elem.get_text(strip=True) if journal_elem else "Cairn.info"
                                    
                                    # Extract date
                                    date_elem = item.select_one('.date, .annee')
                                    date = date_elem.get_text(strip=True) if date_elem else ""
                                    
                                    # Extract abstract
                                    abstract_elem = item.select_one('.abstract, .resume')
                                    abstract = abstract_elem.get_text(strip=True)[:500] if abstract_elem else ""
                                    
                                    result = {
                                        'title': title,
                                        'authors': authors,
                                        'abstract': abstract,
                                        'url': url or f"https://www.cairn.info/resultats_recherche.php?searchTerm={query}",
                                        'publication_date': date,
                                        'journal': journal,
                                        'source': 'Cairn',
                                        'content': f"Title: {title}\nAuthors: {'; '.join(authors)}\nJournal: {journal}\nDate: {date}\nAbstract: {abstract}",
                                        'tokens': 0,
                                        'query': query,
                                        'valid': True
                                    }
                                    results.append(result)
                                    
                                except Exception as e:
                                    logger.warning(f"Error parsing Cairn result {i}: {e}")
                                    continue
                                    
                        except ImportError:
                            logger.error("BeautifulSoup not available for Cairn parsing")
                            
        except Exception as e:
            logger.error(f"Error searching Cairn: {e}")
            
        return results
    async def search_openedition(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search OpenEdition for humanities and social sciences articles and books"""
        results = []
        
        try:
            # OpenEdition search URL with proper encoding
            search_url = f"https://search.openedition.org/results"
            
            params = {
                'searchdomain': 'openedition',
                'q': query,
                's': '',
                'a': 'info%3Aeu-repo%2Fsemantics%2FopenAccess'
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0'
            }
            
            logger.info(f"Searching OpenEdition for: {query}")
            
            timeout = aiohttp.ClientTimeout(total=30)
            connector = aiohttp.TCPConnector(force_close=True)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                try:
                    async with session.get(search_url, params=params, headers=headers) as response:
                        if response.status == 200:
                            html_content = await response.text()
                            logger.info(f"OpenEdition: Received {len(html_content)} characters of HTML")
                            
                            results = await self.parse_openedition_results(html_content, query)
                            
                            if results:
                                logger.info(f"OpenEdition: Successfully parsed {len(results)} results")
                            else:
                                logger.info("OpenEdition: No results could be parsed from HTML")
                            
                            return results
                        else:
                            logger.warning(f"OpenEdition search returned status {response.status}")
                            return []
                            
                except asyncio.TimeoutError:
                    logger.warning("OpenEdition search timed out")
                    return []
                except Exception as e:
                    logger.warning(f"OpenEdition search request failed: {e}")
                    return []
            
        except Exception as e:
            logger.error(f"OpenEdition search completely failed: {e}")
            return []

    async def parse_openedition_results(self, html_content: str, query: str) -> List[Dict]:
        """Parse OpenEdition search results from HTML"""
        
        results = []
        
        try:
            # Check if BeautifulSoup is available
            try:
                from bs4 import BeautifulSoup
            except ImportError:
                logger.error("BeautifulSoup not available for OpenEdition parsing")
                return []
            
            # Limit content size to prevent memory issues
            if len(html_content) > 300000:  # 300KB limit
                html_content = html_content[:300000]
                logger.warning("OpenEdition HTML content truncated due to size")
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # OpenEdition search results typically use these patterns
            result_selectors = [
                # Primary selectors for OpenEdition search results
                'div.result-item',
                'div.search-result',
                'article.result',
                'div.item-result',
                'li.result',
                'div.publication',
                # Secondary selectors
                'div.document',
                'div.entry',
                'div.record',
                '.result-container .result',
                # Table-based results
                'table.results tr',
                'tbody tr'
            ]
            
            found_results = []
            for selector in result_selectors:
                try:
                    found_results = soup.select(selector)
                    if found_results and len(found_results) > 1:  # Need more than just header
                        logger.info(f"OpenEdition: Found {len(found_results)} results with selector: {selector}")
                        break
                except Exception as e:
                    logger.warning(f"OpenEdition selector {selector} failed: {e}")
                    continue
            
            # If no structured results, try to find any publication links
            if not found_results:
                logger.info("OpenEdition: No structured results found, looking for publication links")
                # Look for links that might be publications
                pub_links = soup.find_all('a', href=True)
                potential_results = []
                
                for link in pub_links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    # Look for links that seem like OpenEdition publications
                    if (href and text and len(text) > 10 and 
                        ('openedition' in href or 'revues.org' in href or 'books.openedition' in href or
                        'journals.openedition' in href or href.startswith('/') or 
                        any(keyword in href.lower() for keyword in ['article', 'chapter', 'book', 'document']))):
                        potential_results.append(link.parent or link)
                
                if potential_results:
                    found_results = potential_results[:max_results * 2]
                    logger.info(f"OpenEdition: Found {len(found_results)} potential publication links")
            
            if not found_results:
                logger.warning("OpenEdition: No results found with any method")
                return []
            
            # Process found results
            processed_count = 0
            for i, result_element in enumerate(found_results):
                if processed_count >= max_results:
                    break
                    
                try:
                    # Extract title - try multiple approaches
                    title = ""
                    title_selectors = [
                        'h3 a', 'h4 a', 'h2 a', 'h1 a',
                        '.title a', '.document-title a', '.article-title a',
                        'a[href*="openedition"]', 'a[href*="revues"]', 'a[href*="books"]',
                        '.result-title', '.title', '.publication-title',
                        'h3', 'h4', 'h2', 'h1'
                    ]
                    
                    for title_sel in title_selectors:
                        title_elem = result_element.select_one(title_sel)
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            if len(title) > 5:  # Must be substantial
                                break
                    
                    # If still no title, try getting any prominent text
                    if not title or len(title) < 5:
                        title_elem = result_element.find('a')
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                    
                    # Extract URL
                    url = ""
                    url_selectors = [
                        'a[href*="openedition"]', 'a[href*="revues"]', 'a[href*="books"]',
                        'h3 a', 'h4 a', 'h2 a', '.title a', '.document-title a',
                        '.article-title a', '.publication-title a'
                    ]
                    
                    for url_sel in url_selectors:
                        url_elem = result_element.select_one(url_sel)
                        if url_elem and url_elem.get('href'):
                            url = url_elem.get('href')
                            # Make absolute URL if needed
                            if url.startswith('/'):
                                url = f"https://search.openedition.org{url}"
                            elif not url.startswith('http'):
                                url = f"https://search.openedition.org/{url}"
                            break
                    
                    # Extract metadata (authors, date, journal/book info, etc.)
                    authors = []
                    date = ""
                    abstract = ""
                    journal_or_book = ""
                    publication_type = ""
                    
                    # Look for author information
                    author_selectors = [
                        '.author', '.creator', '.authors', '.by-author',
                        '[class*="author"]', '[class*="creator"]',
                        '.metadata .author', '.byline'
                    ]
                    for auth_sel in author_selectors:
                        author_elems = result_element.select(auth_sel)
                        for auth_elem in author_elems[:3]:  # Max 3 authors
                            author_text = auth_elem.get_text(strip=True)
                            if author_text and len(author_text) > 2 and author_text not in authors:
                                authors.append(author_text)
                    
                    # Look for publication date
                    date_selectors = [
                        '.date', '.publication-date', '.published-date', '.year',
                        '[class*="date"]', '.metadata .date'
                    ]
                    for date_sel in date_selectors:
                        date_elem = result_element.select_one(date_sel)
                        if date_elem:
                            date_text = date_elem.get_text(strip=True)
                            # Look for year pattern
                            import re
                            year_match = re.search(r'\b(19|20)\d{2}\b', date_text)
                            if year_match:
                                date = year_match.group(0)
                                break
                    
                    # Look for journal/book information
                    pub_selectors = [
                        '.journal', '.book', '.publication', '.source',
                        '.journal-title', '.book-title', '.collection',
                        '[class*="journal"]', '[class*="book"]'
                    ]
                    for pub_sel in pub_selectors:
                        pub_elem = result_element.select_one(pub_sel)
                        if pub_elem:
                            pub_text = pub_elem.get_text(strip=True)
                            if len(pub_text) > 3:
                                journal_or_book = pub_text
                                break
                    
                    # Determine publication type based on URL or context
                    if url:
                        if 'books.openedition' in url or 'book' in url.lower():
                            publication_type = "Book"
                        elif 'journals.openedition' in url or 'revues' in url:
                            publication_type = "Journal Article"
                        else:
                            publication_type = "Article"
                    else:
                        publication_type = "Publication"
                    
                    # Look for abstract/description
                    desc_selectors = [
                        '.abstract', '.description', '.summary', '.excerpt',
                        '.content-preview', '[class*="abstract"]', '.teaser'
                    ]
                    for desc_sel in desc_selectors:
                        desc_elem = result_element.select_one(desc_sel)
                        if desc_elem:
                            desc_text = desc_elem.get_text(strip=True)
                            if len(desc_text) > 20:  # Substantial description
                                abstract = desc_text[:500]  # Limit length
                                break
                    
                    # Only add if we have at least a title
                    if title and len(title) > 5:
                        # Set default journal if none found
                        if not journal_or_book:
                            journal_or_book = "OpenEdition"
                        
                        result = {
                            "title": title,
                            "authors": authors,
                            "publication_date": date,
                            "journal": journal_or_book,
                            "abstract": abstract,
                            "url": url or f"https://search.openedition.org/results?searchdomain=openedition&q={urllib.parse.quote(query)}",
                            "source": "OpenEdition",
                            "content": f"Title: {title}\nAuthors: {'; '.join(authors)}\nPublication: {journal_or_book}\nType: {publication_type}\nDate: {date}\nAbstract: {abstract}",
                            "query": query,
                            "valid": True,
                            "tokens": 0,
                            "publication_type": publication_type,
                            "platform": "OpenEdition"
                        }
                        
                        results.append(result)
                        processed_count += 1
                        
                except Exception as e:
                    logger.warning(f"OpenEdition: Error parsing result {i}: {e}")
                    continue
            
            logger.info(f"OpenEdition: Successfully parsed {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"OpenEdition: Error parsing results: {e}")
            return []