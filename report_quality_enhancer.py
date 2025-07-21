"""
Fixed Complex Report Quality Enhancement Module
High-quality analysis with clean output - no clutter
"""

import json
import re
import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)

class ReportQualityEnhancer:
    """Advanced quality enhancement that produces clean, final reports only"""
    
    def __init__(self, pipe_instance):
        """Initialize with reference to main pipe instance"""
        self.pipe = pipe_instance
        self.valves = pipe_instance.valves
        
    async def enhance_report_comprehensively_clean(self, comprehensive_answer: str, user_query: str, sections: Dict[str, str] = None) -> str:
        """
        Main function for comprehensive enhancement with clean output
        Combines the analytical power of the complex system with clean presentation
        """
        
        logger.info("Starting comprehensive clean report enhancement")
        
        # If sections not provided, extract from comprehensive answer
        if sections is None:
            sections = self._extract_sections_from_text(comprehensive_answer)
        
        await self.pipe.emit_status("info", "Analyzing report structure and themes...", False)
        
        # Phase 1: Advanced Analysis (internal only - not added to output)
        analysis_results = await self._comprehensive_analysis_phase(comprehensive_answer, user_query, sections)
        
        await self.pipe.emit_status("info", "Applying comprehensive enhancements...", False)
        
        # Phase 2: Apply all enhancements in single clean pass
        enhanced_content = await self._apply_all_enhancements_cleanly(
            comprehensive_answer, user_query, analysis_results
        )
        
        await self.pipe.emit_status("info", "Finalizing report format...", False)
        
        # Phase 3: Final clean formatting
        final_report = await self._final_clean_format(enhanced_content)
        
        # Phase 4: Verify cleanliness and remove any remaining clutter
        final_report = self._ensure_absolute_cleanliness(final_report)
        
        logger.info("Comprehensive clean report enhancement complete")
        return final_report
    
    async def _comprehensive_analysis_phase(self, content: str, user_query: str, sections: Dict[str, str]) -> Dict:
        """
        Perform all analytical work internally - results not added to output
        """
        analysis_results = {
            "thematic_analysis": {},
            "citation_analysis": {},
            "flow_analysis": {},
            "relevance_analysis": {},
            "structural_analysis": {}
        }
        
        try:
            # Thematic analysis
            if sections:
                thematic_tracker = ThematicTracker(self.pipe)
                themes = await thematic_tracker.identify_themes(sections)
                if themes:
                    coverage = await thematic_tracker.analyze_theme_coverage(themes, sections)
                    suggestions = await thematic_tracker.suggest_theme_integration(themes, coverage)
                    analysis_results["thematic_analysis"] = {
                        "themes": themes,
                        "coverage": coverage,
                        "suggestions": suggestions
                    }
            
            # Citation analysis
            citation_checker = CitationQualityChecker(self.pipe)
            citation_analysis = await citation_checker.analyze_citation_patterns(content)
            analysis_results["citation_analysis"] = citation_analysis
            
            # Flow analysis
            flow_analyzer = ContentFlowAnalyzer(self.pipe)
            structure_analysis = await flow_analyzer.analyze_paragraph_structure(content)
            transition_analysis = await flow_analyzer.evaluate_transitions(content)
            flow_suggestions = await flow_analyzer.suggest_flow_improvements(structure_analysis, transition_analysis)
            analysis_results["flow_analysis"] = {
                "structure": structure_analysis,
                "transitions": transition_analysis,
                "suggestions": flow_suggestions
            }
            
            # Relevance analysis
            if sections:
                enhancer = ReportQualityEnhancer(self.pipe)
                relevance_results = await enhancer.verify_section_relevance(sections, user_query)
                analysis_results["relevance_analysis"] = relevance_results
            
        except Exception as e:
            logger.error(f"Error in analysis phase: {e}")
            # Continue with basic enhancement if analysis fails
        
        return analysis_results
    
    async def _apply_all_enhancements_cleanly(self, content: str, user_query: str, analysis_results: Dict) -> str:
        """
        Apply all enhancements in a single pass with clean output
        """
        
        # Compile all improvement insights into a single comprehensive prompt
        enhancement_instructions = self._compile_enhancement_instructions(analysis_results, user_query)
        
        comprehensive_prompt = {
            "role": "system",
            "content": f"""You are enhancing a research report on: "{user_query}"

Apply these comprehensive improvements in a single pass:

{enhancement_instructions}

CRITICAL OUTPUT REQUIREMENTS:
- Produce ONLY the enhanced report content
- NO analysis commentary or meta-discussion
- NO process notes or improvement explanations
- NO section-by-section breakdowns
- Preserve ALL citations [X] exactly as written
- Maintain academic tone and factual accuracy
- The output should be a complete, polished research report ready for publication

Apply all improvements seamlessly while maintaining the report's integrity and flow."""
        }
        
        try:
            if len(content) > 12000:
                return await self._process_large_content_cleanly(content, comprehensive_prompt)
            else:
                response = await self.pipe.generate_completion(
                    self.pipe.get_synthesis_model(),
                    [comprehensive_prompt, {"role": "user", "content": content}],
                    temperature=0.3
                )
                
                return response["choices"][0]["message"]["content"]
                
        except Exception as e:
            logger.error(f"Error in comprehensive enhancement: {e}")
            return content
    
    def _compile_enhancement_instructions(self, analysis_results: Dict, user_query: str) -> str:
        """
        Compile all analytical insights into clear enhancement instructions
        """
        instructions = []
        
        # Thematic improvements
        thematic_data = analysis_results.get("thematic_analysis", {})
        if thematic_data.get("suggestions"):
            instructions.append("THEMATIC IMPROVEMENTS:")
            for suggestion in thematic_data["suggestions"][:3]:  # Limit to top 3
                instructions.append(f"- {suggestion.get('suggestion', '')}")
        
        # Citation improvements
        citation_data = analysis_results.get("citation_analysis", {})
        if citation_data.get("integration_quality") == "needs_improvement":
            instructions.append("CITATION IMPROVEMENTS:")
            instructions.append("- Improve citation integration into natural sentence flow")
            instructions.append("- Distribute citations more evenly throughout sections")
        
        # Flow improvements
        flow_data = analysis_results.get("flow_analysis", {})
        flow_suggestions = flow_data.get("suggestions", [])
        if flow_suggestions:
            instructions.append("FLOW IMPROVEMENTS:")
            for suggestion in flow_suggestions[:3]:  # Limit to top 3
                instructions.append(f"- {suggestion}")
        
        # Relevance improvements
        relevance_data = analysis_results.get("relevance_analysis", {})
        low_relevance_sections = [
            section for section, data in relevance_data.items() 
            if data.get("score", 10) < 7
        ]
        if low_relevance_sections:
            instructions.append("RELEVANCE IMPROVEMENTS:")
            instructions.append(f"- Strengthen connection to '{user_query}' in sections: {', '.join(low_relevance_sections[:3])}")
        
        # General quality improvements
        instructions.extend([
            "GENERAL QUALITY IMPROVEMENTS:",
            "- Enhance paragraph structure with clear topic sentences",
            "- Improve transitions between sections using connecting phrases", 
            "- Strengthen evidence integration and analysis",
            "- Ensure logical progression from introduction to conclusion",
            "- Fix any grammatical issues or awkward phrasing",
            "- Standardize writing style for consistency"
        ])
        
        return "\n".join(instructions)
    
    async def _process_large_content_cleanly(self, content: str, enhancement_prompt: Dict) -> str:
        """
        Process large content while maintaining clean output
        """
        # Split by major sections but process more holistically
        sections = re.split(r'\n(?=##\s)', content)
        enhanced_sections = []
        
        for i, section in enumerate(sections):
            if len(section.strip()) < 100:
                enhanced_sections.append(section)
                continue
            
            await self.pipe.emit_status("info", f"Enhancing section {i+1}/{len(sections)}", False)
            
            try:
                response = await self.pipe.generate_completion(
                    self.pipe.get_synthesis_model(),
                    [enhancement_prompt, {"role": "user", "content": section}],
                    temperature=0.3
                )
                
                enhanced_section = response["choices"][0]["message"]["content"]
                enhanced_sections.append(enhanced_section)
                
            except Exception as e:
                logger.error(f"Error processing section {i+1}: {e}")
                enhanced_sections.append(section)
        
        return '\n\n'.join(enhanced_sections)
    
    async def _final_clean_format(self, content: str) -> str:
        """
        Final formatting pass for professional presentation
        """
        formatting_prompt = {
            "role": "system",
            "content": """Apply final professional formatting to this research report:

FORMATTING REQUIREMENTS:
- Ensure consistent header hierarchy (# Title, ## Sections, ### Subsections)
- Organize bibliography/references at the end if not already there
- Clean up any formatting inconsistencies
- Ensure proper paragraph spacing
- Standardize citation format
- Verify smooth transitions between sections

OUTPUT: A professionally formatted, publication-ready report.
NO commentary about formatting changes made."""
        }
        
        try:
            response = await self.pipe.generate_completion(
                self.pipe.get_synthesis_model(),
                [formatting_prompt, {"role": "user", "content": content}],
                temperature=0.2
            )
            
            return response["choices"][0]["message"]["content"]
            
        except Exception as e:
            logger.error(f"Error in final formatting: {e}")
            return content
    
    def _ensure_absolute_cleanliness(self, content: str) -> str:
        """
        Final pass to ensure absolutely no clutter remains
        """
        # Remove any clutter patterns that might have been introduced
        clutter_patterns = [
            r"---\s*\n\n.*?improvements?.*?(?=\n##|\n# |\Z)",  # Improvement sections
            r"### (Analysis|Breakdown|Notes?|Explanation).*?(?=\n##|\n# |\Z)",  # Analysis sections
            r"This (revised|enhanced|improved) version.*?(?=\n##|\n# |\n\n)",  # Version notes
            r"\*\*Analysis:?\*\*.*?(?=\n\*\*|\n##|\n# |\n\n)",  # Analysis blocks
            r"\*\*Improvements?:?\*\*.*?(?=\n\*\*|\n##|\n# |\n\n)",  # Improvement blocks
            r"(The following|These) (changes|improvements|enhancements).*?(?=\n##|\n# |\n\n)",  # Change descriptions
        ]
        
        for pattern in clutter_patterns:
            content = re.sub(pattern, "", content, flags=re.DOTALL | re.MULTILINE | re.IGNORECASE)
        
        # Clean up multiple consecutive newlines
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # Remove any remaining meta-commentary
        content = re.sub(r'^(Furthermore|Moreover|Additionally|In summary),? this (section|analysis|report).*?\n', '', content, flags=re.MULTILINE)
        
        return content.strip()
    
    def _extract_sections_from_text(self, text: str) -> Dict[str, str]:
        """Extract sections from a text based on markdown headers"""
        sections = {}
        current_section = None
        current_content = []
        
        lines = text.split('\n')
        
        for line in lines:
            # Check for section headers (## Header)
            header_match = re.match(r'^##\s+(.+)$', line)
            if header_match:
                # Save previous section
                if current_section and current_content:
                    sections[current_section] = '\n'.join(current_content).strip()
                
                # Start new section
                current_section = header_match.group(1).strip()
                current_content = []
            else:
                # Add line to current section
                if current_section:
                    current_content.append(line)
        
        # Save last section
        if current_section and current_content:
            sections[current_section] = '\n'.join(current_content).strip()
        
        return sections


