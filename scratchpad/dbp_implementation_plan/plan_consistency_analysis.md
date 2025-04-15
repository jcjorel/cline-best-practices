# Consistency Analysis Implementation Plan

## Overview

This document outlines the implementation plan for the Consistency Analysis component, which is responsible for detecting inconsistencies between documentation and code, and between related documentation files in the Documentation-Based Programming system.

## Documentation Context

This implementation is based on the following documentation:
- [DESIGN.md](../../doc/DESIGN.md) - Consistency Analysis section
- [DOCUMENT_RELATIONSHIPS.md](../../doc/DOCUMENT_RELATIONSHIPS.md) - Documentation relationship specifications
- [design/MCP_SERVER_ENHANCED_DATA_MODEL.md](../../doc/design/MCP_SERVER_ENHANCED_DATA_MODEL.md) - Data models

## Requirements

The Consistency Analysis component must:
1. Detect inconsistencies between documentation files and their referenced code files
2. Identify conflicts between related documentation files
3. Validate that documentation updates are properly reflected in the code
4. Ensure that code changes are properly documented
5. Provide a detailed report of inconsistencies found
6. Integrate with the Documentation Relationships component for impact analysis
7. Support both on-demand and background consistency checks
8. Prioritize inconsistencies based on severity and impact

## Design

### Consistency Analysis Architecture

The Consistency Analysis component follows a rule-based architecture with specialized analyzers:

```
┌─────────────────────┐      ┌─────────────────────┐      ┌─────────────────────┐
│                     │      │                     │      │                     │
│  Consistency        │─────▶│  Analysis           │─────▶│  Rule               │
│    Manager          │      │    Registry         │      │    Engine           │
│                     │      │                     │      │                     │
└─────────────────────┘      └─────────────────────┘      └─────────────────────┘
                                       │                            │
                                       │                            ▼
                                       │                  ┌─────────────────────┐
                                       │                  │                     │
                                       ▼                  │  Specialized        │
                               ┌─────────────────────┐    │    Analyzers        │
                               │                     │    │                     │
                               │  Inconsistency      │    └─────────────────────┘
                               │    Repository       │               │
                               │                     │               │
                               └─────────────────────┘               ▼
                                       │                  ┌─────────────────────┐
                                       │                  │                     │
                                       ▼                  │  Report             │
                               ┌─────────────────────┐    │    Generator        │
                               │                     │    │                     │
                               │  Impact             │    └─────────────────────┘
                               │    Analyzer         │
                               │                     │
                               └─────────────────────┘
```

### Core Classes and Interfaces

1. **ConsistencyAnalysisComponent**

