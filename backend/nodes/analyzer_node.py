"""
Deep research analyzer for complex analytical queries requiring multi-source investigation.

This node orchestrates comprehensive research through a 4-stage pipeline:
1. Query decomposition into focused sub-questions
2. Intelligent source selection per sub-question
3. Parallel multi-source searches via existing infrastructure
4. Evidence-based synthesis with proper citation preservation

The analyzer integrates deeply with the application's multi-source architecture,
routing sub-questions through source_coordinator → reviewer → summarizer for
optimal results quality and citation management.
"""

import asyncio
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from nodes.base import (
    ChatState,
    logger,
    SystemMessage,
    ChatOpenAI,
    config,
    get_current_datetime_str,
    queue_status,
)
from nodes.source_coordinator_node import source_coordinator_node
from nodes.search_results_reviewer_node import search_results_reviewer_node
from nodes.evidence_summarizer_node import evidence_summarizer_node
from utils.helpers import get_last_user_message


# Configuration - use getattr for safer module attribute access
DEEP_ANALYSIS_MAX_SUB_QUESTIONS = getattr(
    config, "DEEP_ANALYSIS_MAX_SUB_QUESTIONS", 4
)
DEEP_ANALYSIS_TEMPERATURE = getattr(
    config, "DEEP_ANALYSIS_TEMPERATURE", 0.3
)
DEEP_ANALYSIS_SYNTHESIS_TEMPERATURE = getattr(
    config, "DEEP_ANALYSIS_SYNTHESIS_TEMPERATURE", 0.7
)


# Structured output models
class QueryDecomposition(BaseModel):
    """Structured output for query decomposition."""
    sub_questions: List[str] = Field(
        description="List of focused sub-questions for deep research"
    )
    reasoning: str = Field(
        description="Brief explanation of the decomposition strategy"
    )


class ResearchPlanItem(BaseModel):
    """Individual research plan for a sub-question."""
    sub_question: str = Field(
        description="The sub-question to research"
    )
    sources: List[str] = Field(
        description="Selected sources (e.g., search, academic_search, social_search, medical_search)"
    )
    rationale: str = Field(
        description="Brief rationale for source selection"
    )


class SubQuestionResearchPlan(BaseModel):
    """Research plan for a set of sub-questions."""
    plans: List[ResearchPlanItem] = Field(
        description="List of research plans for each sub-question"
    )