# Keep the existing utility classes but ensure they don't add content to output
class ThematicTracker:
    """Track themes across sections for better integration - analysis only"""
    
    def __init__(self, pipe_instance):
        self.pipe = pipe_instance
        self.main_themes = {}
        self.theme_coverage = {}

    async def identify_themes(self, sections: Dict[str, str]) -> Dict[str, List[str]]:
        """Extract recurring themes across sections - for analysis only"""
        
        theme_prompt = {
            "role": "system",
            "content": """Identify the main themes that appear across these research sections.

Return themes as a JSON object with theme names as keys and lists of sections as values.
Format: {"theme_name": ["section1", "section2"], "another_theme": ["section3"]}"""
        }
        
        # Build context with all sections (truncated for analysis)
        theme_context = "Sections to analyze:\n\n"
        for title, content in sections.items():
            preview = content[:800] + "..." if len(content) > 800 else content
            theme_context += f"## {title}\n{preview}\n\n"
        
        try:
            response = await self.pipe.generate_completion(
                self.pipe.get_research_model(),
                [theme_prompt, {"role": "user", "content": theme_context}],
                temperature=0.3
            )
            
            result_text = response["choices"][0]["message"]["content"]
            
            # Parse JSON response
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                themes_data = json.loads(json_match.group())
                return themes_data
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Error identifying themes: {e}")
            return {}
    
    async def analyze_theme_coverage(self, themes: Dict[str, List[str]], sections: Dict[str, str]) -> Dict[str, float]:
        """Analyze theme coverage - for analysis only"""
        coverage_scores = {}
        
        for theme, theme_sections in themes.items():
            section_count = len(theme_sections)
            total_sections = len(sections)
            
            # Base coverage from section distribution
            distribution_score = section_count / total_sections
            
            # Depth score based on content length
            total_theme_content = 0
            for section_name in theme_sections:
                if section_name in sections:
                    total_theme_content += len(sections[section_name])
            
            avg_content_per_section = total_theme_content / max(1, section_count)
            depth_score = min(1.0, avg_content_per_section / 2000)
            
            # Combined coverage score
            coverage_scores[theme] = (distribution_score * 0.6) + (depth_score * 0.4)
        
        return coverage_scores
    
    async def suggest_theme_integration(self, themes: Dict[str, List[str]], coverage: Dict[str, float]) -> List[Dict]:
        """Suggest theme integration improvements - for analysis only"""
        suggestions = []
        
        for theme, score in coverage.items():
            if score < 0.3:  # Low coverage
                suggestions.append({
                    "type": "expand_theme",
                    "theme": theme,
                    "current_score": score,
                    "suggestion": f"Expand coverage of '{theme}' theme throughout the report",
                    "priority": "high" if score < 0.2 else "medium"
                })
            elif score > 0.8:  # Very high coverage
                suggestions.append({
                    "type": "consolidate_theme", 
                    "theme": theme,
                    "current_score": score,
                    "suggestion": f"Consider consolidating redundant discussions of '{theme}'",
                    "priority": "low"
                })
        
        return suggestions


