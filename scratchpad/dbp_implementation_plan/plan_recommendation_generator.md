# Recommendation Generator Implementation Plan

## Overview

This document outlines the implementation plan for the Recommendation Generator component, which is responsible for generating actionable recommendations based on consistency analysis results in the Documentation-Based Programming system.

## Documentation Context

This implementation is based on the following documentation:
- [DESIGN.md](../../doc/DESIGN.md) - Recommendation System section
- [DOCUMENT_RELATIONSHIPS.md](../../doc/DOCUMENT_RELATIONSHIPS.md) - Documentation relationship specifications
- [design/MCP_SERVER_ENHANCED_DATA_MODEL.md](../../doc/design/MCP_SERVER_ENHANCED_DATA_MODEL.md) - Data models
- [design/INTERNAL_LLM_TOOLS.md](../../doc/design/INTERNAL_LLM_TOOLS.md) - LLM integration for recommendations

## Requirements

The Recommendation Generator component must:
1. Generate actionable recommendations based on detected inconsistencies
2. Prioritize recommendations based on severity and impact
3. Group related recommendations for efficient resolution
4. Provide example code and documentation snippets for resolving issues
5. Track recommendation status and effectiveness
6. Support both automated and manual recommendation acceptance/rejection
7. Learn from user feedback to improve future recommendations
8. Integrate with the Consistency Analysis component
9. Provide recommendations in various formats (CLI, MCP, etc.)

## Design

### Recommendation Generator Architecture

The Recommendation Generator component follows a multi-stage architecture:

```
┌─────────────────────┐      ┌─────────────────────┐      ┌─────────────────────┐
│                     │      │                     │      │                     │
│  Recommendation     │─────▶│  Strategy           │─────▶│  Generator          │
│    Manager          │      │    Selector         │      │    Engine           │
│                     │      │                     │      │                     │
└─────────────────────┘      └─────────────────────┘      └─────────────────────┘
                                       │                            │
                                       │                            ▼
                                       │                  ┌─────────────────────┐
                                       │                  │                     │
                                       ▼                  │  LLM                │
                               ┌─────────────────────┐    │    Integration      │
                               │                     │    │                     │
                               │  Recommendation     │    └─────────────────────┘
                               │    Repository       │               │
                               │                     │               │
                               └─────────────────────┘               ▼
                                       │                  ┌─────────────────────┐
                                       │                  │                     │
                                       ▼                  │  Formatting         │
                               ┌─────────────────────┐    │    Engine           │
                               │                     │    │                     │
                               │  Feedback           │    └─────────────────────┘
                               │    Analyzer         │
                               │                     │
                               └─────────────────────┘
```

### Core Classes and Interfaces

1. **RecommendationGeneratorComponent**

