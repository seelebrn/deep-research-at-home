# Setup Instructions

## Quick Setup (5 minutes)

### 1. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set up LMStudio
1. **Download LMStudio**: https://lmstudio.ai/
2. **Install and open** LMStudio
3. **Download models** 
4. **Start local server**:
   - Go to "Local Server" tab
   - Load your research model
   - Click "Start Server"
   - Default URL: `http://localhost:1234`

### 3. Configure Environment
```bash
# Copy template
cp .env.template .env

# Edit .env file with your settings
# At minimum, verify LM_STUDIO_URL is correct
```

### 4. Test Run
```bash
python main.py
```

## Detailed Setup

### LMStudio Model Setup

**Minimum Requirements (4GB+ VRAM):**
- Research: `qwen2.5-7b-longpo-128k-i1` (4.5GB)
- Embedding: `granite-embedding:30m` (120MB)
- Use same model for synthesis

**Recommended Setup (8GB+ VRAM):**
- Research: `qwen2.5-7b-longpo-128k-i1` (4.5GB)  
- Synthesis: `qwen2.5-14b-instruct` (8GB)
- Embedding: `granite-embedding:30m` (120MB)

**High-Quality Setup (16GB+ VRAM):**
- Research: `gemma3-12b` (7GB)
- Synthesis: `gemma3-27b` (16GB) 
- Embedding: `granite-embedding:30m` (120MB)

### Search Engine Setup

**Option 1: Default SearXNG (Recommended)**
- Uses public SearXNG instance
- No additional setup required
- Update `SEARCH_URL` in `.env` if needed

**Option 2: Local SearXNG**
```bash
# Using Docker
docker run -d -p 8080:8080 searxng/searxng

# Update .env
SEARCH_URL=http://localhost:8080/search?q=
```

**Option 3: Custom Search API**
- Implement your own search in `deep_research.py`
- Modify `_fallback_search` method
- Return results in format: `[{"title": "", "url": "", "snippet": ""}]`

### Performance Optimization

**For 4GB VRAM Systems:**
```env
RESEARCH_MODEL=qwen2.5-7b-longpo-128k-i1
SYNTHESIS_MODEL=qwen2.5-7b-longpo-128k-i1  # Same model
MAX_CYCLES=8
COMPRESSION_LEVEL=6
SEARCH_RESULTS_PER_QUERY=2
```

**For 8GB+ VRAM Systems:**
```env
RESEARCH_MODEL=qwen2.5-7b-longpo-128k-i1  
SYNTHESIS_MODEL=qwen2.5-14b-instruct
MAX_CYCLES=15
COMPRESSION_LEVEL=4
SEARCH_RESULTS_PER_QUERY=3
```

**For 16GB+ VRAM Systems:**
```env
RESEARCH_MODEL=gemma3-12b
SYNTHESIS_MODEL=gemma3-27b
MAX_CYCLES=20
COMPRESSION_LEVEL=3
SEARCH_RESULTS_PER_QUERY=4
```

## Common Setup Issues

### "Connection refused" to LMStudio
1. Verify LMStudio is running
2. Check "Local Server" tab shows "Server running"
3. Test URL in browser: http://localhost:1234/v1/models
4. Update `LM_STUDIO_URL` in `.env` if using different port

### "Model not found" errors
1. Ensure model is loaded in LMStudio
2. Check exact model name in LMStudio matches `.env` 
3. Try unloading/reloading model in LMStudio
4. Verify model supports chat completions (not just embeddings)

### "No search results" errors
1. Test search URL manually in browser
2. Check internet connection
3. Try different `SEARCH_URL` in `.env`
4. Verify search API returns JSON format

### Research "skips to synthesis"
1. Ensure `INTERACTIVE_RESEARCH=true` in `.env`
2. Clear any cached state by restarting
3. Check model has enough context length for research cycles
4. Verify embedding model is working for content analysis

### Slow performance
1. Reduce `MAX_CYCLES` to 8-10
2. Increase `COMPRESSION_LEVEL` to 6-8  
3. Use smaller models (7B instead of 14B+)
4. Reduce `SEARCH_RESULTS_PER_QUERY`
5. Set `STEPPED_SYNTHESIS_COMPRESSION=false`

## Verification Tests

### Test 1: Basic Functionality
```bash
python main.py
# Enter: "test query"
# Should show: research outline and ask for feedback
```

### Test 2: Model Communication
```python
# Test script
import aiohttp
import asyncio

async def test_lmstudio():
    async with aiohttp.ClientSession() as session:
        async with session.get("http://localhost:1234/v1/models") as resp:
            print(f"Status: {resp.status}")
            print(f"Models: {await resp.json()}")

asyncio.run(test_lmstudio())
```

### Test 3: Search Integration
```python
# Test search URL in browser or curl
curl "http://192.168.1.1:8888/search?q=test"
# Should return JSON with search results
```

## Advanced Configuration

### Custom Models
Add your own models to LMStudio and update `.env`:
```env
RESEARCH_MODEL=your-custom-model-name
SYNTHESIS_MODEL=your-synthesis-model
```

### Multiple LMStudio Instances
Run different models on different ports:
```env
# Instance 1 (Research): Port 1234
# Instance 2 (Synthesis): Port 1235
LM_STUDIO_URL=http://localhost:1234
# Modify code to use different URLs for different models
```

### Resource Monitoring
Monitor VRAM usage:
```bash
# NVIDIA
nvidia-smi -l 1

# AMD  
rocm-smi -l 1
```

## Next Steps

After successful setup:
1. Try a simple research query
2. Experiment with different feedback commands
3. Review generated research reports
4. Adjust configuration for your hardware
5. Explore advanced features in README.md
