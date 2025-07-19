# Deep Research System

Important Acknowledgement : This project is based on - and reuses code from - atineiatte's (https://github.com/atineiatte) Deep Research At Home (https://github.com/atineiatte/deep-research-at-home)

An AI-powered academic research automation system that conducts comprehensive, multi-cycle research with intelligent source discovery, semantic analysis, and structured synthesis.

## 🎯 What It Does

The Deep Research System automates the entire research process:

1. **Query Analysis**: Breaks down your research question into comprehensive search strategies
2. **Multi-Source Search**: Searches academic databases (PubMed, HAL, arXiv, CrossRef, PEPITE) and web sources
3. **Intelligent Filtering**: Uses semantic analysis to identify the most relevant sources
4. **Iterative Research**: Conducts multiple research cycles, adapting based on findings
5. **Knowledge Persistence**: Stores sources locally for future research sessions
6. **Comprehensive Synthesis**: Generates structured reports with proper citations and bibliography
7. **Interactive Feedback**: Allows you to refine research direction during the process

## 🏗️ System Architecture

```
User Query → Research Outline Generation → Multi-Cycle Research → Synthesis → Report
     ↓              ↓                           ↓              ↓         ↓
Query Analysis → Feedback Loop → Source Discovery → Compression → Export
```

### Key Components

- **`deep_research.py`**: Core research pipeline and orchestration
- **`academia.py`**: Academic database integrations (PubMed, HAL, PEPITE, etc.)
- **`deep_storage.py`**: ChromaDB-based knowledge persistence
- **`knowledge_chat.py`**: Interactive chat with your research database
- **`main.py`**: Standalone CLI interface

## 🚀 Quick Start

### Prerequisites

1. **Python 3.8+**
2. **LM Studio** or compatible OpenAI API server running locally
3. **Search API** (SearXNG recommended)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd deep-research-system
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install spaCy models for keyword extraction:
```bash
python -m spacy download fr_core_news_sm  # French
python -m spacy download en_core_web_sm   # English
```