class CitationQualityChecker:
    """Citation quality analysis - analysis only"""
    
    def __init__(self, pipe_instance):
        self.pipe = pipe_instance
        self.valves = pipe_instance.valves
    
    async def analyze_citation_patterns(self, content: str) -> Dict:
        """Analyze citation patterns - for analysis only"""
        
        # Extract all citations
        citations = re.findall(r'\[(\d+)\]', content)
        
        analysis = {
            "total_citations": len(citations),
            "unique_citations": len(set(citations)),
            "citation_density": len(citations) / max(1, len(content.split())),
            "integration_quality": "good"
        }
        
        # Check for citation clustering
        words = content.split()
        citation_positions = []
        for i, word in enumerate(words):
            if '[' in word and ']' in word:
                citation_positions.append(i)
        
        # Find clusters (3+ citations within 50 words)
        clusters = []
        for i in range(len(citation_positions) - 2):
            if citation_positions[i+2] - citation_positions[i] <= 50:
                clusters.append((citation_positions[i], citation_positions[i+2]))
        
        if clusters:
            analysis["integration_quality"] = "needs_improvement"
        
        return analysis


class ContentFlowAnalyzer:
    """Content flow analysis - analysis only"""
    
    def __init__(self, pipe_instance):
        self.pipe = pipe_instance
        self.valves = pipe_instance.valves
    
    async def analyze_paragraph_structure(self, content: str) -> Dict:
        """Analyze paragraph structure - for analysis only"""
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        analysis = {
            "total_paragraphs": len(paragraphs),
            "avg_paragraph_length": sum(len(p.split()) for p in paragraphs) / max(1, len(paragraphs)),
            "short_paragraphs": [],
            "long_paragraphs": []
        }
        
        # Identify problematic paragraph lengths
        for i, para in enumerate(paragraphs):
            word_count = len(para.split())
            if word_count < 30:
                analysis["short_paragraphs"].append(i)
            elif word_count > 200:
                analysis["long_paragraphs"].append(i)
        
        return analysis
    
    async def evaluate_transitions(self, content: str) -> Dict:
        """Evaluate transitions - for analysis only"""
        # Simplified transition analysis for speed
        transition_words = ["furthermore", "moreover", "however", "therefore", "consequently", "meanwhile", "additionally"]
        
        word_count = len(content.split())
        transition_count = sum(content.lower().count(word) for word in transition_words)
        
        transition_density = transition_count / max(1, word_count / 100)  # Per 100 words
        
        if transition_density > 2:
            score = 4
        elif transition_density > 1:
            score = 3
        else:
            score = 2
        
        return {
            "overall_score": score,
            "transition_density": transition_density,
            "improvement_areas": ["Add more transitional phrases between paragraphs"] if score < 3 else []
        }
    
    async def suggest_flow_improvements(self, structure_analysis: Dict, transition_analysis: Dict) -> List[str]:
        """Suggest flow improvements - for analysis only"""
        suggestions = []
        
        # Paragraph length issues
        if len(structure_analysis["short_paragraphs"]) > 3:
            suggestions.append("Combine very short paragraphs with related content")
        
        if len(structure_analysis["long_paragraphs"]) > 2:
            suggestions.append("Break down overly long paragraphs for better readability")
        
        # Transition quality
        if transition_analysis.get("overall_score", 3) < 3:
            suggestions.append("Improve transitions between paragraphs and sections")
        
        return suggestions