async def analyzer_node(state: ChatState) -> ChatState:
    """
    Deep research analyzer that orchestrates multi-source investigation.

    This node processes analytical queries by:
    1. Decomposing the query into focused sub-questions
    2. Selecting appropriate sources for each sub-question
    3. Executing parallel searches through the multi-source pipeline
    4. Synthesizing evidence-based responses with preserved citations

    Args:
        state: Current chat state containing query and context

    Returns:
        Updated state with comprehensive analysis results
    """
    logger.info("🧩 Deep Analyzer: Initiating comprehensive research")
    queue_status(state.get("thread_id"), "Analyzing query...")
    await asyncio.sleep(0.1)

    # Extract query to analyze
    refined_task = state.get("workflow_context", {}).get("refined_analysis_task")
    original_query = get_last_user_message(state.get("messages", []))
    task_to_analyze = refined_task or original_query

    if not task_to_analyze:
        logger.warning("🧩 Deep Analyzer: No query found")
        state["module_results"]["analyzer"] = {
            "success": False,
            "error": "No query found for deep research"
        }
        return state

    display_task = (
        task_to_analyze[:75] + "..."
        if len(task_to_analyze) > 75
        else task_to_analyze
    )
    logger.info(f'🧩 Deep Analyzer: Researching: "{display_task}"')

    try:
        # Stage 1: Decompose query into sub-questions
        queue_status(state.get("thread_id"), "Breaking down research question...")
        sub_questions = await _decompose_query(state, task_to_analyze)
        logger.info(
            f"🧩 Deep Analyzer: Decomposed into {len(sub_questions)} sub-questions"
        )

        # Stage 2: Plan research sources for each sub-question
        queue_status(state.get("thread_id"), "Planning research sources...")
        research_plans = await _plan_research_sources(
            state, task_to_analyze, sub_questions
        )
        logger.info(
            f"🧩 Deep Analyzer: Created {len(research_plans)} research plans"
        )

        # Stage 3: Execute research plans through multi-source pipeline
        queue_status(state.get("thread_id"), "Gathering evidence...")
        evidence_bundles = await _execute_research_plans(state, research_plans)
        logger.info(
            f"🧩 Deep Analyzer: Collected {len(evidence_bundles)} evidence bundles"
        )

        # Check if we have any evidence to synthesize
        if not evidence_bundles:
            logger.warning(
                "🧩 Deep Analyzer: No evidence collected from any sub-question. "
                "Unable to conduct deep research."
            )
            state["module_results"]["analyzer"] = {
                "success": False,
                "error": "No evidence sources available",
                "task_processed": task_to_analyze,
                "sub_questions": sub_questions,
                "research_plans_count": len(research_plans),
                "evidence_bundles_count": 0
            }
            return state

        # Stage 4: Synthesize comprehensive response
        queue_status(state.get("thread_id"), "Synthesizing findings...")
        analysis_response = await _synthesize_findings(
            state, task_to_analyze, sub_questions, evidence_bundles
        )

        display_result = (
            analysis_response[:75] + "..."
            if len(analysis_response) > 75
            else analysis_response
        )
        logger.info(f'🧩 Deep Analyzer: ✅ Completed: "{display_result}"')

        # Aggregate all citations and search sources from evidence bundles
        all_citations = []
        all_search_sources = []
        for bundle in evidence_bundles:
            if bundle.get("citations"):
                all_citations.extend(bundle["citations"])
            if bundle.get("search_sources"):
                all_search_sources.extend(bundle["search_sources"])

        # Store results with citations for integrator to process
        state["module_results"]["analyzer"] = {
            "success": True,
            "result": analysis_response,
            "task_processed": task_to_analyze,
            "sub_questions": sub_questions,
            "research_plans_count": len(research_plans),
            "evidence_bundles_count": len(evidence_bundles),
            "citations": all_citations,
            "search_results": all_search_sources
        }

        logger.info(
            f"🧩 Deep Analyzer: 📚 Collected {len(all_citations)} total citations "
            f"from {len(evidence_bundles)} evidence bundles"
        )

    except Exception as e:
        logger.error(
            f"🧩 Deep Analyzer: Research failed: {str(e)}",
            exc_info=True
        )
        state["module_results"]["analyzer"] = {
            "success": False,
            "error": f"Deep research error: {str(e)}",
            "task_processed": task_to_analyze
        }

    return state


async def _decompose_query(
    state: ChatState,
    query: str
) -> List[str]:
    """
    Decompose complex query into focused sub-questions.

    Uses structured output to ensure reliable JSON parsing and adapts
    decomposition strategy based on query type and conversation context.
    """
    current_time = get_current_datetime_str()

    # Include memory context for continuity
    memory_context = state.get("memory_context", "")
    memory_section = ""
    if memory_context:
        memory_section = f"\n\nCONVERSATION CONTEXT:\n{memory_context}\n"
        logger.debug("🧩 Deep Analyzer: Including memory context in decomposition")

    prompt = f"""Current date and time: {current_time}

You are an expert research strategist who decomposes queries into focused sub-questions.
{memory_section}
QUERY TO RESEARCH:
{query}

Break this into {DEEP_ANALYSIS_MAX_SUB_QUESTIONS} focused sub-questions for deep investigation.

DECOMPOSITION PRINCIPLES:
1. Adapt to query type - factual, analytical, comparative, etc.
2. Each sub-question should be specific and independently researchable
3. Follow natural logical flow needed to answer the main query
4. Balance depth with breadth - cover key aspects without redundancy
5. Keep sub-questions clear and actionable

Your decomposition should enable comprehensive understanding of the topic."""

    llm = ChatOpenAI(
        model=config.DEFAULT_MODEL,
        temperature=DEEP_ANALYSIS_TEMPERATURE,
        max_tokens=500,
        api_key=config.OPENAI_API_KEY
    )

    try:
        structured_llm = llm.with_structured_output(QueryDecomposition)
        response = await structured_llm.ainvoke([SystemMessage(content=prompt)])

        reasoning_preview = (
            response.reasoning[:100] + "..."
            if len(response.reasoning) > 100
            else response.reasoning
        )
        logger.info(f"🧩 Deep Analyzer: Decomposition reasoning: {reasoning_preview}")

        return response.sub_questions[:DEEP_ANALYSIS_MAX_SUB_QUESTIONS]

    except Exception as e:
        logger.warning(
            f"🧩 Deep Analyzer: Decomposition failed: {str(e)}, using original query"
        )
        # Fallback to original query
        return [query]