```python
class RecommendationGeneratorComponent(Component):
    """Component for generating recommendations."""
    
    @property
    def name(self) -> str:
        return "recommendation_generator"
    
    @property
    def dependencies(self) -> list[str]:
        return ["database", "consistency_analysis", "llm_coordinator"]
    
    def initialize(self, context: InitializationContext) -> None:
        """Initialize the recommendation generator component."""
        self.config = context.config.recommendation_generator
        self.logger = context.logger.get_child("recommendation_generator")
        
        # Get dependencies
        self.db_component = context.get_component("database")
        self.consistency_component = context.get_component("consistency_analysis")
        self.llm_component = context.get_component("llm_coordinator")
        
        # Create recommendation subcomponents
        self.recommendation_repository = RecommendationRepository(self.db_component, self.logger)
        self.strategy_selector = StrategySelector(self.config, self.logger)
        self.generator_engine = GeneratorEngine(self.logger)
        self.llm_integration = LLMIntegration(self.llm_component, self.logger)
        self.formatting_engine = FormattingEngine(self.logger)
        self.feedback_analyzer = FeedbackAnalyzer(self.logger)
        
        # Register recommendation strategies
        self._register_strategies()
        
        self._initialized = True
    
    def _register_strategies(self) -> None:
        """Register recommendation strategies."""
        # Documentation strategies
        self.strategy_selector.register_strategy(
            "doc_link_fix",
            DocumentationLinkFixStrategy(self.llm_integration, self.logger)
        )
        
        self.strategy_selector.register_strategy(
            "doc_terminology",
            DocumentationTerminologyStrategy(self.llm_integration, self.logger)
        )
        
        self.strategy_selector.register_strategy(
            "doc_content_update",
            DocumentationContentUpdateStrategy(self.llm_integration, self.logger)
        )
        
        # Code strategies
        self.strategy_selector.register_strategy(
            "code_comment_update",
            CodeCommentUpdateStrategy(self.llm_integration, self.logger)
        )
        
        self.strategy_selector.register_strategy(
            "code_header_fix",
            CodeHeaderFixStrategy(self.llm_integration, self.logger)
        )
        
        # Combined strategies
        self.strategy_selector.register_strategy(
            "function_signature_fix",
            FunctionSignatureFixStrategy(self.llm_integration, self.logger)
        )
        
        self.strategy_selector.register_strategy(
            "class_structure_fix",
            ClassStructureFixStrategy(self.llm_integration, self.logger)
        )
    
    def generate_recommendations(self, inconsistency_ids: List[str]) -> List[Recommendation]:
        """
        Generate recommendations for inconsistencies.
        
        Args:
            inconsistency_ids: List of inconsistency IDs
            
        Returns:
            List of recommendations
        """
        if not self._initialized:
            raise ComponentNotInitializedError(self.name)
        
        self.logger.info(f"Generating recommendations for {len(inconsistency_ids)} inconsistencies")
        
        # Get inconsistencies from consistency component
        inconsistencies = [
            self.consistency_component.inconsistency_repository.get(id)
            for id in inconsistency_ids
        ]
        
        # Filter out any None values (inconsistencies that weren't found)
        inconsistencies = [i for i in inconsistencies if i is not None]
        
        # Group inconsistencies by type
        grouped_inconsistencies = self._group_inconsistencies(inconsistencies)
        
        # Generate recommendations for each group
        recommendations = []
        for group_type, group_inconsistencies in grouped_inconsistencies.items():
            self.logger.info(f"Generating recommendations for {len(group_inconsistencies)} {group_type} inconsistencies")
            
            # Select appropriate strategy
            strategy = self.strategy_selector.select_strategy(group_type)
            
            if not strategy:
                self.logger.warning(f"No strategy found for inconsistency type: {group_type}")
                continue
            
            # Generate recommendations using strategy
            group_recommendations = strategy.generate(group_inconsistencies)
            
            # Add to overall recommendations
            recommendations.extend(group_recommendations)
            
            self.logger.info(f"Generated {len(group_recommendations)} recommendations for {group_type}")
        
        # Store recommendations
        for recommendation in recommendations:
            self.recommendation_repository.save(recommendation)
        
        self.logger.info(f"Generated a total of {len(recommendations)} recommendations")
        
        return recommendations
    
    def _group_inconsistencies(self, inconsistencies: List[InconsistencyRecord]) -> Dict[str, List[InconsistencyRecord]]:
        """
        Group inconsistencies by type.
        
        Args:
            inconsistencies: List of inconsistency records
            
        Returns:
            Dictionary mapping inconsistency types to lists of records
        """
        grouped = {}
        
        for inconsistency in inconsistencies:
            inconsistency_type = inconsistency.inconsistency_type.value
            if inconsistency_type not in grouped:
                grouped[inconsistency_type] = []
            grouped[inconsistency_type].append(inconsistency)
        
        return grouped
    
    def format_recommendations(self, recommendations: List[Recommendation], format_type: str = "markdown") -> str:
        """
        Format recommendations for display.
        
        Args:
            recommendations: List of recommendations
            format_type: Format type (markdown, plain, html, json)
            
        Returns:
            Formatted recommendations
        """
        if not self._initialized:
            raise ComponentNotInitializedError(self.name)
        
        self.logger.info(f"Formatting {len(recommendations)} recommendations as {format_type}")
        
        return self.formatting_engine.format(recommendations, format_type)
    
    def apply_recommendation(self, recommendation_id: str) -> bool:
        """
        Apply a recommendation automatically.
        
        Args:
            recommendation_id: Recommendation ID
            
        Returns:
            True if the recommendation was applied successfully
        """
        if not self._initialized:
            raise ComponentNotInitializedError(self.name)
        
        self.logger.info(f"Applying recommendation: {recommendation_id}")
        
        # Get recommendation
        recommendation = self.recommendation_repository.get(recommendation_id)
        
        if not recommendation:
            raise RecommendationNotFoundError(f"Recommendation {recommendation_id} not found")
        
        # Get strategy
        strategy = self.strategy_selector.select_strategy_by_name(recommendation.strategy_name)
        
        if not strategy:
            raise StrategyNotFoundError(f"Strategy {recommendation.strategy_name} not found")
        
        # Apply recommendation
        try:
            applied = strategy.apply(recommendation)
            
            if applied:
                # Update recommendation status
                recommendation.status = RecommendationStatus.APPLIED
                recommendation.applied_at = datetime.now()
                self.recommendation_repository.update(recommendation)
                
                self.logger.info(f"Successfully applied recommendation: {recommendation_id}")
                
                # Update associated inconsistencies
                for inconsistency_id in recommendation.inconsistency_ids:
                    try:
                        self.consistency_component.mark_inconsistency_resolved(inconsistency_id)
                    except Exception as e:
                        self.logger.warning(f"Error marking inconsistency {inconsistency_id} as resolved: {e}")
            
            return applied
        
        except Exception as e:
            self.logger.error(f"Error applying recommendation {recommendation_id}: {e}")
            
            # Update recommendation status
            recommendation.status = RecommendationStatus.FAILED
            recommendation.metadata["error"] = str(e)
            self.recommendation_repository.update(recommendation)
            
            return False
    
    def provide_feedback(self, recommendation_id: str, feedback: RecommendationFeedback) -> None:
        """
        Provide feedback on a recommendation.
        
        Args:
            recommendation_id: Recommendation ID
            feedback: Recommendation feedback
        """
        if not self._initialized:
            raise ComponentNotInitializedError(self.name)
        
        self.logger.info(f"Providing feedback for recommendation: {recommendation_id}")
        
        # Get recommendation
        recommendation = self.recommendation_repository.get(recommendation_id)
        
        if not recommendation:
            raise RecommendationNotFoundError(f"Recommendation {recommendation_id} not found")
        
        # Update recommendation with feedback
        recommendation.feedback = feedback
        
        # Update status based on feedback
        if feedback.accepted:
            recommendation.status = RecommendationStatus.ACCEPTED
        else:
            recommendation.status = RecommendationStatus.REJECTED
        
        # Save updated recommendation
        self.recommendation_repository.update(recommendation)
        
        # Analyze feedback to improve future recommendations
        self.feedback_analyzer.analyze(recommendation)
    
    def get_recommendations(self,
                          inconsistency_id: Optional[str] = None,
                          status: Optional[str] = None,
                          limit: int = 100) -> List[Recommendation]:
        """
        Get recommendations from the repository.
        
        Args:
            inconsistency_id: Optional inconsistency ID filter
            status: Optional status filter
            limit: Maximum number of recommendations to return
            
        Returns:
            List of recommendations
        """
        if not self._initialized:
            raise ComponentNotInitializedError(self.name)
        
        return self.recommendation_repository.get_recommendations(
            inconsistency_id=inconsistency_id,
            status=status,
            limit=limit
        )
    
    def shutdown(self) -> None:
        """Shutdown the component gracefully."""
        self.logger.info("Shutting down recommendation generator component")
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized
```

