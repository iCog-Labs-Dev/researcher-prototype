"""
Query disambiguation service for detecting vague queries and generating clarifying questions.
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from nodes.base import logger, config, get_current_datetime_str
from models import (
    QueryDisambiguationAnalysis,
    ClarifyingQuestion,
    QueryRefinement
)
from utils import get_last_user_message


class QueryDisambiguationService:
    """Service for analyzing query vagueness and generating clarifying questions."""
    
    def __init__(self):
        self.vague_query_indicators = [
            "tell me about", "help with", "what is", "explain",
            "information on", "research", "project", "help me",
            "can you", "how do i", "what should", "i need",
            "looking for", "want to know", "curious about"
        ]
        
        self.broad_topics = [
            "ai", "technology", "science", "health", "business",
            "politics", "education", "art", "music", "sports",
            "history", "philosophy", "psychology", "economics"
        ]
    
    async def analyze_query(self, query: str, context: Dict[str, Any]) -> QueryDisambiguationAnalysis:
        """
        Analyze a query to determine if it needs disambiguation.
        
        Args:
            query: The user query to analyze
            context: Conversation context and user information
            
        Returns:
            QueryDisambiguationAnalysis with vagueness assessment
        """
        logger.info(f"🔍 Query Disambiguation: Analyzing query: '{query[:50]}...'")
        
        try:
            # Basic vagueness detection
            is_vague, confidence_score, vague_indicators = self._detect_vagueness(query)
            
            # If not vague, return early
            if not is_vague:
                return QueryDisambiguationAnalysis(
                    is_vague=False,
                    confidence_score=confidence_score,
                    vague_indicators=[],
                    clarifying_questions=[],
                    suggested_refinements=[],
                    context_analysis="Query appears specific and clear"
                )
            
            # Generate clarifying questions for vague queries
            clarifying_questions = await self._generate_clarifying_questions(query, context)
            
            # Generate suggested refinements
            suggested_refinements = self._generate_suggested_refinements(query, context)
            
            # Analyze conversation context
            context_analysis = self._analyze_context(context)
            
            return QueryDisambiguationAnalysis(
                is_vague=True,
                confidence_score=confidence_score,
                vague_indicators=vague_indicators,
                clarifying_questions=clarifying_questions,
                suggested_refinements=suggested_refinements,
                context_analysis=context_analysis
            )
            
        except Exception as e:
            logger.error(f"🔍 Query Disambiguation: Error analyzing query: {str(e)}")
            # Return safe fallback
            return QueryDisambiguationAnalysis(
                is_vague=False,
                confidence_score=0.0,
                vague_indicators=[],
                clarifying_questions=[],
                suggested_refinements=[],
                context_analysis=f"Error in analysis: {str(e)}"
            )
    
    def _detect_vagueness(self, query: str) -> tuple[bool, float, List[str]]:
        """Detect if a query is vague using pattern matching and heuristics."""
        query_lower = query.lower().strip()
        vague_indicators = []
        confidence_score = 0.0
        
        # Check for vague indicator phrases
        for indicator in self.vague_query_indicators:
            if indicator in query_lower:
                vague_indicators.append(f"Contains vague phrase: '{indicator}'")
                confidence_score += 0.3
        
        # Check for broad topics without specificity
        for topic in self.broad_topics:
            if topic in query_lower and len(query.split()) < 5:
                vague_indicators.append(f"Broad topic '{topic}' without specificity")
                confidence_score += 0.2
        
        # Check query length (very short queries are often vague)
        if len(query.split()) < 3:
            vague_indicators.append("Query is very short")
            confidence_score += 0.4
        
        # Check for question words without specifics
        question_words = ["what", "how", "why", "when", "where", "who"]
        if any(word in query_lower for word in question_words) and len(query.split()) < 4:
            vague_indicators.append("Question word without specific context")
            confidence_score += 0.3
        
        # Normalize confidence score
        confidence_score = min(confidence_score, 1.0)
        is_vague = confidence_score >= 0.5
        
        return is_vague, confidence_score, vague_indicators
    
    async def _generate_clarifying_questions(self, query: str, context: Dict[str, Any]) -> List[ClarifyingQuestion]:
        """Generate clarifying questions using LLM assistance."""
        try:
            # For now, use rule-based generation
            # TODO: Implement LLM-based generation in next iteration
            questions = []
            
            query_lower = query.lower()
            
            # Generate questions based on query patterns
            if "help" in query_lower or "project" in query_lower:
                questions.append(ClarifyingQuestion(
                    question="What type of project or help do you need?",
                    question_type="open_ended",
                    context="Understanding the specific type of assistance needed"
                ))
            
            if any(topic in query_lower for topic in ["ai", "technology", "science"]):
                questions.append(ClarifyingQuestion(
                    question="Are you interested in:",
                    question_type="multiple_choice",
                    options=["Recent developments", "Basic concepts", "Technical details", "Applications"],
                    context="Clarifying the depth and focus of your interest"
                ))
            
            if "research" in query_lower:
                questions.append(ClarifyingQuestion(
                    question="What specific aspect would you like to research?",
                    question_type="open_ended",
                    context="Narrowing down the research focus"
                ))
            
            # Default question if no specific patterns match
            if not questions:
                questions.append(ClarifyingQuestion(
                    question="Could you provide more specific details about what you're looking for?",
                    question_type="open_ended",
                    context="General clarification request"
                ))
            
            return questions
            
        except Exception as e:
            logger.error(f"🔍 Query Disambiguation: Error generating questions: {str(e)}")
            return [ClarifyingQuestion(
                question="Could you provide more specific details about what you're looking for?",
                question_type="open_ended",
                context="Fallback clarification request"
            )]
    
    def _generate_suggested_refinements(self, query: str, context: Dict[str, Any]) -> List[str]:
        """Generate suggested query refinements."""
        suggestions = []
        
        # Add time-based refinements
        suggestions.append(f"{query} recent developments")
        suggestions.append(f"{query} 2024")
        
        # Add specificity refinements
        if "ai" in query.lower():
            suggestions.append("artificial intelligence applications in healthcare")
            suggestions.append("machine learning algorithms for data analysis")
        
        if "research" in query.lower():
            suggestions.append("research methodology best practices")
            suggestions.append("academic research paper writing")
        
        return suggestions[:3]  # Limit to 3 suggestions
    
    def _analyze_context(self, context: Dict[str, Any]) -> str:
        """Analyze conversation context for better disambiguation."""
        messages = context.get("messages", [])
        
        if len(messages) < 2:
            return "New conversation - no previous context"
        
        # Look for recent topics in conversation
        recent_topics = []
        for msg in messages[-3:]:  # Last 3 messages
            if isinstance(msg, dict) and msg.get("role") == "user":
                content = msg.get("content", "")
                if len(content.split()) > 2:  # Non-trivial content
                    recent_topics.append(content[:50])
        
        if recent_topics:
            return f"Recent conversation topics: {', '.join(recent_topics)}"
        
        return "Limited conversation context available"
    
    async def refine_query_with_clarification(self, original_query: str, clarification: str, context: Dict[str, Any]) -> QueryRefinement:
        """
        Refine the original query using user clarification.
        
        Args:
            original_query: The original vague query
            clarification: User's clarification response
            context: Conversation context
            
        Returns:
            QueryRefinement with the improved query
        """
        logger.info(f"🔍 Query Disambiguation: Refining query with clarification")
        
        try:
            # Simple refinement logic - combine original with clarification
            refined_query = f"{original_query} {clarification}".strip()
            
            # Clean up the query
            refined_query = self._clean_query(refined_query)
            
            return QueryRefinement(
                original_query=original_query,
                refined_query=refined_query,
                refinement_type="clarification",
                confidence_score=0.8,  # High confidence in refinement
                reasoning=f"Combined original query with user clarification: '{clarification}'"
            )
            
        except Exception as e:
            logger.error(f"🔍 Query Disambiguation: Error refining query: {str(e)}")
            return QueryRefinement(
                original_query=original_query,
                refined_query=original_query,
                refinement_type="clarification",
                confidence_score=0.0,
                reasoning=f"Error in refinement: {str(e)}"
            )
    
    def _clean_query(self, query: str) -> str:
        """Clean and normalize a query."""
        # Remove extra whitespace
        query = " ".join(query.split())
        
        # Remove common filler words that don't add value
        filler_words = ["please", "can you", "could you", "i need", "i want"]
        for filler in filler_words:
            query = query.replace(filler, "").strip()
        
        return query