```python
class ConsistencyAnalysisComponent(Component):
    """Component for consistency analysis."""
    
    @property
    def name(self) -> str:
        return "consistency_analysis"
    
    @property
    def dependencies(self) -> list[str]:
        return ["database", "doc_relationships", "metadata_extraction"]
    
    def initialize(self, context: InitializationContext) -> None:
        """Initialize the consistency analysis component."""
        self.config = context.config.consistency_analysis
        self.logger = context.logger.get_child("consistency_analysis")
        self.db_component = context.get_component("database")
        self.doc_relationships_component = context.get_component("doc_relationships")
        self.metadata_extraction_component = context.get_component("metadata_extraction")
        
        # Create analysis subcomponents
        self.inconsistency_repository = InconsistencyRepository(self.db_component, self.logger)
        self.analysis_registry = AnalysisRegistry(self.logger)
        self.rule_engine = RuleEngine(self.analysis_registry, self.logger)
        self.impact_analyzer = ConsistencyImpactAnalyzer(self.doc_relationships_component, self.logger)
        self.report_generator = ReportGenerator(self.logger)
        
        # Register specialized analyzers
        self._register_analyzers()
        
        self._initialized = True
    
    def _register_analyzers(self) -> None:
        """Register specialized analyzers."""
        # Code-Doc consistency analyzers
        self.analysis_registry.register_analyzer(
            "code_doc_metadata",
            CodeDocMetadataAnalyzer(self.metadata_extraction_component, self.logger)
        )
        
        self.analysis_registry.register_analyzer(
            "function_signature_change",
            FunctionSignatureChangeAnalyzer(self.metadata_extraction_component, self.logger)
        )
        
        self.analysis_registry.register_analyzer(
            "class_structure_change",
            ClassStructureChangeAnalyzer(self.metadata_extraction_component, self.logger)
        )
        
        # Doc-Doc consistency analyzers
        self.analysis_registry.register_analyzer(
            "cross_reference_consistency",
            CrossReferenceConsistencyAnalyzer(self.doc_relationships_component, self.logger)
        )
        
        self.analysis_registry.register_analyzer(
            "terminology_consistency",
            TerminologyConsistencyAnalyzer(self.logger)
        )
        
        # Configuration consistency analyzers
        self.analysis_registry.register_analyzer(
            "config_parameter_consistency",
            ConfigParameterConsistencyAnalyzer(self.logger)
        )
        
        # API consistency analyzers
        self.analysis_registry.register_analyzer(
            "api_documentation_consistency",
            APIDocumentationConsistencyAnalyzer(self.logger)
        )
    
    def analyze_code_doc_consistency(self, code_file_path: str, doc_file_path: str) -> List[InconsistencyRecord]:
        """
        Analyze consistency between a code file and a documentation file.
        
        Args:
            code_file_path: Path to the code file
            doc_file_path: Path to the documentation file
            
        Returns:
            List of inconsistency records
        """
        if not self._initialized:
            raise ComponentNotInitializedError(self.name)
        
        self.logger.info(f"Analyzing consistency between {code_file_path} and {doc_file_path}")
        
        # Run rule engine for code-doc consistency analyzers
        inconsistencies = self.rule_engine.run_analysis(
            analysis_type="code_doc",
            inputs={
                "code_file_path": code_file_path,
                "doc_file_path": doc_file_path
            }
        )
        
        # Store inconsistencies in repository
        for inconsistency in inconsistencies:
            self.inconsistency_repository.save(inconsistency)
        
        self.logger.info(f"Found {len(inconsistencies)} inconsistencies between {code_file_path} and {doc_file_path}")
        
        return inconsistencies
    
    def analyze_doc_doc_consistency(self, doc_file_paths: List[str]) -> List[InconsistencyRecord]:
        """
        Analyze consistency between multiple documentation files.
        
        Args:
            doc_file_paths: List of documentation file paths
            
        Returns:
            List of inconsistency records
        """
        if not self._initialized:
            raise ComponentNotInitializedError(self.name)
        
        self.logger.info(f"Analyzing consistency between {len(doc_file_paths)} documentation files")
        
        # Run rule engine for doc-doc consistency analyzers
        inconsistencies = self.rule_engine.run_analysis(
            analysis_type="doc_doc",
            inputs={
                "doc_file_paths": doc_file_paths
            }
        )
        
        # Store inconsistencies in repository
        for inconsistency in inconsistencies:
            self.inconsistency_repository.save(inconsistency)
        
        self.logger.info(f"Found {len(inconsistencies)} inconsistencies between documentation files")
        
        return inconsistencies
    
    def analyze_project_consistency(self) -> List[InconsistencyRecord]:
        """
        Analyze consistency across the entire project.
        
        Returns:
            List of inconsistency records
        """
        if not self._initialized:
            raise ComponentNotInitializedError(self.name)
        
        self.logger.info("Analyzing consistency across the entire project")
        
        # Run rule engine for all analyzers
        inconsistencies = self.rule_engine.run_analysis(
            analysis_type="full_project",
            inputs={}  # The analyzers will scan the project directory
        )
        
        # Store inconsistencies in repository
        for inconsistency in inconsistencies:
            self.inconsistency_repository.save(inconsistency)
        
        self.logger.info(f"Found {len(inconsistencies)} inconsistencies across the project")
        
        return inconsistencies
    
    def get_inconsistencies(self, 
                          file_path: Optional[str] = None,
                          severity: Optional[str] = None,
                          status: Optional[str] = None,
                          limit: int = 100) -> List[InconsistencyRecord]:
        """
        Get inconsistencies from the repository.
        
        Args:
            file_path: Optional file path filter
            severity: Optional severity filter
            status: Optional status filter
            limit: Maximum number of inconsistencies to return
            
        Returns:
            List of inconsistency records
        """
        if not self._initialized:
            raise ComponentNotInitializedError(self.name)
        
        return self.inconsistency_repository.get_inconsistencies(
            file_path=file_path,
            severity=severity,
            status=status,
            limit=limit
        )
    
    def generate_report(self, inconsistencies: List[InconsistencyRecord]) -> ConsistencyReport:
        """
        Generate a consistency report from inconsistencies.
        
        Args:
            inconsistencies: List of inconsistency records
            
        Returns:
            Consistency report
        """
        if not self._initialized:
            raise ComponentNotInitializedError(self.name)
        
        self.logger.info("Generating consistency report")
        
        # Generate report
        report = self.report_generator.generate(inconsistencies)
        
        # Analyze impact of inconsistencies
        self.impact_analyzer.analyze_impact(report)
        
        return report
    
    def mark_inconsistency_resolved(self, inconsistency_id: str) -> None:
        """
        Mark an inconsistency as resolved.
        
        Args:
            inconsistency_id: Inconsistency ID
        """
        if not self._initialized:
            raise ComponentNotInitializedError(self.name)
        
        self.logger.info(f"Marking inconsistency {inconsistency_id} as resolved")
        
        # Get inconsistency
        inconsistency = self.inconsistency_repository.get(inconsistency_id)
        
        if not inconsistency:
            raise InconsistencyNotFoundError(f"Inconsistency {inconsistency_id} not found")
        
        # Update status
        inconsistency.status = InconsistencyStatus.RESOLVED
        inconsistency.resolved_at = datetime.now()
        
        # Save
        self.inconsistency_repository.update(inconsistency)
    
    def shutdown(self) -> None:
        """Shutdown the component gracefully."""
        self.logger.info("Shutting down consistency analysis component")
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized
```

2. **InconsistencyRepository**