2. **RecommendationRepository**

```python
class RecommendationRepository:
    """Repository for recommendations."""
    
    def __init__(self, db_component: Component, logger: Logger):
        self.db_component = db_component
        self.logger = logger
    
    def save(self, recommendation: Recommendation) -> str:
        """
        Save a recommendation.
        
        Args:
            recommendation: Recommendation
            
        Returns:
            Recommendation ID
        """
        session = self.db_component.get_session()
        
        try:
            with session.begin():
                # Convert recommendation to ORM model
                recommendation_orm = RecommendationORM(
                    title=recommendation.title,
                    description=recommendation.description,
                    strategy_name=recommendation.strategy_name,
                    fix_type=recommendation.fix_type.value,
                    severity=recommendation.severity.value,
                    status=recommendation.status.value,
                    source_file=recommendation.source_file,
                    target_file=recommendation.target_file,
                    inconsistency_ids=json.dumps(recommendation.inconsistency_ids),
                    code_snippet=recommendation.code_snippet,
                    doc_snippet=recommendation.doc_snippet,
                    created_at=recommendation.created_at or datetime.now(),
                    updated_at=recommendation.updated_at or datetime.now(),
                    applied_at=recommendation.applied_at,
                    metadata=json.dumps(recommendation.metadata) if recommendation.metadata else None,
                    feedback=json.dumps(recommendation.feedback.to_dict()) if recommendation.feedback else None
                )
                
                session.add(recommendation_orm)
                session.flush()
                
                recommendation_id = str(recommendation_orm.id)
                
                # Update the ID in the recommendation object
                recommendation.id = recommendation_id
                
                self.logger.debug(f"Saved recommendation: {recommendation_id}")
                
                return recommendation_id
        
        except Exception as e:
            self.logger.error(f"Error saving recommendation: {e}")
            raise RepositoryError(f"Error saving recommendation: {e}")
    
    def update(self, recommendation: Recommendation) -> None:
        """
        Update a recommendation.
        
        Args:
            recommendation: Recommendation
        """
        if not recommendation.id:
            raise ValueError("Recommendation ID is required for update")
        
        session = self.db_component.get_session()
        
        try:
            with session.begin():
                # Get existing recommendation
                recommendation_orm = session.query(RecommendationORM).filter(
                    RecommendationORM.id == recommendation.id
                ).first()
                
                if not recommendation_orm:
                    raise RepositoryError(f"Recommendation {recommendation.id} not found")
                
                # Update fields
                recommendation_orm.title = recommendation.title
                recommendation_orm.description = recommendation.description
                recommendation_orm.strategy_name = recommendation.strategy_name
                recommendation_orm.fix_type = recommendation.fix_type.value
                recommendation_orm.severity = recommendation.severity.value
                recommendation_orm.status = recommendation.status.value
                recommendation_orm.source_file = recommendation.source_file
                recommendation_orm.target_file = recommendation.target_file
                recommendation_orm.inconsistency_ids = json.dumps(recommendation.inconsistency_ids)
                recommendation_orm.code_snippet = recommendation.code_snippet
                recommendation_orm.doc_snippet = recommendation.doc_snippet
                recommendation_orm.updated_at = datetime.now()
                recommendation_orm.applied_at = recommendation.applied_at
                recommendation_orm.metadata = json.dumps(recommendation.metadata) if recommendation.metadata else None
                recommendation_orm.feedback = json.dumps(recommendation.feedback.to_dict()) if recommendation.feedback else None
                
                self.logger.debug(f"Updated recommendation: {recommendation.id}")
        
        except Exception as e:
            self.logger.error(f"Error updating recommendation: {e}")
            raise RepositoryError(f"Error updating recommendation: {e}")
    
    def get(self, recommendation_id: str) -> Optional[Recommendation]:
        """
        Get a recommendation by ID.
        
        Args:
            recommendation_id: Recommendation ID
            
        Returns:
            Recommendation or None if not found
        """
        session = self.db_component.get_session()
        
        try:
            with session.begin():
                # Get recommendation
                recommendation_orm = session.query(RecommendationORM).filter(
                    RecommendationORM.id == recommendation_id
                ).first()
                
                if not recommendation_orm:
                    return None
                
                # Convert ORM model to recommendation
                return self._convert_orm_to_recommendation(recommendation_orm)
        
        except Exception as e:
            self.logger.error(f"Error getting recommendation {recommendation_id}: {e}")
            raise RepositoryError(f"Error getting recommendation: {e}")
    
    def get_recommendations(self,
                          inconsistency_id: Optional[str] = None,
                          status: Optional[str] = None,
                          limit: int = 100) -> List[Recommendation]:
        """
        Get recommendations with filtering.
        
        Args:
            inconsistency_id: Optional inconsistency ID filter
            status: Optional status filter
            limit: Maximum number of recommendations to return
            
        Returns:
            List of recommendations
        """
        session = self.db_component.get_session()
        
        try:
            with session.begin():
                # Build query
                query = session.query(RecommendationORM)
                
                # Apply filters
                if inconsistency_id:
                    # This requires parsing the JSON array in the database
                    # The exact implementation depends on the database being used
                    # For SQLite, this might involve using JSON functions if available, or a LIKE query
                    # For PostgreSQL, use the JSON operators
                    if isinstance(self.db_component, SQLiteDatabase):
                        query = query.filter(
                            RecommendationORM.inconsistency_ids.like(f'%"{inconsistency_id}"%')
                        )
                    else:  # Assume PostgreSQL or similar with JSON operators
                        query = query.filter(
                            RecommendationORM.inconsistency_ids.op('->')(inconsistency_id).isnot(None)
                        )
                
                if status:
                    query = query.filter(RecommendationORM.status == status)
                
                # Apply order by and limit
                query = query.order_by(
                    RecommendationORM.severity.desc(),
                    RecommendationORM.created_at.desc()
                ).limit(limit)
                
                # Execute query
                recommendation_orms = query.all()
                
                # Convert ORM models to recommendations
                return [self._convert_orm_to_recommendation(orm) for orm in recommendation_orms]
        
        except Exception as e:
            self.logger.error(f"Error getting recommendations: {e}")
            raise RepositoryError(f"Error getting recommendations: {e}")
    
    def delete(self, recommendation_id: str) -> None:
        """
        Delete a recommendation.
        
        Args:
            recommendation_id: Recommendation ID
        """
        session = self.db_component.get_session()
        
        try:
            with session.begin():
                # Delete recommendation
                result = session.query(RecommendationORM).filter(
                    RecommendationORM.id == recommendation_id
                ).delete()
                
                if result == 0:
                    self.logger.warning(f"Recommendation {recommendation_id} not found for deletion")
                else:
                    self.logger.debug(f"Deleted recommendation: {recommendation_id}")
        
        except Exception as e:
            self.logger.error(f"Error deleting recommendation {recommendation_id}: {e}")
            raise RepositoryError(f"Error deleting recommendation: {e}")
    
    def _convert_orm_to_recommendation(self, orm: RecommendationORM) -> Recommendation:
        """Convert ORM model to recommendation."""
        feedback = None
        if orm.feedback:
            feedback_dict = json.loads(orm.feedback)
            feedback = RecommendationFeedback(
                accepted=feedback_dict.get("accepted", False),
                reason=feedback_dict.get("reason"),
                improvements=feedback_dict.get("improvements"),
                provided_at=datetime.fromisoformat(feedback_dict.get("provided_at")) if feedback_dict.get("provided_at") else None
            )
        
        return Recommendation(
            id=str(orm.id),
            title=orm.title,
            description=orm.description,
            strategy_name=orm.strategy_name,
            fix_type=RecommendationFixType(orm.fix_type),
            severity=RecommendationSeverity(orm.severity),
            status=RecommendationStatus(orm.status),
            source_file=orm.source_file,
            target_file=orm.target_file,
            inconsistency_ids=json.loads(orm.inconsistency_ids),
            code_snippet=orm.code_snippet,
            doc_snippet=orm.doc_snippet,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            applied_at=orm.applied_at,
            metadata=json.loads(orm.metadata) if orm.metadata else {},
            feedback=feedback
        )
```

