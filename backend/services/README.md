# Services

This directory contains business logic and services that are used by the API endpoints. It helps to separate concerns and keeps the API layer thin.

## Key Services

### `motivation.py` - Per-Topic Motivation System
Intelligent per-topic motivation system for autonomous research scheduling:

**Per-Topic Motivation**:
- `update_scores()` - Updates motivation scores for all active topics
- `check_for_research_needed()` - Identifies topics that need research
- Factors: staleness pressure, user engagement, research success rate
- Staleness coefficients: LLM-assessed values (0.1=stable, 2.0=urgent)
- Research loop owned by Motivation module

**Integration**:
- Uses PersonalizationManager for user engagement data
- Configurable via environment variables (see CLAUDE.md)
- Called by autonomous_research_engine for intelligent topic selection

### `autonomous_research_engine.py` - Research Orchestration
LangGraph-based autonomous research engine that uses the motivation system to intelligently schedule background research on user topics. 