```python
class InconsistencyRepository:
    """Repository for inconsistency records."""
    
    def __init__(self, db_component: Component, logger: Logger):
        self.db_component = db_component
        self.logger = logger
    
    def save(self, inconsistency: InconsistencyRecord) -> str:
        """
        Save an inconsistency record.
        
        Args:
            inconsistency: Inconsistency record
            
        Returns:
            Inconsistency ID
        """
        session = self.db_component.get_session()
        
        try:
            with session.begin():
                # Convert inconsistency to ORM model
                inconsistency_orm = InconsistencyORM(
                    source_file=inconsistency.source_file,
                    target_file=inconsistency.target_file,
                    inconsistency_type=inconsistency.inconsistency_type.value,
                    description=inconsistency.description,
                    details=json.dumps(inconsistency.details) if inconsistency.details else None,
                    severity=inconsistency.severity.value,
                    status=inconsistency.status.value,
                    confidence_score=inconsistency.confidence_score,
                    detected_at=inconsistency.detected_at,
                    resolved_at=inconsistency.resolved_at,
                    metadata=json.dumps(inconsistency.metadata) if inconsistency.metadata else None
                )
                
                session.add(inconsistency_orm)
                session.flush()
                
                inconsistency_id = str(inconsistency_orm.id)
                
                self.logger.debug(f"Saved inconsistency: {inconsistency_id}")
                
                return inconsistency_id
        
        except Exception as e:
            self.logger.error(f"Error saving inconsistency: {e}")
            raise RepositoryError(f"Error saving inconsistency: {e}")
    
    def update(self, inconsistency: InconsistencyRecord) -> None:
        """
        Update an inconsistency record.
        
        Args:
            inconsistency: Inconsistency record
        """
        session = self.db_component.get_session()
        
        try:
            with session.begin():
                # Get existing inconsistency
                inconsistency_orm = session.query(InconsistencyORM).filter(
                    InconsistencyORM.id == inconsistency.id
                ).first()
                
                if not inconsistency_orm:
                    raise RepositoryError(f"Inconsistency {inconsistency.id} not found")
                
                # Update fields
                inconsistency_orm.source_file = inconsistency.source_file
                inconsistency_orm.target_file = inconsistency.target_file
                inconsistency_orm.inconsistency_type = inconsistency.inconsistency_type.value
                inconsistency_orm.description = inconsistency.description
                inconsistency_orm.details = json.dumps(inconsistency.details) if inconsistency.details else None
                inconsistency_orm.severity = inconsistency.severity.value
                inconsistency_orm.status = inconsistency.status.value
                inconsistency_orm.confidence_score = inconsistency.confidence_score
                inconsistency_orm.detected_at = inconsistency.detected_at
                inconsistency_orm.resolved_at = inconsistency.resolved_at
                inconsistency_orm.metadata = json.dumps(inconsistency.metadata) if inconsistency.metadata else None
                
                self.logger.debug(f"Updated inconsistency: {inconsistency.id}")
        
        except Exception as e:
            self.logger.error(f"Error updating inconsistency: {e}")
            raise RepositoryError(f"Error updating inconsistency: {e}")
    
    def get(self, inconsistency_id: str) -> Optional[InconsistencyRecord]:
        """
        Get an inconsistency record by ID.
        
        Args:
            inconsistency_id: Inconsistency ID
            
        Returns:
            Inconsistency record or None if not found
        """
        session = self.db_component.get_session()
        
        try:
            with session.begin():
                # Get inconsistency
                inconsistency_orm = session.query(InconsistencyORM).filter(
                    InconsistencyORM.id == inconsistency_id
                ).first()
                
                if not inconsistency_orm:
                    return None
                
                # Convert ORM model to inconsistency record
                return self._convert_orm_to_inconsistency(inconsistency_orm)
        
        except Exception as e:
            self.logger.error(f"Error getting inconsistency {inconsistency_id}: {e}")
            raise RepositoryError(f"Error getting inconsistency: {e}")
    
    def get_inconsistencies(self, 
                          file_path: Optional[str] = None,
                          severity: Optional[str] = None,
                          status: Optional[str] = None,
                          limit: int = 100) -> List[InconsistencyRecord]:
        """
        Get inconsistency records with filtering.
        
        Args:
            file_path: Optional file path filter
            severity: Optional severity filter
            status: Optional status filter
            limit: Maximum number of inconsistencies to return
            
        Returns:
            List of inconsistency records
        """
        session = self.db_component.get_session()
        
        try:
            with session.begin():
                # Build query
                query = session.query(InconsistencyORM)
                
                # Apply filters
                if file_path:
                    query = query.filter(
                        sqlalchemy.or_(
                            InconsistencyORM.source_file == file_path,
                            InconsistencyORM.target_file == file_path
                        )
                    )
                
                if severity:
                    query = query.filter(InconsistencyORM.severity == severity)
                
                if status:
                    query = query.filter(InconsistencyORM.status == status)
                
                # Apply order by and limit
                query = query.order_by(
                    InconsistencyORM.severity.desc(),
                    InconsistencyORM.detected_at.desc()
                ).limit(limit)
                
                # Execute query
                inconsistency_orms = query.all()
                
                # Convert ORM models to inconsistency records
                return [self._convert_orm_to_inconsistency(orm) for orm in inconsistency_orms]
        
        except Exception as e:
            self.logger.error(f"Error getting inconsistencies: {e}")
            raise RepositoryError(f"Error getting inconsistencies: {e}")
    
    def delete(self, inconsistency_id: str) -> None:
        """
        Delete an inconsistency record.
        
        Args:
            inconsistency_id: Inconsistency ID
        """
        session = self.db_component.get_session()
        
        try:
            with session.begin():
                # Delete inconsistency
                result = session.query(InconsistencyORM).filter(
                    InconsistencyORM.id == inconsistency_id
                ).delete()
                
                if result == 0:
                    self.logger.warning(f"Inconsistency {inconsistency_id} not found for deletion")
                else:
                    self.logger.debug(f"Deleted inconsistency: {inconsistency_id}")
        
        except Exception as e:
            self.logger.error(f"Error deleting inconsistency {inconsistency_id}: {e}")
            raise RepositoryError(f"Error deleting inconsistency: {e}")
    
    def _convert_orm_to_inconsistency(self, orm: InconsistencyORM) -> InconsistencyRecord:
        """Convert ORM model to inconsistency record."""
        return InconsistencyRecord(
            id=str(orm.id),
            source_file=orm.source_file,
            target_file=orm.target_file,
            inconsistency_type=InconsistencyType(orm.inconsistency_type),
            description=orm.description,
            details=json.loads(orm.details) if orm.details else {},
            severity=InconsistencySeverity(orm.severity),
            status=InconsistencyStatus(orm.status),
            confidence_score=orm.confidence_score,
            detected_at=orm.detected_at,
            resolved_at=orm.resolved_at,
            metadata=json.loads(orm.metadata) if orm.metadata else {}
        )
```