3. **StrategySelector**

```python
class StrategySelector:
    """Selector for recommendation strategies."""
    
    def __init__(self, config: RecommendationGeneratorConfig, logger: Logger):
        self.config = config
        self.logger = logger
        self._strategies = {}  # type: Dict[str, RecommendationStrategy]
        self._type_to_strategy = {
            # Inconsistency type to strategy mapping
            "intent_mismatch": "doc_content_update",
            "missing_constraints": "doc_content_update",
            "design_principles_mismatch": "doc_content_update",
            "missing_reference_docs": "doc_content_update",
            "broken_reference": "doc_link_fix",
            "missing_bidirectional_reference": "doc_link_fix",
            "circular_reference": "doc_link_fix",
            "terminology_inconsistency": "doc_terminology",
            "config_parameter_inconsistency": "doc_content_update",
            "api_documentation_inconsistency": "doc_content_update",
            "function_signature_mismatch": "function_signature_fix",
            "class_structure_mismatch": "class_structure_fix"
        }
    
    def register_strategy(self, strategy_name: str, strategy: RecommendationStrategy) -> None:
        """
        Register a recommendation strategy.
        
        Args:
            strategy_name: Strategy name
            strategy: Strategy instance
        """
        self.logger.info(f"Registering recommendation strategy: {strategy_name}")
        self._strategies[strategy_name] = strategy
    
    def select_strategy(self, inconsistency_type: str) -> Optional[RecommendationStrategy]:
        """
        Select a strategy for an inconsistency type.
        
        Args:
            inconsistency_type: Inconsistency type
            
        Returns:
            Strategy or None if no matching strategy is found
        """
        strategy_name = self._type_to_strategy.get(inconsistency_type)
        
        if not strategy_name:
            self.logger.warning(f"No strategy mapping for inconsistency type: {inconsistency_type}")
            return None
        
        strategy = self._strategies.get(strategy_name)
        
        if not strategy:
            self.logger.warning(f"Strategy not found: {strategy_name}")
            return None
        
        return strategy
    
    def select_strategy_by_name(self, strategy_name: str) -> Optional[RecommendationStrategy]:
        """
        Select a strategy by name.
        
        Args:
            strategy_name: Strategy name
            
        Returns:
            Strategy or None if not found
        """
        return self._strategies.get(strategy_name)
    
    def get_all_strategies(self) -> Dict[str, RecommendationStrategy]:
        """
        Get all registered strategies.
        
        Returns:
            Dictionary of strategy names to strategies
        """
        return self._strategies.copy()
```

4. **GeneratorEngine**