4. Set up your environment (see [Configuration](#configuration)):
```bash
cp .env.example .env
# Edit .env with your settings
```

### Basic Usage

```bash
# Run interactive research
python main.py

# Use specific knowledge database
python main.py --kn medical_research

# List available knowledge databases
python main.py --kn-list

# Chat with your research data
python knowledge_chat.py --kn medical_research
```

## ⚙️ Configuration

### Environment Variables (.env file)

```bash
# LM Studio Configuration
LM_STUDIO_URL=http://localhost:1234
RESEARCH_MODEL=qwen2.5-7b-longpo-128k-i1
SYNTHESIS_MODEL=qwen2.5-7b-longpo-128k-i1
EMBEDDING_MODEL=granite-embedding:30m
VERIFICATION_MODEL=phi-4-reasoning-plus
QUALITY_FILTER_MODEL=qwen2.5-7b-longpo-128k-i1

# Search Configuration
SEARCH_URL=http://127.0.0.1:8888/search?q=

# Academic Database Settings
ACADEMIC_PRIORITY=true
ACADEMIC_DATABASES=pubmed,hal,pepite,arxiv,crossref
ACADEMIC_RESULTS_PER_QUERY=3
CROSSREF_EMAIL=research@example.com

# Research Behavior
MAX_CYCLES=15
MIN_CYCLES=10
SEARCH_RESULTS_PER_QUERY=3
SUCCESSFUL_RESULTS_PER_QUERY=1
TEMPERATURE=0.7
SYNTHESIS_TEMPERATURE=0.6

# Quality Control
QUALITY_FILTER_ENABLED=true
QUALITY_SIMILARITY_THRESHOLD=0.60
VERIFY_CITATIONS=true
ENABLE_FINAL_VERIFICATION=true

# Content Processing
EXTRACT_CONTENT_ONLY=true
HANDLE_PDFS=true
PDF_MAX_PAGES=25
MAX_RESULT_TOKENS=4000
COMPRESSION_LEVEL=4

# Knowledge Base
USE_KNOWLEDGE_BASE=true
KB_MIN_SIMILARITY=0.5
KB_LOCAL_SOURCES_THRESHOLD=2
KB_MAX_SOURCES_PER_QUERY=5

# Advanced Features
INTERACTIVE_RESEARCH=true
SEMANTIC_TRANSFORMATION_STRENGTH=0.7
EXPORT_RESEARCH_DATA=true
```

### Command Line Flags

```bash
# Knowledge Database Management
--kn, --knowledge <name>    # Specify knowledge database
--kn-list                   # List available databases

# Knowledge Chat
--lm-studio-url <url>       # LM Studio server URL
--chat-model <model>        # Chat model name
--embedding-model <model>   # Embedding model name
--max-sources <int>         # Max context sources (default: 5)
--similarity-threshold <float> # Min similarity (default: 0.3)
```

## 🔄 Research Flow

### 1. Query Processing
- **Input**: Your research question
- **Process**: NLP-based keyword extraction and query analysis
- **Output**: Structured research outline

### 2. Interactive Feedback (Optional)
```
Research Outline Generated
↓
User Feedback Prompt: "Keep items 1,3,5-7" or "Focus on practical applications"
↓
Refined Research Direction
```

### 3. Multi-Cycle Research
```
Cycle 1: Broad exploratory queries
↓
Cycle 2-N: Targeted queries based on findings
↓
Each cycle: Source discovery → Quality filtering → Content extraction
```

### 4. Synthesis & Export
- **Section Generation**: Structured content with inline citations
- **Bibliography**: Automatically generated from sources
- **Verification**: Citation accuracy checking
- **Export**: Clean report + detailed source data

## 🎛️ Key Features

### Academic Database Integration
- **PubMed**: Medical and life sciences
- **HAL**: French academic repository
- **PEPITE**: Université de Lille repository
- **arXiv**: Preprints and research papers
- **CrossRef**: DOI-based academic sources
- **SUDOC**: French university catalog

### Intelligent Processing
- **Semantic Compression**: Reduces content while preserving meaning
- **Quality Filtering**: AI-powered relevance assessment
- **Citation Verification**: Validates citations against sources
- **Preference Learning**: Adapts to user feedback

### Knowledge Persistence
- **ChromaDB Integration**: Vector database for source storage
- **Semantic Search**: Find relevant past research
- **Cross-Session Learning**: Build knowledge over time

## 🛠️ Advanced Configuration

### Research Behavior Tuning

```python
# In .env or programmatically
CHUNK_LEVEL=2                    # 1=phrase, 2=sentence, 3=paragraph
COMPRESSION_LEVEL=4              # 1=minimal, 10=maximum compression
LOCAL_INFLUENCE_RADIUS=3         # Context window for semantic analysis
QUERY_WEIGHT=0.5                 # Balance query vs document relevance
SEMANTIC_TRANSFORMATION_STRENGTH=0.7  # User preference influence
```

### Domain Prioritization

```bash
# Prioritize specific domains
DOMAIN_PRIORITY=.edu,.gov,.org,pubmed.ncbi.nlm.nih.gov

# Prioritize content keywords
CONTENT_PRIORITY="evidence-based medicine,clinical trials,meta-analysis"

# Scoring multipliers
DOMAIN_MULTIPLIER=1.3
KEYWORD_MULTIPLIER_PER_MATCH=1.1
MAX_KEYWORD_MULTIPLIER=2.0
```

## 🚨 Common Issues & Solutions

### Setup Issues

**Problem**: `ModuleNotFoundError: No module named 'spacy'`
```bash
pip install spacy
python -m spacy download en_core_web_sm
```

**Problem**: `ChromaDB connection failed`
```bash
# Ensure write permissions
chmod -R 755 ./DBs/
```

**Problem**: `LM Studio connection refused`
```bash
# Check LM Studio is running on correct port
curl http://localhost:1234/v1/models
```

### Research Issues

**Problem**: No search results found
- Check `SEARCH_URL` is accessible
- Verify SearXNG or search API is running
- Try broader search terms

**Problem**: Academic sources not working
- Verify `ACADEMIC_DATABASES` configuration
- Check internet connectivity for database APIs
- Some databases may have rate limits

**Problem**: Citations not verifying
```bash
# Disable if problematic
VERIFY_CITATIONS=false
```

### Performance Issues

**Problem**: Research too slow
```bash
# Reduce cycles and sources
MAX_CYCLES=8
SEARCH_RESULTS_PER_QUERY=2
ACADEMIC_RESULTS_PER_QUERY=2
```

**Problem**: Memory issues
```bash
# Enable model unloading
UNLOAD_RESEARCH_MODEL=true

# Increase compression
COMPRESSION_LEVEL=6
MAX_RESULT_TOKENS=2000
```

## 🗂️ Knowledge Database Management

### Creating Specialized Databases

```bash
# Medical research database
python main.py --kn medical

# Legal research database  
python main.py --kn legal

# Each creates: ./DBs/{name}_knowledge_db/
```

### Chatting with Research Data

```bash
# Interactive chat with accumulated research
python knowledge_chat.py --kn medical

# Example queries:
# "What did I find about drug interactions?"
# "Summarize the regulatory frameworks from my research"
# "Which sources discuss side effects?"
```

## 📁 File Structure

```
deep-research-system/
├── .env                    # Environment configuration
├── deep_research.py        # Core research engine
├── academia.py            # Academic database integrations
├── deep_storage.py         # Knowledge persistence
├── knowledge_chat.py       # Interactive chat interface
├── main.py                # CLI interface
├── requirements.txt        # Python dependencies
├── DBs/                   # Knowledge databases
│   ├── research_knowledge_db/
│   ├── medical_knowledge_db/
│   └── ...
└── research_export_*/     # Exported research files
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and test thoroughly
4. Submit a pull request with detailed description

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments
- atineiatte's (https://github.com/atineiatte) for developing Deep Research At Home (https://github.com/atineiatte/deep-research-at-home)
- Academic database integrations
- ChromaDB for vector storage
- spaCy for natural language processing

## 📞 Support

For issues and questions:
1. Check the [Common Issues](#-common-issues--solutions) section
2. Review your `.env` configuration
3. Ensure all dependencies are installed correctly
4. Check logs for specific error messages

---

**Happy Researching! 🎓🔬**