3. **AnalysisRegistry**

```python
class AnalysisRegistry:
    """Registry for consistency analyzers."""
    
    def __init__(self, logger: Logger):
        self.logger = logger
        self._analyzers = {}
        self._rules = defaultdict(list)
    
    def register_analyzer(self, analyzer_id: str, analyzer: ConsistencyAnalyzer) -> None:
        """
        Register a consistency analyzer.
        
        Args:
            analyzer_id: Analyzer ID
            analyzer: Consistency analyzer instance
        """
        self.logger.info(f"Registering consistency analyzer: {analyzer_id}")
        self._analyzers[analyzer_id] = analyzer
        
        # Extract rules from analyzer
        for rule in analyzer.get_rules():
            self._rules[rule.analysis_type].append((analyzer, rule))
    
    def get_analyzer(self, analyzer_id: str) -> ConsistencyAnalyzer:
        """
        Get a consistency analyzer by ID.
        
        Args:
            analyzer_id: Analyzer ID
            
        Returns:
            Consistency analyzer
            
        Raises:
            AnalysisError: If analyzer not found
        """
        if analyzer_id not in self._analyzers:
            raise AnalysisError(f"Analyzer not found: {analyzer_id}")
        
        return self._analyzers[analyzer_id]
    
    def get_rules_for_analysis_type(self, analysis_type: str) -> List[Tuple[ConsistencyAnalyzer, ConsistencyRule]]:
        """
        Get rules for a specific analysis type.
        
        Args:
            analysis_type: Analysis type
            
        Returns:
            List of (analyzer, rule) tuples
        """
        return self._rules.get(analysis_type, [])
    
    def get_all_analyzers(self) -> Dict[str, ConsistencyAnalyzer]:
        """
        Get all registered analyzers.
        
        Returns:
            Dictionary of analyzer IDs to analyzers
        """
        return self._analyzers.copy()
```

4. **RuleEngine**

```python
class RuleEngine:
    """Rule engine for consistency analysis."""
    
    def __init__(self, analysis_registry: AnalysisRegistry, logger: Logger):
        self.analysis_registry = analysis_registry
        self.logger = logger
    
    def run_analysis(self, analysis_type: str, inputs: Dict[str, Any]) -> List[InconsistencyRecord]:
        """
        Run consistency analysis.
        
        Args:
            analysis_type: Analysis type
            inputs: Analysis inputs
            
        Returns:
            List of inconsistency records
        """
        self.logger.info(f"Running analysis type: {analysis_type}")
        
        inconsistencies = []
        
        # Get rules for this analysis type
        rules = self.analysis_registry.get_rules_for_analysis_type(analysis_type)
        
        # Run each rule
        for analyzer, rule in rules:
            try:
                self.logger.debug(f"Running rule: {rule.rule_id} with analyzer: {analyzer.__class__.__name__}")
                
                # Apply rule
                rule_inconsistencies = analyzer.apply_rule(rule, inputs)
                
                # Add to list
                inconsistencies.extend(rule_inconsistencies)
                
                self.logger.debug(f"Rule {rule.rule_id} found {len(rule_inconsistencies)} inconsistencies")
            
            except Exception as e:
                self.logger.error(f"Error applying rule {rule.rule_id}: {e}")
        
        self.logger.info(f"Analysis complete. Found {len(inconsistencies)} inconsistencies")
        
        return inconsistencies
```

5. **ConsistencyAnalyzer (Interface)**

```python
class ConsistencyAnalyzer(ABC):
    """Base class for consistency analyzers."""
    
    def __init__(self, logger: Logger):
        self.logger = logger
    
    @abstractmethod
    def get_rules(self) -> List[ConsistencyRule]:
        """
        Get rules provided by this analyzer.
        
        Returns:
            List of consistency rules
        """
        pass
    
    @abstractmethod
    def apply_rule(self, rule: ConsistencyRule, inputs: Dict[str, Any]) -> List[InconsistencyRecord]:
        """
        Apply a rule to the inputs.
        
        Args:
            rule: Consistency rule
            inputs: Analysis inputs
            
        Returns:
            List of inconsistency records
        """
        pass
```

6. **CodeDocMetadataAnalyzer**