async def _plan_research_sources(
    state: ChatState,
    original_query: str,
    sub_questions: List[str]
) -> List[Dict[str, Any]]:
    """
    Plan research sources for each sub-question.

    Uses the multi_source_analyzer logic to intelligently select sources
    (web, academic, social, medical) based on sub-question characteristics.
    """
    current_time = get_current_datetime_str()

    sub_q_text = "\n".join([f"{i+1}. {q}" for i, q in enumerate(sub_questions)])

    prompt = f"""Current date and time: {current_time}

You are a research coordinator planning multi-source investigation.

ORIGINAL QUERY:
{original_query}

SUB-QUESTIONS TO RESEARCH:
{sub_q_text}

For each sub-question, select the most appropriate sources (1-2 sources max per question).

AVAILABLE SOURCES:
- search: Web search for current info, news, trends
- academic_search: Scholarly papers, research publications
- social_search: Community discussions, experiences (Hacker News)
- medical_search: Medical literature, health research

SOURCE SELECTION GUIDELINES:
- Academic topics → academic_search + search
- Medical/health → medical_search + academic_search
- Tech/opinions → search + social_search
- Current events → search only
- General research → search + academic_search

Provide a research plan for EACH sub-question with selected sources and brief rationale.

Return format: Array of objects with sub_question, sources (array), and rationale (string)."""

    llm = ChatOpenAI(
        model=config.ROUTER_MODEL,
        temperature=0.2,
        max_tokens=800,
        api_key=config.OPENAI_API_KEY
    )

    try:
        structured_llm = llm.with_structured_output(SubQuestionResearchPlan)
        response = await structured_llm.ainvoke([SystemMessage(content=prompt)])

        # Validate and clean plans
        validated_plans = []
        valid_sources = ["search", "academic_search", "social_search", "medical_search"]

        for plan in response.plans:
            # Ensure sources are valid
            sources = [s for s in plan.sources if s in valid_sources]
            if not sources:
                sources = ["search"]  # Fallback

            # Limit to 2 sources per sub-question
            sources = sources[:2]

            validated_plans.append({
                "sub_question": plan.sub_question,
                "sources": sources,
                "rationale": plan.rationale
            })

        logger.info(
            f"🧩 Deep Analyzer: Created {len(validated_plans)} validated research plans"
        )
        return validated_plans

    except Exception as e:
        logger.warning(
            f"🧩 Deep Analyzer: Research planning failed: {str(e)}, using fallback"
        )
        # Fallback: use search for all sub-questions
        return [
            {
                "sub_question": q,
                "sources": ["search"],
                "rationale": "Fallback to web search"
            }
            for q in sub_questions
        ]