```python
class GeneratorEngine:
    """Engine for generating recommendations."""
    
    def __init__(self, logger: Logger):
        self.logger = logger
    
    def generate(self, 
                strategy: RecommendationStrategy, 
                inconsistencies: List[InconsistencyRecord]) -> List[Recommendation]:
        """
        Generate recommendations using a strategy.
        
        Args:
            strategy: Recommendation strategy
            inconsistencies: List of inconsistency records
            
        Returns:
            List of recommendations
        """
        self.logger.info(f"Generating recommendations using strategy: {strategy.__class__.__name__}")
        
        try:
            # Apply strategy
            return strategy.generate(inconsistencies)
        
        except Exception as e:
            self.logger.error(f"Error generating recommendations: {e}")
            return []
```

5. **LLMIntegration**

```python
class LLMIntegration:
    """Integration with LLM for recommendation generation."""
    
    def __init__(self, llm_component: Component, logger: Logger):
        self.llm_component = llm_component
        self.logger = logger
    
    def generate_fix(self, 
                    inconsistency: InconsistencyRecord, 
                    fix_type: str) -> Dict[str, Any]:
        """
        Generate a fix recommendation using LLM.
        
        Args:
            inconsistency: Inconsistency record
            fix_type: Type of fix to generate
            
        Returns:
            Dictionary with fix details
        """
        self.logger.info(f"Generating {fix_type} fix for inconsistency {inconsistency.id}")
        
        # Prepare prompt for LLM
        prompt = self._build_prompt(inconsistency, fix_type)
        
        # Submit job to LLM coordinator
        job_id = self.llm_component.submit_job(
            JobSpecification(
                type="llm_internal_tool",
                payload={
                    "tool_name": "generate_recommendation",
                    "parameters": {
                        "inconsistency_id": inconsistency.id,
                        "fix_type": fix_type,
                        "prompt": prompt
                    }
                },
                priority=5  # Medium priority
            )
        )
        
        # Wait for job completion
        result = None
        max_wait = 30  # seconds
        wait_interval = 0.5  # seconds
        waited = 0
        
        while waited < max_wait:
            job_status = self.llm_component.get_job_status(job_id)
            
            if job_status == JobStatus.COMPLETED:
                result = self.llm_component.get_job_result(job_id)
                break
            
            if job_status in [JobStatus.FAILED, JobStatus.CANCELLED]:
                self.logger.error(f"LLM job {job_id} failed or was cancelled")
                break
            
            time.sleep(wait_interval)
            waited += wait_interval
        
        if not result:
            self.logger.error(f"Timed out waiting for LLM job {job_id}")
            return {"error": "Timed out waiting for LLM response"}
        
        # Process LLM response
        try:
            return result.result
        except Exception as e:
            self.logger.error(f"Error processing LLM response: {e}")
            return {"error": f"Error processing LLM response: {e}"}
    
    def _build_prompt(self, inconsistency: InconsistencyRecord, fix_type: str) -> str:
        """Build a prompt for the LLM."""
        
        # Get source and target file content
        source_content = self._get_file_content(inconsistency.source_file)
        target_content = self._get_file_content(inconsistency.target_file)
        
        # Build prompt based on inconsistency type and fix type
        prompt = [
            "You are an expert system helping resolve inconsistencies between documentation and code.",
            f"Inconsistency Type: {inconsistency.inconsistency_type.value}",
            f"Description: {inconsistency.description}",
            f"Source File: {inconsistency.source_file}",
            f"Target File: {inconsistency.target_file}",
            f"Fix Type: {fix_type}",
            "\nSource File Content:",
            "```",
            source_content[:5000] if source_content else "File content not available",
            "```",
            "\nTarget File Content:",
            "```",
            target_content[:5000] if target_content else "File content not available",
            "```",
            "\nInconsistency Details:",
            json.dumps(inconsistency.details, indent=2),
            "\nTask: Generate a recommendation to fix this inconsistency. Include:",
            "1. A clear title for the recommendation",
            "2. A detailed description of what needs to be fixed",
            "3. Precise code and/or documentation snippets showing exactly what to change",
            "4. Any additional context or considerations",
            "\nFormat your response as a JSON object with the following fields:",
            "- title: string",
            "- description: string",
            "- code_snippet: string (if applicable)",
            "- doc_snippet: string (if applicable)",
            "- metadata: object with any additional information"
        ]
        
        return "\n".join(prompt)
    
    def _get_file_content(self, file_path: str) -> Optional[str]:
        """Get the content of a file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"Error reading file {file_path}: {e}")
            return None
```

6. **FormattingEngine**

```python
class FormattingEngine:
    """Engine for formatting recommendations."""
    
    def __init__(self, logger: Logger):
        self.logger = logger
    
    def format(self, recommendations: List[Recommendation], format_type: str = "markdown") -> str:
        """
        Format recommendations for display.
        
        Args:
            recommendations: List of recommendations
            format_type: Format type (markdown, plain, html, json)
            
        Returns:
            Formatted recommendations
        """
        if not recommendations:
            return "No recommendations available."
        
        if format_type == "json":
            return self._format_as_json(recommendations)
        elif format_type == "html":
            return self._format_as_html(recommendations)
        elif format_type == "plain":
            return self._format_as_plain(recommendations)
        else:  # Default to markdown
            return self._format_as_markdown(recommendations)
    
    def _format_as_markdown(self, recommendations: List[Recommendation]) -> str:
        """Format recommendations as markdown."""
        sections = [
            "# Recommendations",
            f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"\nTotal recommendations: {len(recommendations)}"
        ]
        
        # Group by severity
        by_severity = {}
        for r in recommendations:
            severity = r.severity.value
            if severity not in by_severity:
                by_severity[severity] = []
            by_severity[severity].append(r)
        
        # Add sections for each severity
        for severity in ["high", "medium", "low"]:
            if severity in by_severity:
                severity_recs = by_severity[severity]
                sections.append(f"\n## {severity.title()} Severity ({len(severity_recs)})")
                
                # Add each recommendation
                for i, r in enumerate(severity_recs, 1):
                    sections.append(f"\n### {i}. {r.title}")
                    sections.append(f"\nID: `{r.id}`")
                    sections.append(f"\nStatus: {r.status.value.title()}")
                    sections.append(f"\n{r.description}")
                    
                    # Add code snippet if available
                    if r.code_snippet:
                        sections.append("\n#### Code Snippet")
                        sections.append("```python")
                        sections.append(r.code_snippet)
                        sections.append("```")
                    
                    # Add doc snippet if available
                    if r.doc_snippet:
                        sections.append("\n#### Documentation Snippet")
                        sections.append("```markdown")
                        sections.append(r.doc_snippet)
                        sections.append("```")
                    
                    sections.append("\n---")
        
        return "\n".join(sections)
    
    def _format_as_plain(self, recommendations: List[Recommendation]) -> str:
        """Format recommendations as plain text."""
        sections = [
            "RECOMMENDATIONS",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total recommendations: {len(recommendations)}",
            ""
        ]
        
        # Add each recommendation
        for i, r in enumerate(recommendations, 1):
            sections.append(f"{i}. {r.title} [{r.severity.value.upper()}]")
            sections.append(f"   Status: {r.status.value}")
            sections.append(f"   {r.description}")
            
            # Add code snippet if available
            if r.code_snippet:
                sections.append("   CODE SNIPPET:")
                sections.append("   " + r.code_snippet.replace("\n", "\n   "))
            
            # Add doc snippet if available
            if r.doc_snippet:
                sections.append("   DOCUMENTATION SNIPPET:")
                sections.append("   " + r.doc_snippet.replace("\n", "\n   "))
            
            sections.append("")
        
        return "\n".join(sections)
    
    def _format_as_html(self, recommendations: List[Recommendation]) -> str:
        """Format recommendations as HTML."""
        # Simple HTML implementation for demonstration
        # Would be expanded for production use
        html = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "  <title>Recommendations</title>",
            "  <style>",
            "    body { font-family: Arial, sans-serif; margin: 20px; }",
            "    .high { background-color: #ffdddd; }",
            "    .medium { background-color: #ffffdd; }",
            "    .low { background-color: #ddffdd; }",
            "    pre { background-color: #f4f4f4; padding: 10px; border-radius: 5px; }",
            "  </style>",
            "</head>",
            "<body>",
            "  <h1>Recommendations</h1>",
            f"  <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>",
            f"  <p>Total recommendations: {len(recommendations)}</p>"
        ]
        
        # Add each recommendation
        for i, r in enumerate(recommendations, 1):
            html.append(f"  <div class=\"{r.severity.value}\">")
            html.append(f"    <h2>{i}. {r.title}</h2>")
            html.append(f"    <p>ID: <code>{r.id}</code></p>")
            html.append(f"    <p>Status: {r.status.value.title()}</p>")
            html.append(f"    <p>{r.description}</p>")
            
            # Add code snippet if available
            if r.code_snippet:
                html.append("    <h3>Code Snippet</h3>")
                html.append("    <pre>")
                html.append(html_escape(r.code_snippet))
                html.append("    </pre>")
            
            # Add doc snippet if available
            if r.doc_snippet:
                html.append("    <h3>Documentation Snippet</h3>")
                html.append("    <pre>")
                html.append(html_escape(r.doc_snippet))
                html.append("    </pre>")
            
            html.append("  </div>")
            html.append("  <hr>")
        
        html.append("</body>")
        html.append("</html>")
        
        return "\n".join(html)
    
    def _format_as_json(self, recommendations: List[Recommendation]) -> str:
        """Format recommendations as JSON."""
        result = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "count": len(recommendations)
            },
            "recommendations": []
        }
        
        for r in recommendations:
            rec = {
                "id": r.id,
                "title": r.title,
                "description": r.description,
                "strategy_name": r.strategy_name,
                "fix_type": r.fix_type.value,
                "severity": r.severity.value,
                "status": r.status.value,
                "source_file": r.source_file,
                "target_file": r.target_file,
                "inconsistency_ids": r.inconsistency_ids,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                "applied_at": r.applied_at.isoformat() if r.applied_at else None,
            }
            
            # Add snippets if available
            if r.code_snippet:
                rec["code_snippet"] = r.code_snippet
            
            if r.doc_snippet:
                rec["doc_snippet"] = r.doc_snippet
            
            # Add feedback if available
            if r.feedback:
                rec["feedback"] = {
                    "accepted": r.feedback.accepted,
                    "reason": r.feedback.reason,
                    "improvements": r.feedback.improvements,
                    "provided_at": r.feedback.provided_at.isoformat() if r.feedback.provided_at else None
                }
            
            result["recommendations"].append(rec)
        
        return json.dumps(result, indent=2)

def html_escape(text: str) -> str:
    """Escape special characters for HTML."""
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#39;"))
```

7. **FeedbackAnalyzer**

```python
class FeedbackAnalyzer:
    """Analyzer for recommendation feedback."""
    
    def __init__(self, logger: Logger):
        self.logger = logger
        self._feedback_stats = {}  # type: Dict[str, Dict[str, Any]]
    
    def analyze(self, recommendation: Recommendation) -> None:
        """
        Analyze feedback for a recommendation.
        
        Args:
            recommendation: Recommendation with feedback
        """
        if not recommendation.feedback:
            return
        
        strategy_name = recommendation.strategy_name
        feedback = recommendation.feedback
        
        # Initialize stats for this strategy if needed
        if strategy_name not in self._feedback_stats:
            self._feedback_stats[strategy_name] = {
                "total": 0,
                "accepted": 0,
                "rejected": 0,
                "acceptance_rate": 0.0,
                "common_reasons": {},
                "common_improvements": {}
            }
        
        # Update stats
        stats = self._feedback_stats[strategy_name]
        stats["total"] += 1
        
        if feedback.accepted:
            stats["accepted"] += 1
        else:
            stats["rejected"] += 1
        
        # Update acceptance rate
        stats["acceptance_rate"] = stats["accepted"] / stats["total"]
        
        # Track common reasons for rejection
        if not feedback.accepted and feedback.reason:
            reason = feedback.reason.lower()
            if reason not in stats["common_reasons"]:
                stats["common_reasons"][reason] = 0
            stats["common_reasons"][reason] += 1
        
        # Track common improvement suggestions
        if feedback.improvements:
            for improvement in feedback.improvements:
                improvement_key = improvement.lower()
                if improvement_key not in stats["common_improvements"]:
                    stats["common_improvements"][improvement_key] = 0
                stats["common_improvements"][improvement_key] += 1
        
        self.logger.info(f"Analyzed feedback for strategy {strategy_name}, new acceptance rate: {stats['acceptance_rate']:.2f}")
    
    def get_feedback_stats(self, strategy_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get feedback statistics.
        
        Args:
            strategy_name: Optional strategy name to filter by
            
        Returns:
            Dictionary with feedback statistics
        """
        if strategy_name:
            return self._feedback_stats.get(strategy_name, {})
        
        return self._feedback_stats