```python
class CodeDocMetadataAnalyzer(ConsistencyAnalyzer):
    """Analyzer for code-doc metadata consistency."""
    
    def __init__(self, metadata_component: Component, logger: Logger):
        super().__init__(logger)
        self.metadata_component = metadata_component
    
    def get_rules(self) -> List[ConsistencyRule]:
        """Get rules provided by this analyzer."""
        return [
            ConsistencyRule(
                rule_id="code_doc_metadata_intent",
                analysis_type="code_doc",
                description="Check if code intent matches documentation intent"
            ),
            ConsistencyRule(
                rule_id="code_doc_metadata_constraints",
                analysis_type="code_doc",
                description="Check if code constraints are documented"
            ),
            ConsistencyRule(
                rule_id="code_doc_metadata_design_principles",
                analysis_type="code_doc",
                description="Check if design principles are consistent"
            ),
            ConsistencyRule(
                rule_id="code_doc_metadata_reference_docs",
                analysis_type="code_doc",
                description="Check if reference documentation exists"
            )
        ]
    
    def apply_rule(self, rule: ConsistencyRule, inputs: Dict[str, Any]) -> List[InconsistencyRecord]:
        """Apply a rule to the inputs."""
        # Ensure required inputs are present
        if "code_file_path" not in inputs or "doc_file_path" not in inputs:
            self.logger.error("Missing required inputs for code-doc consistency analysis")
            return []
        
        code_file_path = inputs["code_file_path"]
        doc_file_path = inputs["doc_file_path"]
        
        # Get code metadata
        code_metadata = self.metadata_component.extract_metadata(code_file_path)
        
        # Read documentation content
        try:
            with open(doc_file_path, "r") as f:
                doc_content = f.read()
        except Exception as e:
            self.logger.error(f"Error reading doc file {doc_file_path}: {e}")
            return []
        
        inconsistencies = []
        
        # Apply the specific rule
        if rule.rule_id == "code_doc_metadata_intent":
            # Check if code intent matches documentation intent
            code_intent = code_metadata.get("intent", "")
            
            # Extract intent from documentation
            doc_intent_match = re.search(r"#+\s*Intent\s*\n(.*?)(?:\n#+|$)", doc_content, re.DOTALL | re.IGNORECASE)
            doc_intent = doc_intent_match.group(1).strip() if doc_intent_match else ""
            
            # Check for inconsistency
            if code_intent and doc_intent and not self._text_similarity(code_intent, doc_intent, threshold=0.7):
                inconsistencies.append(
                    InconsistencyRecord(
                        id=None,  # Will be assigned when saved
                        source_file=code_file_path,
                        target_file=doc_file_path,
                        inconsistency_type=InconsistencyType.INTENT_MISMATCH,
                        description="Code intent does not match documentation intent",
                        details={
                            "code_intent": code_intent,
                            "doc_intent": doc_intent,
                            "similarity_score": self._text_similarity(code_intent, doc_intent)
                        },
                        severity=InconsistencySeverity.MEDIUM,
                        status=InconsistencyStatus.OPEN,
                        confidence_score=0.8,
                        detected_at=datetime.now(),
                        resolved_at=None,
                        metadata={}
                    )
                )
        
        elif rule.rule_id == "code_doc_metadata_constraints":
            # Check if code constraints are documented
            code_constraints = code_metadata.get("constraints", "")
            
            # Extract constraints from documentation
            doc_constraints_match = re.search(r"#+\s*Constraints\s*\n(.*?)(?:\n#+|$)", doc_content, re.DOTALL | re.IGNORECASE)
            doc_constraints = doc_constraints_match.group(1).strip() if doc_constraints_match else ""
            
            # Check for inconsistency
            if code_constraints and not doc_constraints:
                inconsistencies.append(
                    InconsistencyRecord(
                        id=None,  # Will be assigned when saved
                        source_file=code_file_path,
                        target_file=doc_file_path,
                        inconsistency_type=InconsistencyType.MISSING_CONSTRAINTS,
                        description="Code constraints are not documented",
                        details={
                            "code_constraints": code_constraints
                        },
                        severity=InconsistencySeverity.LOW,
                        status=InconsistencyStatus.OPEN,
                        confidence_score=0.9,
                        detected_at=datetime.now(),
                        resolved_at=None,
                        metadata={}
                    )
                )
        
        # Similar implementations for other rules...
        
        return inconsistencies
    
    def _text_similarity(self, text1: str, text2: str, threshold: float = None) -> float:
        """Calculate similarity between two text strings."""
        # Simple implementation using difflib
        similarity = difflib.SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
        
        if threshold is not None:
            return similarity >= threshold
        
        return similarity
```

7. **ReportGenerator**