async def _execute_research_plans(
    state: ChatState,
    research_plans: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Execute research plans through the multi-source pipeline in parallel.

    For each sub-question, this routes through:
    1. source_coordinator_node - parallel multi-source execution
    2. search_results_reviewer_node - relevance filtering
    3. evidence_summarizer_node - citation-aware summarization

    All sub-questions are researched concurrently for optimal performance.

    Returns evidence bundles with properly formatted, citation-preserved summaries.
    """

    async def _research_single_plan(plan: Dict[str, Any], index: int) -> Optional[Dict[str, Any]]:
        """Research a single sub-question through the pipeline."""
        sub_question = plan["sub_question"]
        sources = plan["sources"]

        logger.info(
            f"🧩 Deep Analyzer: [{index}/{len(research_plans)}] Researching: "
            f"{sub_question[:50]}... (sources: {sources})"
        )

        # Update status for user visibility
        queue_status(
            state.get("thread_id"),
            f"Researching {index}/{len(research_plans)}: {sub_question[:40]}..."
        )

        try:
            # Create isolated state for this sub-question
            # Use dict() for safer state construction
            sub_state = dict(
                messages=state.get("messages", []),
                model=state.get("model", config.DEFAULT_MODEL),
                temperature=state.get("temperature", 0.7),
                max_tokens=state.get("max_tokens", 2000),
                personality=state.get("personality"),
                current_module="search",
                module_results={},
                workflow_context={
                    "refined_search_query": sub_question,
                    "original_research_query": sub_question
                },
                user_id=state.get("user_id"),
                routing_analysis=state.get("routing_analysis"),
                thread_id=state.get("thread_id"),
                memory_context=state.get("memory_context"),
                intent="search",
                selected_sources=sources
            )

            # Execute multi-source pipeline
            sub_state = await source_coordinator_node(sub_state)
            sub_state = await search_results_reviewer_node(sub_state)
            sub_state = await evidence_summarizer_node(sub_state)

            # Extract evidence from successful sources
            # Handle both specialized sources (with evidence_summary) and Perplexity (with result)
            evidence_pieces = []
            all_citations = []
            all_search_sources = []

            for source_key in sources:
                source_result = sub_state["module_results"].get(source_key, {})
                if source_result.get("success"):
                    # Try evidence_summary first (specialized sources after summarizer)
                    evidence_content = source_result.get("evidence_summary")

                    # Fallback to result field (Perplexity search)
                    if not evidence_content:
                        evidence_content = source_result.get("result")

                    if evidence_content:
                        evidence_pieces.append({
                            "source": source_key,
                            "summary": evidence_content,
                            "source_name": _get_source_display_name(source_key)
                        })

                        # Collect citations and search sources for this evidence
                        citations = source_result.get("citations", [])
                        search_sources = source_result.get("search_results", [])

                        if citations:
                            all_citations.extend(citations)
                        if search_sources:
                            all_search_sources.extend(search_sources)

            if evidence_pieces:
                logger.info(
                    f"🧩 Deep Analyzer: ✅ [{index}] Collected {len(evidence_pieces)} evidence pieces "
                    f"with {len(all_citations)} citations"
                )
                return {
                    "sub_question": sub_question,
                    "evidence": evidence_pieces,
                    "sources_used": sources,
                    "citations": all_citations,
                    "search_sources": all_search_sources
                }
            else:
                logger.warning(
                    f"🧩 Deep Analyzer: ⚠️ [{index}] No evidence collected"
                )
                return None

        except Exception as e:
            logger.error(
                f"🧩 Deep Analyzer: ❌ [{index}] Research failed: {str(e)}"
            )
            return None

    # Execute all research plans in parallel
    logger.info(
        f"🧩 Deep Analyzer: Executing {len(research_plans)} research plans in parallel"
    )

    tasks = [
        _research_single_plan(plan, i)
        for i, plan in enumerate(research_plans, 1)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out None results and exceptions
    evidence_bundles = []
    for i, result in enumerate(results, 1):
        if isinstance(result, Exception):
            logger.error(
                f"🧩 Deep Analyzer: ❌ Sub-question {i} raised exception: {result}"
            )
        elif result is not None:
            evidence_bundles.append(result)

    logger.info(
        f"🧩 Deep Analyzer: ✅ Collected {len(evidence_bundles)} evidence bundles "
        f"from {len(research_plans)} sub-questions"
    )

    return evidence_bundles


async def _synthesize_findings(
    state: ChatState,
    original_query: str,
    sub_questions: List[str],
    evidence_bundles: List[Dict[str, Any]]
) -> str:
    """
    Synthesize evidence into comprehensive analytical response.

    Creates natural, flowing response that:
    - Directly addresses the original query
    - Integrates evidence from all sources
    - Preserves all citation markers exactly
    - Adapts tone and structure to query type
    """
    # Safety check - should never happen due to earlier validation
    if not evidence_bundles:
        logger.error("🧩 Deep Analyzer: _synthesize_findings called with empty evidence")
        return (
            f"Unable to provide deep analysis for: {original_query}\n\n"
            "No evidence sources were available for this query."
        )

    current_time = get_current_datetime_str()

    # Build evidence context
    evidence_text = ""
    for i, bundle in enumerate(evidence_bundles, 1):
        evidence_text += f"\n### Research for: {bundle['sub_question']}\n"
        evidence_text += f"Sources: {', '.join(bundle['sources_used'])}\n\n"

        for piece in bundle["evidence"]:
            evidence_text += f"**{piece['source_name']}:**\n"
            evidence_text += f"{piece['summary']}\n\n"

    # Include memory context
    memory_context = state.get("memory_context", "")
    memory_section = ""
    if memory_context:
        memory_section = f"\n\nCONVERSATION CONTEXT:\n{memory_context}\n"

    sub_q_text = "\n".join([f"{i+1}. {q}" for i, q in enumerate(sub_questions)])

    prompt = f"""Current date and time: {current_time}
{memory_section}
You are an expert research synthesizer creating comprehensive, evidence-based responses.

ORIGINAL QUERY:
{original_query}

SUB-QUESTIONS RESEARCHED:
{sub_q_text}

RESEARCH EVIDENCE (with citation markers):
{evidence_text}

Synthesize this research into a thorough response that directly addresses the original query.

SYNTHESIS GUIDELINES:
1. Start with a concise summary (2-3 sentences) answering the main question
2. Follow with detailed explanation that flows naturally from the evidence
3. Adapt structure to the query - avoid rigid formatting unless needed
4. Present information in a conversational, accessible way
5. When sources differ, acknowledge multiple perspectives objectively
6. Note any limitations in the evidence when appropriate

CRITICAL - CITATION PRESERVATION:
The evidence contains citation markers like [1], [2], [3] that reference specific sources.
**YOU MUST preserve these markers EXACTLY as they appear.**
When referencing information from evidence, copy the citation markers with it.
Do NOT remove, modify, or create new citation markers.

Example:
Evidence: "Recent studies show X[1][2] and Y[3]"
Your synthesis: "Research indicates X[1][2], which relates to Y[3]"

Your response should feel like a thorough, well-researched explanation that a knowledgeable colleague would provide, complete with proper citations."""

    llm = ChatOpenAI(
        model=config.DEFAULT_MODEL,
        temperature=DEEP_ANALYSIS_SYNTHESIS_TEMPERATURE,
        max_tokens=2000,
        api_key=config.OPENAI_API_KEY
    )

    try:
        response = await llm.ainvoke([SystemMessage(content=prompt)])
        return response.content

    except Exception as e:
        logger.error(f"🧩 Deep Analyzer: Synthesis failed: {str(e)}")
        return (
            f"Deep analysis of: {original_query}\n\n"
            f"Unable to complete synthesis due to error: {str(e)}"
        )


def _get_source_display_name(source_key: str) -> str:
    """Get human-readable source name."""
    source_names = {
        "search": "Web Search",
        "academic_search": "Academic Papers",
        "social_search": "Hacker News Discussions",
        "medical_search": "Medical Literature"
    }
    return source_names.get(source_key, source_key)