```

8. **RecommendationStrategy (Interface)**

```python
class RecommendationStrategy(ABC):
    """Base class for recommendation strategies."""
    
    def __init__(self, llm_integration: LLMIntegration, logger: Logger):
        self.llm_integration = llm_integration
        self.logger = logger
    
    @abstractmethod
    def generate(self, inconsistencies: List[InconsistencyRecord]) -> List[Recommendation]:
        """
        Generate recommendations for inconsistencies.
        
        Args:
            inconsistencies: List of inconsistency records
            
        Returns:
            List of recommendations
        """
        pass
    
    @abstractmethod
    def apply(self, recommendation: Recommendation) -> bool:
        """
        Apply a recommendation.
        
        Args:
            recommendation: Recommendation to apply
            
        Returns:
            True if the recommendation was applied successfully
        """
        pass
```

9. **Example Strategy Implementation**

```python
class DocumentationLinkFixStrategy(RecommendationStrategy):
    """Strategy for fixing broken documentation links."""
    
    def generate(self, inconsistencies: List[InconsistencyRecord]) -> List[Recommendation]:
        """Generate recommendations for broken links."""
        recommendations = []
        
        for inconsistency in inconsistencies:
            self.logger.info(f"Generating link fix recommendation for {inconsistency.id}")
            
            try:
                # Use LLM to generate fix
                llm_result = self.llm_integration.generate_fix(inconsistency, "doc_link_fix")
                
                if "error" in llm_result:
                    self.logger.error(f"Error generating fix: {llm_result['error']}")
                    continue
                
                # Create recommendation from LLM result
                recommendation = Recommendation(
                    id=None,  # Will be assigned when saved
                    title=llm_result.get("title", "Fix broken documentation link"),
                    description=llm_result.get("description", "Update the broken link in the documentation"),
                    strategy_name="doc_link_fix",
                    fix_type=RecommendationFixType.DOCUMENTATION,
                    severity=self._map_severity(inconsistency.severity),
                    status=RecommendationStatus.PENDING,
                    source_file=inconsistency.source_file,
                    target_file=inconsistency.target_file,
                    inconsistency_ids=[inconsistency.id],
                    code_snippet=None,
                    doc_snippet=llm_result.get("doc_snippet"),
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    applied_at=None,
                    metadata={},
                    feedback=None
                )
                
                recommendations.append(recommendation)
                
            except Exception as e:
                self.logger.error(f"Error generating recommendation for {inconsistency.id}: {e}")
        
        return recommendations
    
    def apply(self, recommendation: Recommendation) -> bool:
        """Apply a link fix recommendation."""
        self.logger.info(f"Applying link fix recommendation {recommendation.id}")
        
        try:
            # Get file content
            with open(recommendation.source_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Extract old and new links from doc snippet
            # This is a simplified implementation; in practice would use more sophisticated parsing
            doc_snippet = recommendation.doc_snippet
            if not doc_snippet:
                self.logger.error("Missing doc snippet in recommendation")
                return False
            
            # Parse doc snippet to find old and new links
            # Assumes format like:
            # - Old link: [text](old_path)
            # - New link: [text](new_path)
            old_link_match = re.search(r"Old link: \[(.*?)\]\((.*?)\)", doc_snippet)
            new_link_match = re.search(r"New link: \[(.*?)\]\((.*?)\)", doc_snippet)
            
            if not old_link_match or not new_link_match:
                self.logger.error("Could not parse old and new links from doc snippet")
                return False
            
            old_text = old_link_match.group(1)
            old_path = old_link_match.group(2)
            new_text = new_link_match.group(1)
            new_path = new_link_match.group(2)
            
            # Create regex patterns to match the old link (with escaped special chars)
            old_link_pattern = re.escape(f"[{old_text}]({old_path})")
            new_link = f"[{new_text}]({new_path})"
            
            # Replace the link
            new_content = re.sub(old_link_pattern, new_link, content)
            
            if new_content == content:
                self.logger.warning(f"No changes made to {recommendation.source_file}")
                return False
            
            # Write the updated content
            with open(recommendation.source_file, "w", encoding="utf-8") as f:
                f.write(new_content)
            
            self.logger.info(f"Successfully updated link in {recommendation.source_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error applying recommendation {recommendation.id}: {e}")
            return False
    
    def _map_severity(self, inconsistency_severity: InconsistencySeverity) -> RecommendationSeverity:
        """Map inconsistency severity to recommendation severity."""
        if inconsistency_severity == InconsistencySeverity.HIGH:
            return RecommendationSeverity.HIGH
        elif inconsistency_severity == InconsistencySeverity.MEDIUM:
            return RecommendationSeverity.MEDIUM
        else:
            return RecommendationSeverity.LOW
```

### Data Model Classes

1. **RecommendationFixType**

```python
class RecommendationFixType(Enum):
    """Types of recommendation fixes."""
    
    DOCUMENTATION = "documentation"
    CODE = "code"
    COMBINED = "combined"
```

2. **RecommendationSeverity**

```python
class RecommendationSeverity(Enum):
    """Severity levels for recommendations."""
    
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
```

3. **RecommendationStatus**

```python
class RecommendationStatus(Enum):
    """Status values for recommendations."""
    
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    APPLIED = "applied"
    FAILED = "failed"
```

4. **RecommendationFeedback**

```python
@dataclass
class RecommendationFeedback:
    """Feedback on a recommendation."""
    
    accepted: bool
    reason: Optional[str] = None
    improvements: Optional[List[str]] = None
    provided_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "accepted": self.accepted,
            "reason": self.reason,
            "improvements": self.improvements,
            "provided_at": self.provided_at.isoformat() if self.provided_at else None
        }
