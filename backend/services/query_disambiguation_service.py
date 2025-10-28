import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from nodes.base import (
    logger, 
    config, 
    get_current_datetime_str,
    ChatOpenAI,
    SystemMessage,
    HumanMessage,
    QUERY_DISAMBIGUATION_SYSTEM_PROMPT
)
from models import (
    QueryDisambiguationAnalysis,
    ClarifyingQuestion,
    QueryRefinement
)
from utils import get_last_user_message


class QueryDisambiguationService:
    """Service for analyzing query vagueness and generating clarifying questions using LLM."""
    
    def __init__(self):
        pass
    
    async def analyze_query(self, query: str, context: Dict[str, Any]) -> QueryDisambiguationAnalysis:
        """
        Analyze a query to determine if it needs disambiguation using LLM.
        
        Args:
            query: The user query to analyze
            context: Conversation context and user information
            
        Returns:
            QueryDisambiguationAnalysis with vagueness assessment
        """
        logger.info(f"🔍 Query Disambiguation: Analyzing query: '{query[:50]}...'")
        
        try:
            # Use LLM-based analysis
            analysis = await self._llm_analyze_query(query, context)
            
            logger.info(f"🔍 Query Disambiguation: LLM analysis complete - vague: {analysis.is_vague}, confidence: {analysis.confidence_score:.2f}")
            return analysis
            
        except Exception as e:
            logger.error(f"🔍 Query Disambiguation: Error in LLM analysis: {str(e)}")
            # Return safe fallback without rule-based analysis
            return QueryDisambiguationAnalysis(
                is_vague=False,
                confidence_score=0.0,
                vague_indicators=[],
                clarifying_questions=[],
                suggested_refinements=[],
                context_analysis=f"LLM analysis failed: {str(e)}"
            )
    
    async def _llm_analyze_query(self, query: str, context: Dict[str, Any]) -> QueryDisambiguationAnalysis:
        """
        Use LLM to analyze query vagueness and generate intelligent clarifying questions.
        """
        logger.info("🔍 Query Disambiguation: Using LLM for analysis")
        
        try:
            # Initialize LLM
            llm = ChatOpenAI(
                model=config.ROUTER_MODEL,  # Use router model for cost efficiency
                temperature=0.1,  # Low temperature for consistent analysis
                max_tokens=500,
                api_key=config.OPENAI_API_KEY
            )
            
            # Prepare conversation context
            conversation_context = self._build_conversation_context(context)
            memory_context = context.get("memory_context", "")
            
            # Create system prompt
            system_prompt = QUERY_DISAMBIGUATION_SYSTEM_PROMPT.format(
                current_time=get_current_datetime_str(),
                memory_context_section=f"CONVERSATION MEMORY:\n{memory_context}\n\n" if memory_context else ""
            )
            
            # Create messages for LLM
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"QUERY TO ANALYZE: {query}\n\nCONVERSATION CONTEXT:\n{conversation_context}")
            ]
            
            # Get LLM response
            response = await llm.ainvoke(messages)
            llm_response = response.content
            
            # Parse LLM response into structured analysis
            analysis = self._parse_llm_response(llm_response, query, context)
            
            logger.info(f"🔍 Query Disambiguation: LLM analysis - vague: {analysis.is_vague}, confidence: {analysis.confidence_score:.2f}")
            return analysis
            
        except Exception as e:
            logger.error(f"🔍 Query Disambiguation: LLM analysis failed: {str(e)}")
            raise e
    
    def _build_conversation_context(self, context: Dict[str, Any]) -> str:
        """Build conversation context string for LLM."""
        messages = context.get("messages", [])
        
        if not messages:
            return "No previous conversation context."
        
        # Get last 3 messages for context
        recent_messages = messages[-3:] if len(messages) > 3 else messages
        context_lines = []
        
        for msg in recent_messages:
            if hasattr(msg, 'content'):
                role = "User" if hasattr(msg, 'role') and msg.role == "user" else "Assistant"
                context_lines.append(f"{role}: {msg.content}")
        
        return "\n".join(context_lines) if context_lines else "No recent conversation context."
    
    def _parse_llm_response(self, llm_response: str, query: str, context: Dict[str, Any]) -> QueryDisambiguationAnalysis:
        """Parse LLM response into structured QueryDisambiguationAnalysis."""
        try:
            # Extract structured information from LLM response
            lines = llm_response.strip().split('\n')
            
            # Initialize default values
            is_vague = False
            confidence_score = 0.0
            vague_indicators = []
            clarifying_questions = []
            suggested_refinements = []
            context_analysis = ""
            
            # Parse the response (this is a simplified parser - you could make it more sophisticated)
            current_section = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Detect sections
                if "VAGUE:" in line.upper() or "IS_VAGUE:" in line.upper():
                    is_vague = "true" in line.lower() or "yes" in line.lower()
                elif "CONFIDENCE:" in line.upper():
                    try:
                        confidence_score = float(line.split(":")[1].strip())
                    except:
                        confidence_score = 0.5 if is_vague else 0.0
                elif "INDICATORS:" in line.upper():
                    current_section = "indicators"
                elif "QUESTIONS:" in line.upper():
                    current_section = "questions"
                elif "SUGGESTIONS:" in line.upper():
                    current_section = "suggestions"
                elif "CONTEXT:" in line.upper():
                    current_section = "context"
                elif line.startswith("-") or line.startswith("•"):
                    # List item
                    item = line[1:].strip()
                    if current_section == "indicators":
                        vague_indicators.append(item)
                    elif current_section == "questions":
                        clarifying_questions.append(ClarifyingQuestion(
                            question=item,
                            question_type="open_ended",
                            context="Generated by LLM"
                        ))
                    elif current_section == "suggestions":
                        suggested_refinements.append(item)
                elif current_section == "context":
                    context_analysis += line + " "
            
            # If LLM didn't provide structured output, use intelligent defaults
            if not vague_indicators and is_vague:
                vague_indicators = ["LLM detected vagueness"]
            
            if not clarifying_questions and is_vague:
                clarifying_questions = [ClarifyingQuestion(
                    question="Could you provide more specific details about what you're looking for?",
                    question_type="open_ended",
                    context="LLM-generated clarification request"
                )]
            
            if not suggested_refinements:
                suggested_refinements = [f"{query} with more specific details"]
            
            return QueryDisambiguationAnalysis(
                is_vague=is_vague,
                confidence_score=confidence_score,
                vague_indicators=vague_indicators,
                clarifying_questions=clarifying_questions,
                suggested_refinements=suggested_refinements,
                context_analysis=context_analysis.strip() or "LLM analysis completed"
            )
            
        except Exception as e:
            logger.error(f"🔍 Query Disambiguation: Error parsing LLM response: {str(e)}")
            # Return safe fallback
            return QueryDisambiguationAnalysis(
                is_vague=False,
                confidence_score=0.0,
                vague_indicators=[],
                clarifying_questions=[],
                suggested_refinements=[],
                context_analysis=f"Error parsing LLM response: {str(e)}"
            )
    
    
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