# Import the original ReportQualityEnhancer for the verify_section_relevance method
# (We'll just use that one method from the original class)

# Main integration function
async def enhance_report_comprehensively_clean(pipe_instance, comprehensive_answer: str, user_message: str, sections: Dict[str, str] = None) -> str:
    """
    Fixed comprehensive enhancement that produces high-quality, clean reports
    Combines advanced analysis with clean output presentation
    """
    
    # Initialize fixed enhancer
    enhancer = FixedComplexReportEnhancer(pipe_instance)
    
    # Run comprehensive enhancement with clean output
    enhanced_report = await enhancer.enhance_report_comprehensively_clean(
        comprehensive_answer, user_message, sections
    )
    
    return enhanced_report
import json
import re
import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)

class CleanReportEnhancer:
    """Enhanced quality control that produces clean, final reports only"""
    
    def __init__(self, pipe_instance):
        """Initialize with reference to main pipe instance"""
        self.pipe = pipe_instance
        self.valves = pipe_instance.valves
        
    async def enhance_report_cleanly(self, comprehensive_answer: str, user_query: str) -> str:
        """Main enhancement function that returns only the clean final report"""
        
        await self.pipe.emit_status("info", "Enhancing report quality...", False)
        
        # Step 1: Extract and clean structure
        cleaned_content = await self._clean_existing_structure(comprehensive_answer)
        
        # Step 2: Enhance content quality (single pass, no commentary)
        enhanced_content = await self._enhance_content_quality(cleaned_content, user_query)
        
        # Step 3: Final formatting and bibliography organization
        final_report = await self._finalize_report_format(enhanced_content)
        
        await self.pipe.emit_status("info", "Report enhancement complete", False)
        return final_report
    
    async def _clean_existing_structure(self, content: str) -> str:
        """Remove any process commentary and standardize structure"""
        
        cleaning_prompt = {
            "role": "system",
            "content": """Clean this research report by removing ALL process commentary, revision notes, and meta-text.

EXTRACT ONLY:
- Title and abstract
- Main content sections
- Conclusion
- References/Bibliography

REMOVE:
- Revision notes like "Revised version:" or "This revised version..."
- Process commentary like "### Additional Improvements" 
- Meta-text about paragraph structure
- Duplicate content
- Improvement explanations
- Multiple versions of the same content

OUTPUT: A clean, well-structured academic report with clear sections and proper flow.
Preserve all citations [X] exactly as written."""
        }
        
        try:
            response = await self.pipe.generate_completion(
                self.pipe.get_synthesis_model(),
                [cleaning_prompt, {"role": "user", "content": content}],
                temperature=0.2
            )
            
            return response["choices"][0]["message"]["content"]
            
        except Exception as e:
            logger.error(f"Error cleaning structure: {e}")
            return content
    
    async def _enhance_content_quality(self, content: str, user_query: str) -> str:
        """Single-pass content enhancement focused on quality, not process"""
        
        enhancement_prompt = {
            "role": "system",
            "content": f"""Enhance this research report addressing: "{user_query}"

IMPROVEMENTS TO MAKE:
- Improve paragraph flow and transitions
- Strengthen topic sentences
- Enhance evidence integration  
- Fix grammatical issues
- Ensure logical section progression
- Add connecting phrases between sections

CRITICAL REQUIREMENTS:
- Output ONLY the enhanced report content
- NO meta-commentary about changes made
- NO revision notes or improvement explanations
- Preserve ALL citations [X] exactly
- Maintain academic tone throughout
- Keep all factual content intact

The output should be a polished, publication-ready research report."""
        }
        
        try:
            if len(content) > 12000:
                # Process in chunks for very long content
                return await self._process_large_content(content, enhancement_prompt)
            else:
                response = await self.pipe.generate_completion(
                    self.pipe.get_synthesis_model(),
                    [enhancement_prompt, {"role": "user", "content": content}],
                    temperature=0.3
                )
                
                return response["choices"][0]["message"]["content"]
                
        except Exception as e:
            logger.error(f"Error enhancing content quality: {e}")
            return content
    
    async def _process_large_content(self, content: str, enhancement_prompt: Dict) -> str:
        """Process large content in sections while maintaining coherence"""
        
        # Split by major sections (## headers)
        sections = re.split(r'\n(?=##\s)', content)
        enhanced_sections = []
        
        for i, section in enumerate(sections):
            if len(section.strip()) < 100:  # Skip very short sections
                enhanced_sections.append(section)
                continue
                
            await self.pipe.emit_status("info", f"Processing section {i+1}/{len(sections)}", False)
            
            try:
                response = await self.pipe.generate_completion(
                    self.pipe.get_synthesis_model(),
                    [enhancement_prompt, {"role": "user", "content": section}],
                    temperature=0.3
                )
                
                enhanced_section = response["choices"][0]["message"]["content"]
                enhanced_sections.append(enhanced_section)
                
            except Exception as e:
                logger.error(f"Error processing section {i+1}: {e}")
                enhanced_sections.append(section)  # Keep original if enhancement fails
        
        return '\n\n'.join(enhanced_sections)
    
    async def _finalize_report_format(self, content: str) -> str:
        """Final formatting pass to ensure clean, professional structure"""
        
        formatting_prompt = {
            "role": "system",
            "content": """Apply final formatting to this research report:

FORMATTING REQUIREMENTS:
- Ensure consistent header hierarchy (# Title, ## Sections, ### Subsections)
- Organize bibliography/references at the end
- Remove any duplicate sections
- Ensure smooth paragraph breaks
- Standardize citation format
- Clean up any formatting inconsistencies

OUTPUT: A properly formatted, publication-ready report with:
1. Clear title
2. Abstract (if present)
3. Main content sections
4. Conclusion
5. References/Bibliography section

NO meta-commentary or process notes in the output."""
        }
        
        try:
            response = await self.pipe.generate_completion(
                self.pipe.get_synthesis_model(),
                [formatting_prompt, {"role": "user", "content": content}],
                temperature=0.2
            )
            
            formatted_content = response["choices"][0]["message"]["content"]
            
            # Additional cleanup: remove common clutter patterns
            formatted_content = self._remove_clutter_patterns(formatted_content)
            
            return formatted_content
            
        except Exception as e:
            logger.error(f"Error in final formatting: {e}")
            return content
    
    def _remove_clutter_patterns(self, content: str) -> str:
        """Remove common clutter patterns that might remain"""
        
        # Patterns to remove
        clutter_patterns = [
            r"---\s*\n\n### Additional.*?(?=\n##|\n# |\Z)",  # Additional sections
            r"### Breakdown of Improvements:.*?(?=\n##|\n# |\Z)",  # Improvement breakdowns
            r"This revised version.*?(?=\n##|\n# |\n\n)",  # Revision notes
            r"### Notes.*?(?=\n##|\n# |\Z)",  # Notes sections
            r"### Explanation.*?(?=\n##|\n# |\Z)",  # Explanation sections
            r"\*\*Paragraph \d+:.*?\*\*\n.*?(?=\n\*\*|### |## |\Z)",  # Paragraph analysis
            r"- \*\*Topic Sentence:\*\*.*?(?=\n\*\*|\n- |\n\n)",  # Topic sentence analysis
        ]
        
        for pattern in clutter_patterns:
            content = re.sub(pattern, "", content, flags=re.DOTALL | re.MULTILINE)
        
        # Clean up multiple consecutive newlines
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # Remove standalone transition explanations
        content = re.sub(r'^(Furthermore|Moreover|Additionally|In conclusion),? this.*?\n', '', content, flags=re.MULTILINE)
        
        return content.strip()

    async def verify_clean_output(self, content: str) -> bool:
        """Verify the output is clean without process commentary"""
        
        # Check for common clutter indicators
        clutter_indicators = [
            "revised version",
            "improvement",
            "enhancement",
            "breakdown of",
            "explanation:",
            "notes:",
            "topic sentence:",
            "supporting evidence:",
            "analysis:",
            "paragraph \\d+:",
            "this section",
            "furthermore, this",
            "### Additional"
        ]
        
        content_lower = content.lower()
        found_clutter = []
        
        for indicator in clutter_indicators:
            if re.search(indicator, content_lower):
                found_clutter.append(indicator)
        
        if found_clutter:
            logger.warning(f"Potential clutter found: {found_clutter}")
            return False
        
        return True

    async def extract_bibliography_cleanly(self, content: str) -> Tuple[str, str]:
        """Extract and clean bibliography section separately"""
        
        # Find bibliography section
        bib_patterns = [
            r'## References.*?(?=\n## |\Z)',
            r'## Bibliography.*?(?=\n## |\Z)',
            r'### References.*?(?=\n## |\Z)',
            r'# References.*?(?=\n# |\Z)'
        ]
        
        bibliography = ""
        main_content = content
        
        for pattern in bib_patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                bibliography = match.group(0)
                main_content = content.replace(bibliography, "").strip()
                break
        
        # If no explicit bibliography found, extract from end of document
        if not bibliography:
            lines = content.split('\n')
            bib_start = -1
            
            # Look for reference patterns at the end
            for i in range(len(lines) - 1, max(0, len(lines) - 50), -1):
                line = lines[i].strip()
                if re.match(r'^\d+\.\s|\[\d+\]\s|^[A-Z].*\(\d{4}\)', line):
                    if bib_start == -1:
                        bib_start = i
                elif bib_start != -1 and line and not re.match(r'^\d+\.\s|\[\d+\]\s|^[A-Z].*\(\d{4}\)', line):
                    break
            
            if bib_start != -1:
                bibliography = "## References\n\n" + '\n'.join(lines[bib_start:])
                main_content = '\n'.join(lines[:bib_start]).strip()
        
        return main_content, bibliography