```

5. **Recommendation**

```python
@dataclass
class Recommendation:
    """Recommendation for fixing inconsistencies."""
    
    title: str
    description: str
    strategy_name: str
    fix_type: RecommendationFixType
    severity: RecommendationSeverity
    status: RecommendationStatus
    source_file: str
    target_file: str
    inconsistency_ids: List[str]
    code_snippet: Optional[str]
    doc_snippet: Optional[str]
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]
    id: Optional[str] = None
    applied_at: Optional[datetime] = None
    feedback: Optional[RecommendationFeedback] = None
```

6. **RecommendationORM**

```python
class RecommendationORM(Base):
    """ORM model for recommendations."""
    
    __tablename__ = "recommendations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    strategy_name = Column(String, nullable=False)
    fix_type = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    status = Column(String, nullable=False)
    source_file = Column(String, nullable=False)
    target_file = Column(String, nullable=False)
    inconsistency_ids = Column(Text, nullable=False)  # JSON array as text
    code_snippet = Column(Text, nullable=True)
    doc_snippet = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    applied_at = Column(DateTime, nullable=True)
    metadata = Column(Text, nullable=True)
    feedback = Column(Text, nullable=True)
```

### Configuration Class

```python
@dataclass
class RecommendationGeneratorConfig:
    """Configuration for recommendation generator."""
    
    enabled_strategies: List[str]
    llm_timeout_seconds: int
    auto_apply_recommendations: bool
    max_recommendations_per_batch: int