```python
class ReportGenerator:
    """Generator for consistency reports."""
    
    def __init__(self, logger: Logger):
        self.logger = logger
    
    def generate(self, inconsistencies: List[InconsistencyRecord]) -> ConsistencyReport:
        """
        Generate a consistency report.
        
        Args:
            inconsistencies: List of inconsistency records
            
        Returns:
            Consistency report
        """
        self.logger.info(f"Generating report for {len(inconsistencies)} inconsistencies")
        
        # Count inconsistencies by type
        type_counts = {}
        for inconsistency in inconsistencies:
            inconsistency_type = inconsistency.inconsistency_type.value
            type_counts[inconsistency_type] = type_counts.get(inconsistency_type, 0) + 1
        
        # Count inconsistencies by severity
        severity_counts = {}
        for inconsistency in inconsistencies:
            severity = inconsistency.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # Group inconsistencies by file
        file_inconsistencies = {}
        for inconsistency in inconsistencies:
            source_file = inconsistency.source_file
            if source_file not in file_inconsistencies:
                file_inconsistencies[source_file] = []
            file_inconsistencies[source_file].append(inconsistency)
        
        # Create summary
        summary = {
            "total_inconsistencies": len(inconsistencies),
            "by_type": type_counts,
            "by_severity": severity_counts,
            "by_file": {file: len(incons) for file, incons in file_inconsistencies.items()},
            "high_severity_count": severity_counts.get(InconsistencySeverity.HIGH.value, 0),
            "medium_severity_count": severity_counts.get(InconsistencySeverity.MEDIUM.value, 0),
            "low_severity_count": severity_counts.get(InconsistencySeverity.LOW.value, 0)
        }
        
        # Create report
        report = ConsistencyReport(
            id=str(uuid.uuid4()),
            summary=summary,
            inconsistencies=inconsistencies,
            generated_at=datetime.now(),
            report_version="1.0"
        )
        
        return report
```

8. **ConsistencyImpactAnalyzer**

```python
class ConsistencyImpactAnalyzer:
    """Analyzer for the impact of inconsistencies."""
    
    def __init__(self, doc_relationships_component: Component, logger: Logger):
        self.doc_relationships_component = doc_relationships_component
        self.logger = logger
    
    def analyze_impact(self, report: ConsistencyReport) -> None:
        """
        Analyze the impact of inconsistencies in the report.
        
        Args:
            report: Consistency report to analyze
        """
        self.logger.info("Analyzing impact of inconsistencies")
        
        # Analyze each inconsistency
        for inconsistency in report.inconsistencies:
            try:
                # Get document relationships
                source_file = inconsistency.source_file
                
                # Get documents impacted by changes to the source document
                impacts = self.doc_relationships_component.get_impacted_documents(source_file)
                
                # Add impact information to inconsistency metadata
                if impacts:
                    inconsistency.metadata["impacted_documents"] = [
                        {
                            "path": impact.target_document,
                            "impact_type": impact.impact_type,
                            "impact_level": impact.impact_level,
                            "relationship_type": impact.relationship_type
                        }
                        for impact in impacts
                    ]
                    
                    # Update severity based on impact
                    if any(impact.impact_level == "high" for impact in impacts):
                        inconsistency.severity = max(
                            inconsistency.severity,
                            InconsistencySeverity.HIGH
                        )
                
            except Exception as e:
                self.logger.error(f"Error analyzing impact for inconsistency {inconsistency.id}: {e}")

        # Add overall impact summary to report metadata
        all_impacted_docs = set()
        high_impact_docs = set()
        
        for inconsistency in report.inconsistencies:
            impacted_docs = inconsistency.metadata.get("impacted_documents", [])
            for doc in impacted_docs:
                all_impacted_docs.add(doc["path"])
                if doc["impact_level"] == "high":
                    high_impact_docs.add(doc["path"])
        
        report.metadata["impact_summary"] = {
            "total_impacted_documents": len(all_impacted_docs),
            "high_impact_documents": len(high_impact_docs),
            "impacted_document_list": list(all_impacted_docs)
        }
        
        self.logger.info(
            f"Impact analysis complete. "
            f"Found {len(all_impacted_docs)} impacted documents, "
            f"{len(high_impact_docs)} with high impact."
        )
```

9. **CrossReferenceConsistencyAnalyzer**

```python
class CrossReferenceConsistencyAnalyzer(ConsistencyAnalyzer):
    """Analyzer for cross-reference consistency between documentation files."""
    
    def __init__(self, doc_relationships_component: Component, logger: Logger):
        super().__init__(logger)
        self.doc_relationships_component = doc_relationships_component
    
    def get_rules(self) -> List[ConsistencyRule]:
        """Get rules provided by this analyzer."""
        return [
            ConsistencyRule(
                rule_id="broken_cross_references",
                analysis_type="doc_doc",
                description="Check for broken cross-references between documentation files"
            ),
            ConsistencyRule(
                rule_id="bidirectional_references",
                analysis_type="doc_doc",
                description="Check for missing bidirectional references"
            ),
            ConsistencyRule(
                rule_id="circular_references",
                analysis_type="doc_doc",
                description="Check for problematic circular references"
            )
        ]
    
    def apply_rule(self, rule: ConsistencyRule, inputs: Dict[str, Any]) -> List[InconsistencyRecord]:
        """Apply a rule to the inputs."""
        # Ensure required inputs are present
        if "doc_file_paths" not in inputs:
            self.logger.error("Missing required inputs for doc-doc consistency analysis")
            return []
        
        doc_file_paths = inputs["doc_file_paths"]
        inconsistencies = []
        
        # Apply the specific rule
        if rule.rule_id == "broken_cross_references":
            # Check if all cross-references point to existing files
            for doc_path in doc_file_paths:
                try:
                    # Get related documents
                    related_docs = self.doc_relationships_component.get_related_documents(
                        doc_path, relationship_type="references"
                    )
                    
                    # Check if target files exist
                    for related_doc in related_docs:
                        target_path = related_doc.target_document
                        
                        if not os.path.exists(target_path):
                            inconsistencies.append(
                                InconsistencyRecord(
                                    id=None,  # Will be assigned when saved
                                    source_file=doc_path,
                                    target_file=target_path,
                                    inconsistency_type=InconsistencyType.BROKEN_REFERENCE,
                                    description=f"Reference to non-existent file: {target_path}",
                                    details={
                                        "relationship_type": related_doc.relationship_type,
                                        "topic": related_doc.topic
                                    },
                                    severity=InconsistencySeverity.HIGH,
                                    status=InconsistencyStatus.OPEN,
                                    confidence_score=1.0,
                                    detected_at=datetime.now(),
                                    resolved_at=None,
                                    metadata={}
                                )
                            )
                
                except Exception as e:
                    self.logger.error(f"Error checking cross-references for {doc_path}: {e}")
        
        # Similar implementations for other rules...
        
        return inconsistencies
```