# Main integration function
async def enhance_report_quality_cleanly(pipe_instance, comprehensive_answer: str, user_message: str) -> str:
    """
    Main function to enhance report quality while ensuring clean output
    Returns only the final polished report with bibliography
    """
    
    logger.info("Starting clean report enhancement")
    
    # Initialize clean enhancer
    enhancer = CleanReportEnhancer(pipe_instance)
    
    # Enhance report cleanly
    enhanced_report = await enhancer.enhance_report_cleanly(comprehensive_answer, user_message)
    
    # Verify output is clean
    is_clean = await enhancer.verify_clean_output(enhanced_report)
    
    if not is_clean:
        logger.warning("Output may contain clutter - applying additional cleaning")
        # Apply additional cleaning if needed
        enhanced_report = enhancer._remove_clutter_patterns(enhanced_report)
    
    # Extract and organize bibliography
    main_content, bibliography = await enhancer.extract_bibliography_cleanly(enhanced_report)
    
    # Combine into final clean report
    if bibliography and bibliography not in main_content:
        final_report = f"{main_content}\n\n{bibliography}"
    else:
        final_report = enhanced_report
    
    logger.info("Clean report enhancement complete")
    return final_report


# Alternative simple enhancement for when you want minimal processing
async def minimal_clean_enhancement(pipe_instance, comprehensive_answer: str, user_query: str) -> str:
    """
    Minimal enhancement that just cleans structure without heavy processing
    Use this when you want to avoid any risk of clutter
    """
    
    minimal_prompt = {
        "role": "system",
        "content": f"""Clean and organize this research report on: "{user_query}"

ONLY:
- Remove any process commentary or revision notes
- Organize into clear sections with proper headers
- Move references to end if not already there
- Fix obvious formatting issues
- Preserve ALL content and citations [X] exactly

Output the clean, organized report without any meta-commentary."""
    }
    
    try:
        response = await pipe_instance.generate_completion(
            pipe_instance.get_synthesis_model(),
            [minimal_prompt, {"role": "user", "content": comprehensive_answer}],
            temperature=0.1  # Very low temperature for minimal changes
        )
        
        return response["choices"][0]["message"]["content"]
        
    except Exception as e:
        logger.error(f"Error in minimal enhancement: {e}")
        return comprehensive_answer  # Return original if enhancement fails