```

Default configuration values:

| Parameter | Description | Default | Valid Values |
|-----------|-------------|---------|-------------|
| `enabled_strategies` | List of enabled strategies | All strategies | List of strategy names |
| `llm_timeout_seconds` | Timeout for LLM operations | `30` | `5-300` |
| `auto_apply_recommendations` | Whether to automatically apply recommendations | `False` | `True/False` |
| `max_recommendations_per_batch` | Maximum recommendations per batch | `50` | `10-1000` |

## Implementation Plan

### Phase 1: Core Structure
1. Implement RecommendationGeneratorComponent as a system component
2. Define data model classes (Recommendation, RecommendationStatus, etc.)
3. Create configuration class
4. Implement ORM model for recommendations

### Phase 2: Strategy Framework
1. Implement RecommendationStrategy interface
2. Create StrategySelector for managing strategies
3. Implement GeneratorEngine for applying strategies
4. Set up LLMIntegration for LLM-based recommendations

### Phase 3: Basic Strategies
1. Implement DocumentationLinkFixStrategy
2. Implement DocumentationContentUpdateStrategy
3. Implement CodeCommentUpdateStrategy
4. Integrate with Consistency Analysis component

### Phase 4: Advanced Features
1. Implement FormattingEngine for various output formats
2. Create FeedbackAnalyzer for learning from user feedback
3. Add functionality to filter and group recommendations
4. Implement automatic recommendation application

## Security Considerations

The Recommendation Generator component implements these security measures:
- Validation of file paths to prevent path traversal attacks
- Sanitization of LLM-generated content before application
- Safe handling of markdown and code content during recommendation application
- Proper error isolation and reporting
- User confirmation before applying recommendations by default
- Proper handling of file I/O operations
- Secure integration with LLM services

## Testing Strategy

### Unit Tests
- Test individual strategies for correctness
- Test recommendation repository operations
- Test formatting engine
- Test feedback analyzer

### Integration Tests
- Test database integration
- Test integration with LLM Coordinator component
- Test integration with Consistency Analysis component
- Test end-to-end recommendation workflow

### System Tests
- Test performance with large codebases
- Test quality of LLM-generated recommendations
- Test automatic recommendation application

## Dependencies on Other Plans

This plan depends on:
- Database Schema plan (for ORM models)
- Consistency Analysis plan (for inconsistency records)
- LLM Coordinator plan (for LLM integration)
- Component Initialization plan (for component framework)

## Implementation Timeline

1. Core Structure - 1 day
2. Strategy Framework - 2 days
3. Basic Strategies - 2 days
4. Advanced Features - 2 days

Total: 7 days