10. **Other Specialized Analyzers**

```python
class FunctionSignatureChangeAnalyzer(ConsistencyAnalyzer):
    """Analyzer for function signature changes."""
    
    def __init__(self, metadata_component: Component, logger: Logger):
        super().__init__(logger)
        self.metadata_component = metadata_component
    
    def get_rules(self) -> List[ConsistencyRule]:
        """Get rules provided by this analyzer."""
        return [
            ConsistencyRule(
                rule_id="function_signature_change",
                analysis_type="code_doc",
                description="Check if function signatures in code match documentation"
            )
        ]
    
    def apply_rule(self, rule: ConsistencyRule, inputs: Dict[str, Any]) -> List[InconsistencyRecord]:
        """Apply a rule to the inputs."""
        # Implementation would extract function signatures from code 
        # and compare them with documentation
        return []  # Placeholder


class ClassStructureChangeAnalyzer(ConsistencyAnalyzer):
    """Analyzer for class structure changes."""
    
    def __init__(self, metadata_component: Component, logger: Logger):
        super().__init__(logger)
        self.metadata_component = metadata_component
    
    def get_rules(self) -> List[ConsistencyRule]:
        """Get rules provided by this analyzer."""
        return [
            ConsistencyRule(
                rule_id="class_structure_change",
                analysis_type="code_doc",
                description="Check if class structures in code match documentation"
            )
        ]
    
    def apply_rule(self, rule: ConsistencyRule, inputs: Dict[str, Any]) -> List[InconsistencyRecord]:
        """Apply a rule to the inputs."""
        # Implementation would extract class structures from code 
        # and compare them with documentation
        return []  # Placeholder


class TerminologyConsistencyAnalyzer(ConsistencyAnalyzer):
    """Analyzer for terminology consistency."""
    
    def __init__(self, logger: Logger):
        super().__init__(logger)
    
    def get_rules(self) -> List[ConsistencyRule]:
        """Get rules provided by this analyzer."""
        return [
            ConsistencyRule(
                rule_id="terminology_consistency",
                analysis_type="doc_doc",
                description="Check if terminology is consistent across documentation"
            )
        ]
    
    def apply_rule(self, rule: ConsistencyRule, inputs: Dict[str, Any]) -> List[InconsistencyRecord]:
        """Apply a rule to the inputs."""
        # Implementation would analyze terminology usage across documents
        return []  # Placeholder


class ConfigParameterConsistencyAnalyzer(ConsistencyAnalyzer):
    """Analyzer for configuration parameter consistency."""
    
    def __init__(self, logger: Logger):
        super().__init__(logger)
    
    def get_rules(self) -> List[ConsistencyRule]:
        """Get rules provided by this analyzer."""
        return [
            ConsistencyRule(
                rule_id="config_parameter_consistency",
                analysis_type="full_project",
                description="Check if configuration parameters are consistently documented"
            )
        ]
    
    def apply_rule(self, rule: ConsistencyRule, inputs: Dict[str, Any]) -> List[InconsistencyRecord]:
        """Apply a rule to the inputs."""
        # Implementation would check configuration parameters across the project
        return []  # Placeholder


class APIDocumentationConsistencyAnalyzer(ConsistencyAnalyzer):
    """Analyzer for API documentation consistency."""
    
    def __init__(self, logger: Logger):
        super().__init__(logger)
    
    def get_rules(self) -> List[ConsistencyRule]:
        """Get rules provided by this analyzer."""
        return [
            ConsistencyRule(
                rule_id="api_documentation_consistency",
                analysis_type="full_project",
                description="Check if API endpoints are properly documented"
            )
        ]
    
    def apply_rule(self, rule: ConsistencyRule, inputs: Dict[str, Any]) -> List[InconsistencyRecord]:
        """Apply a rule to the inputs."""
        # Implementation would check API endpoints against documentation
        return []  # Placeholder
```

### Data Model Classes

1. **InconsistencyType**

```python
class InconsistencyType(Enum):
    """Types of inconsistencies."""
    
    INTENT_MISMATCH = "intent_mismatch"
    MISSING_CONSTRAINTS = "missing_constraints"
    DESIGN_PRINCIPLES_MISMATCH = "design_principles_mismatch"
    MISSING_REFERENCE_DOCS = "missing_reference_docs"
    BROKEN_REFERENCE = "broken_reference"
    MISSING_BIDIRECTIONAL_REFERENCE = "missing_bidirectional_reference"
    CIRCULAR_REFERENCE = "circular_reference"
    TERMINOLOGY_INCONSISTENCY = "terminology_inconsistency"
    CONFIG_PARAMETER_INCONSISTENCY = "config_parameter_inconsistency"
    API_DOCUMENTATION_INCONSISTENCY = "api_documentation_inconsistency"
    FUNCTION_SIGNATURE_MISMATCH = "function_signature_mismatch"
    CLASS_STRUCTURE_MISMATCH = "class_structure_mismatch"
    OTHER = "other"
```

