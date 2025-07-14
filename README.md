## Acknowledgments
Based on the [Deep Research Open-WebUI Pipe](https://github.com/atineiatte/deep-research-at-home) by atineiatte. He/she did all the heavy lifting.

I just cut all ties with open-webui and adapted the script to a simple OpenAI compatible API, also add command line args to optimize the whole process. 

Made a little fast config script too, that can't be bad.

Simplified the whole process a bit, it's still incredibly strong.

And a few little tweaks here and there.

Have fun and enjoy superior reasoning power (and responsibilities) !

~Cadenza


# Deep Research at Home

An advanced AI-powered research system that conducts comprehensive literature reviews and generates detailed reports with citations and bibliography.

## Features

- **Interactive Research**: AI generates research outline and asks for your feedback
- **Web Search Integration**: Automatically searches and processes web content
- **Citation Management**: Numbered citations with verification and bibliography
- **Multi-Model Support**: Uses different models for research vs synthesis
- **Semantic Analysis**: Advanced content filtering and relevance scoring
- **Export Functionality**: Saves complete research data for future reference
- **PDF Processing**: Extracts and analyzes PDF documents
- **Adaptive Research**: Learns from previous cycles to improve query generation

## Quick Start

1. **Clone/Download** the repository
2. **Install dependencies**: `pip install -r requirements.txt`
3. **Configure environment** (see Configuration section)
4. **Run**: `python main.py`

## System Requirements

- Python 3.8+
- 4GB+ RAM (8GB+ recommended for large research projects)
- Internet connection for web searches
- LMStudio or compatible API server running locally

## Installation

### 1. Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set up LMStudio
1. Download and install [LMStudio](https://lmstudio.ai/)
2. Load your preferred models (see Model Recommendations)
3. Start the local server (default: http://localhost:1234)

### 3. Set up Search Engine (Optional)
- Default: Uses SearXNG at http://192.168.1.1:8888
- Alternative: Configure your own search API
- See Configuration section for details

## Configuration

Create a `.env` file in the project directory:

```env
# LMStudio Configuration
LM_STUDIO_URL=http://localhost:1234

# Model Configuration
RESEARCH_MODEL=qwen2.5-7b-longpo-128k-i1
SYNTHESIS_MODEL=qwen2.5-14b-instruct
EMBEDDING_MODEL=granite-embedding:30m
QUALITY_FILTER_MODEL=gemma3:4b

# Search Configuration
SEARCH_URL=http://192.168.1.1:8888/search?q=

# Research Parameters
MAX_CYCLES=15
TEMPERATURE=0.7
ENABLED=true
```

## Model Recommendations

### Research Model (Primary)
- **Qwen2.5-7B-Longpo-128k**: Excellent for query generation and analysis
- **Gemma3-12B**: Good balance of speed and quality
- **Llama3-8B-Instruct**: Reliable alternative

### Synthesis Model (Report Writing)
- **Qwen2.5-14B-Instruct**: Superior for long-form writing
- **Gemma3-27B**: High quality but requires more VRAM
- **Same as research model**: Use if VRAM limited

### Embedding Model
- **Granite-Embedding-30M**: Fast and accurate
- **Nomic-Embed-Text**: Good alternative
- **BGE-M3**: Multilingual support

## Usage

### Basic Research
```bash
python main.py
```
Enter your research question when prompted. The system will:
1. Generate initial search queries
2. Collect and analyze web results  
3. Create research outline
4. **Ask for your feedback** ← Interactive step
5. Conduct detailed research cycles
6. Generate comprehensive report with citations

### Feedback Commands
When the system shows the research outline:

- `/keep 1,3,5-7` - Keep only specified items
- `/remove 2,4,8-10` - Remove specified items  
- `"focus on historical aspects"` - Natural language guidance
- `"continue"` - Proceed with all items

### Example Research Topics
- "What are the latest developments in quantum computing?"
- "Analyze the environmental impact of cryptocurrency mining"
- "François-Vincent Raspail's stance on self diagnosis"
- "Current trends in remote work productivity"

## Configuration Options

### Research Settings
```python
MAX_CYCLES = 15              # Maximum research cycles
MIN_CYCLES = 10              # Minimum cycles before stopping
SEARCH_RESULTS_PER_QUERY = 3 # Results per search
SUCCESSFUL_RESULTS_PER_QUERY = 1  # Results to keep
```

### Quality Control
```python
QUALITY_FILTER_ENABLED = True        # Enable content filtering
QUALITY_SIMILARITY_THRESHOLD = 0.60  # Relevance threshold
VERIFY_CITATIONS = True              # Verify citation accuracy
```

### Compression Settings
```python
COMPRESSION_LEVEL = 4                # 1-10 (higher = more compression)
MAX_RESULT_TOKENS = 4000            # Token limit per result
STEPPED_SYNTHESIS_COMPRESSION = True # Tiered compression
```

## Output Files

The system generates several output files:

- **Console Output**: Full research report with citations
- **Export File**: `research_export_[query]_[timestamp].txt`
  - Contains all search results, queries, and metadata
  - Raw research data for analysis
- **Bibliography**: Automatically generated with numbered citations

## Troubleshooting

### Common Issues

**"No search results found"**
- Check your search URL configuration
- Verify internet connection
- Try different search queries

**"Model not found"**
- Ensure LMStudio is running
- Check model names in .env file
- Verify models are loaded in LMStudio

**"Research skips to synthesis"**
- Check INTERACTIVE_RESEARCH setting
- Verify conversation state is clean
- Restart with fresh conversation

**"Citations not working"**
- Enable VERIFY_CITATIONS in config
- Check web search functionality
- Verify URL accessibility

### Performance Tips

**For slower systems:**
- Reduce MAX_CYCLES to 8-10
- Use smaller models (7B instead of 14B+)
- Increase COMPRESSION_LEVEL to 6-8
- Reduce SEARCH_RESULTS_PER_QUERY to 2

**For better quality:**
- Increase MAX_CYCLES to 20+
- Use larger synthesis models (27B+)
- Lower COMPRESSION_LEVEL to 2-3
- Enable all quality filters

## Advanced Features

### Custom Search Integration
Replace the default search with your own API:
```python
# In deep_research.py, modify _fallback_search method
async def _fallback_search(self, query: str) -> List[Dict]:
    # Your custom search implementation
    pass
```

### Model Swapping
Switch models mid-research by updating the valves:
```python
pipe.valves.SYNTHESIS_MODEL = "your-preferred-model"
```

### Research State Management
Access research state programmatically:
```python
state = pipe.get_state()
results = state.get("results_history", [])
outline = state.get("research_state", {}).get("research_outline", [])
```

## API Integration

The research pipe can be integrated into larger applications:

```python
from deep_research import Pipe, User

# Initialize
pipe = Pipe()
user = User(id="user123", name="Researcher")

# Configure
pipe.valves.RESEARCH_MODEL = "your-model"
pipe.valves.INTERACTIVE_RESEARCH = False  # Disable for API use

# Run research
result = await pipe.pipe(
    body={"messages": [{"content": "your query", "role": "user"}]},
    __user__=user.__dict__,
    __event_emitter__=your_event_handler,
    __event_call__=your_event_call_handler
)
```

## Contributing

This project is based on the original [Deep Research at Home](https://github.com/atineiatte/deep-research-at-home) by atineiatte.

### Development Setup
1. Fork the repository
2. Create virtual environment: `python -m venv venv`
3. Install dev dependencies: `pip install -r requirements-dev.txt`
4. Make changes and test thoroughly
5. Submit pull request

## License

This project maintains the same license as the original Deep Research at Home project. Please refer to the original repository for license details.

## Support

For issues and questions:
1. Check the Troubleshooting section above
2. Review the original project documentation
3. Create an issue with detailed error information

## Acknowledgments

- Original Deep Research at Home by [atineiatte](https://github.com/atineiatte)
- LMStudio team for the excellent local LLM server
- SearXNG project for privacy-focused search
- The open source LLM community