2. **InconsistencySeverity**

```python
class InconsistencySeverity(Enum):
    """Severity levels for inconsistencies."""
    
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
```

3. **InconsistencyStatus**

```python
class InconsistencyStatus(Enum):
    """Status values for inconsistencies."""
    
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    IGNORED = "ignored"
```

4. **InconsistencyRecord**

```python
@dataclass
class InconsistencyRecord:
    """Record of an inconsistency."""
    
    source_file: str
    target_file: str
    inconsistency_type: InconsistencyType
    description: str
    details: Dict[str, Any]
    severity: InconsistencySeverity
    status: InconsistencyStatus
    confidence_score: float  # 0.0 to 1.0
    detected_at: datetime
    metadata: Dict[str, Any]
    id: Optional[str] = None
    resolved_at: Optional[datetime] = None
```

5. **ConsistencyRule**

```python
@dataclass
class ConsistencyRule:
    """Rule for consistency checking."""
    
    rule_id: str
    analysis_type: str  # e.g., "code_doc", "doc_doc", "full_project"
    description: str
```

6. **ConsistencyReport**

```python
@dataclass
class ConsistencyReport:
    """Report of consistency analysis."""
    
    id: str
    summary: Dict[str, Any]
    inconsistencies: List[InconsistencyRecord]
    generated_at: datetime
    report_version: str
    metadata: Dict[str, Any] = field(default_factory=dict)
```

7. **InconsistencyORM**

```python
class InconsistencyORM(Base):
    """ORM model for inconsistency records."""
    
    __tablename__ = "inconsistencies"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_file = Column(String, nullable=False)
    target_file = Column(String, nullable=False)
    inconsistency_type = Column(String, nullable=False)
    description = Column(String, nullable=False)
    details = Column(Text, nullable=True)
    severity = Column(String, nullable=False)
    status = Column(String, nullable=False)
    confidence_score = Column(Float, nullable=False)
    detected_at = Column(DateTime, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    metadata = Column(Text, nullable=True)
```

### Configuration Class

```python
@dataclass
class ConsistencyAnalysisConfig:
    """Configuration for consistency analysis."""
    
    enabled_analyzers: List[str]
    high_severity_threshold: float
    medium_severity_threshold: float
    background_check_interval_minutes: int
    max_inconsistencies_per_report: int
```

Default configuration values:

| Parameter | Description | Default | Valid Values |
|-----------|-------------|---------|-------------|
| `enabled_analyzers` | List of enabled analyzers | All analyzers | List of analyzer IDs |
| `high_severity_threshold` | Threshold for high severity | `0.8` | `0.0-1.0` |
| `medium_severity_threshold` | Threshold for medium severity | `0.5` | `0.0-1.0` |
| `background_check_interval_minutes` | Interval for background checks | `60` | `10-1440` |
| `max_inconsistencies_per_report` | Maximum inconsistencies per report | `1000` | `100-10000` |

## Implementation Plan

### Phase 1: Core Structure
1. Implement ConsistencyAnalysisComponent as a system component
2. Define data model classes (InconsistencyRecord, InconsistencyType, etc.)
3. Create configuration class
4. Implement ORM model for inconsistency records

### Phase 2: Analysis Framework
1. Implement AnalysisRegistry for managing consistency analyzers
2. Create RuleEngine for running analyses
3. Implement ConsistencyAnalyzer interface
4. Set up specialized analyzers for different types of consistency checks

### Phase 3: Repository and Reporting
1. Implement InconsistencyRepository for persistent storage
2. Create ReportGenerator for generating consistency reports
3. Implement ConsistencyImpactAnalyzer for impact analysis
4. Add functionality to filter and query inconsistencies

### Phase 4: Integration
1. Integrate with Documentation Relationships component
2. Connect to the metadata extraction component
3. Set up event handlers for document changes
4. Implement automatic consistency checking on document changes

## Security Considerations

The Consistency Analysis component implements these security measures:
- Validation of file paths to prevent path traversal attacks
- Sanitization of inconsistency records before storage
- Safe handling of markdown and code content during analysis
- Proper error isolation and reporting
- Thread safety for concurrent analysis operations
- Protection against resource exhaustion from large analyses
- Proper handling of file I/O operations

## Testing Strategy

### Unit Tests
- Test individual analyzers for correctness
- Test inconsistency repository operations
- Test report generation
- Test impact analysis

### Integration Tests
- Test database integration
- Test integration with document relationship component
- Test integration with metadata extraction
- Test end-to-end consistency analysis workflow

### System Tests
- Test performance with large codebases
- Test correctness of inconsistency detection
- Test impact analysis with complex relationship graphs

## Dependencies on Other Plans

This plan depends on:
- Database Schema plan (for ORM models)
- Documentation Relationships plan (for relationship analysis)
- Metadata Extraction plan (for code analysis)
- Component Initialization plan (for component framework)

## Implementation Timeline

1. Core Structure - 1 day
2. Analysis Framework - 2 days
3. Repository and Reporting - 2 days
4. Integration - 1 day

Total: 6 days
