###############################################################################
# IMPORTANT: This header comment is designed for GenAI code review and maintenance
# Any GenAI tool working with this file MUST preserve and update this header
###############################################################################
# [GenAI coding tool directive]
# - Maintain this header with all modifications
# - Update History section with each change
# - Keep only the 4 most recent records in the history section. Sort from older to newer.
# - Preserve Intent, Design, and Constraints sections
# - Use this header as context for code reviews and modifications
# - Ensure all changes align with the design principles
# - Respect system prompt directives at all times
###############################################################################
# [Source file intent]
# Implements the ConsistencyAnalysisComponent class, the main entry point for the
# consistency analysis subsystem. It conforms to the Component protocol, initializes
# and manages the lifecycle of its internal parts (repository, registry, engine,
# analyzers, reporter), registers the analyzers, and provides the public API for
# running analyses and managing inconsistency records.
###############################################################################
# [Source file design principles]
# - Conforms to the Component protocol (`src/dbp/core/component.py`).
# - Encapsulates the entire consistency analysis logic.
# - Declares dependencies on other components ('database', 'doc_relationships', 'metadata_extraction').
# - Initializes sub-components (repository, registry, engine, etc.) in `initialize`.
# - Registers concrete analyzer implementations with the `AnalysisRegistry`.
# - Provides high-level methods for triggering different analysis scopes.
# - Manages its own initialization state.
# - Design Decision: Component Facade for Consistency Analysis (2025-04-15)
#   * Rationale: Presents the consistency analysis subsystem as a single component.
#   * Alternatives considered: Exposing engine/registry directly (more complex).
###############################################################################
# [Source file constraints]
# - Depends on the core component framework and other system components.
# - Requires all helper classes within the `consistency_analysis` package.
# - Assumes configuration is available via InitializationContext.
# - Relies on placeholder implementations within the concrete analyzers.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - src/dbp/core/component.py
# - All other files in src/dbp/consistency_analysis/
###############################################################################
# [GenAI tool change history]
# 2025-04-20T01:21:25Z : Completed dependency injection refactoring by CodeAssistant
# * Removed dependencies property
# * Made dependencies parameter required in initialize method
# * Removed conditional logic for backwards compatibility
# 2025-04-20T00:09:49Z : Added dependency injection support by CodeAssistant
# * Updated initialize() method to accept dependencies parameter
# * Added dictionary-based dependency retrieval with validation
# * Enhanced method documentation for dependency injection
# 2025-04-15T10:32:00Z : Initial creation of ConsistencyAnalysisComponent by CodeAssistant
# * Implemented Component protocol, initialization, analyzer registration, and public API methods.
###############################################################################

import logging
from datetime import datetime, timezone
from typing import List, Optional, Any, Dict

# Core component imports
try:
    from ..core.component import Component, InitializationContext
    Config = Any # Placeholder for config type
    ConsistencyAnalysisConfig = Any # Placeholder for specific config model
except ImportError:
    logging.getLogger(__name__).error("Failed to import core component types for ConsistencyAnalysisComponent.", exc_info=True)
    class Component: pass
    class InitializationContext: pass
    Config = Any
    ConsistencyAnalysisConfig = Any

# Imports for internal services
try:
    from .data_models import InconsistencyRecord, ConsistencyReport, InconsistencyStatus, InconsistencySeverity # Import Enums too
    from .repository import InconsistencyRepository, RepositoryError
    from .registry import AnalysisRegistry, AnalysisError
    from .engine import RuleEngine
    # Import concrete analyzers (assuming they are in analyzer.py)
    from .analyzer import (
        ConsistencyAnalyzer, # Base class for type hints if needed
        CodeDocMetadataAnalyzer,
        FunctionSignatureChangeAnalyzer,
        ClassStructureChangeAnalyzer,
        CrossReferenceConsistencyAnalyzer,
        TerminologyConsistencyAnalyzer,
        ConfigParameterConsistencyAnalyzer,
        APIDocumentationConsistencyAnalyzer,
    )
    # Import other dependencies needed by analyzers/component
    from .impact_analyzer import ConsistencyImpactAnalyzer # Renamed from plan
    from .report_generator import ReportGenerator
    from ..doc_relationships.component import DocRelationshipsComponent # Dependency
    from ..metadata_extraction.component import MetadataExtractionComponent # Dependency
    from ..database.database import DatabaseManager # For type hint

except ImportError as e:
    logging.getLogger(__name__).error(f"ConsistencyAnalysisComponent ImportError: {e}. Check package structure.", exc_info=True)
    # Placeholders
    InconsistencyRecord, ConsistencyReport, InconsistencyStatus, InconsistencySeverity = object, object, object, object
    InconsistencyRepository, RepositoryError = object, Exception
    AnalysisRegistry, AnalysisError = object, Exception
    RuleEngine = object
    ConsistencyAnalyzer = object
    CodeDocMetadataAnalyzer, FunctionSignatureChangeAnalyzer, ClassStructureChangeAnalyzer = object, object, object
    CrossReferenceConsistencyAnalyzer, TerminologyConsistencyAnalyzer = object, object
    ConfigParameterConsistencyAnalyzer, APIDocumentationConsistencyAnalyzer = object, object
    ConsistencyImpactAnalyzer = object
    ReportGenerator = object
    DocRelationshipsComponent = object
    MetadataExtractionComponent = object
    DatabaseManager = object


logger = logging.getLogger(__name__)

class ComponentNotInitializedError(Exception):
    """Exception raised when a component method is called before initialization."""
    pass

class ConsistencyAnalysisComponent(Component):
    """
    DBP system component responsible for analyzing consistency between
    documentation and code artifacts.
    """
    _initialized: bool = False
    _repository: Optional[InconsistencyRepository] = None
    _registry: Optional[AnalysisRegistry] = None
    _engine: Optional[RuleEngine] = None
    _impact_analyzer: Optional[ConsistencyImpactAnalyzer] = None
    _report_generator: Optional[ReportGenerator] = None

    @property
    def name(self) -> str:
        """Returns the unique name of the component."""
        return "consistency_analysis"

    def initialize(self, context: InitializationContext, dependencies: Dict[str, Component]) -> None:
        """
        [Function intent]
        Initializes the Consistency Analysis component and its sub-components.
        
        [Implementation details]
        Uses the strongly-typed configuration for component setup.
        Creates internal sub-components and registers consistency analyzers.
        Sets the _initialized flag when initialization succeeds.
        
        [Design principles]
        Explicit initialization with strong typing.
        Dependency injection for improved performance and testability.
        Type-safe configuration access.
        
        Args:
            context: Initialization context with typed configuration and resources
            dependencies: Dictionary of pre-resolved dependencies {name: component_instance}
        """
        if self._initialized:
            logger.warning(f"Component '{self.name}' already initialized.")
            return

        self.logger = context.logger # Use logger from context
        self.logger.info(f"Initializing component '{self.name}'...")

        try:
            # Get strongly-typed configuration
            config = context.get_typed_config()
            component_config = getattr(config, self.name)

            # Get dependent components using dependency injection
            self.logger.debug("Using injected dependencies")
            db_component = self.get_dependency(dependencies, "database")
            doc_relationships_component = self.get_dependency(dependencies, "doc_relationships")
            metadata_extraction_component = self.get_dependency(dependencies, "metadata_extraction")

            # Get database manager using the method instead of accessing attribute
            db_manager = db_component.get_manager()

            # Instantiate sub-components
            self._repository = InconsistencyRepository(db_manager=db_manager, logger_override=self.logger.getChild("repository"))
            self._registry = AnalysisRegistry(logger_override=self.logger.getChild("registry"))
            self._engine = RuleEngine(analysis_registry=self._registry, logger_override=self.logger.getChild("engine"))
            self._impact_analyzer = ConsistencyImpactAnalyzer(doc_relationships_component=doc_relationships_component, logger_override=self.logger.getChild("impact"))
            self._report_generator = ReportGenerator(logger_override=self.logger.getChild("reporter"))

            # Register all available analyzers
            self._register_analyzers(metadata_extraction_component, doc_relationships_component)

            self._initialized = True
            self.logger.info(f"Component '{self.name}' initialized successfully.")

        except KeyError as e:
             self.logger.error(f"Initialization failed: Missing dependency component '{e}'. Ensure it's registered.")
             self._initialized = False
             raise RuntimeError(f"Missing dependency during {self.name} initialization: {e}") from e
        except Exception as e:
            self.logger.error(f"Initialization failed for component '{self.name}': {e}", exc_info=True)
            self._initialized = False
            raise RuntimeError(f"Failed to initialize {self.name}") from e

    def _register_analyzers(self, metadata_component, doc_rel_component):
        """Instantiates and registers all concrete ConsistencyAnalyzer implementations."""
        if not self._registry: return
        self.logger.debug("Registering consistency analyzers...")

        analyzers_to_register = [
            ("code_doc_metadata", CodeDocMetadataAnalyzer(metadata_component, self.logger.getChild("CDMA"))),
            ("function_signature_change", FunctionSignatureChangeAnalyzer(metadata_component, self.logger.getChild("FSCA"))),
            ("class_structure_change", ClassStructureChangeAnalyzer(metadata_component, self.logger.getChild("CSCA"))),
            ("cross_reference_consistency", CrossReferenceConsistencyAnalyzer(doc_rel_component, self.logger.getChild("CRCA"))),
            ("terminology_consistency", TerminologyConsistencyAnalyzer(self.logger.getChild("TCA"))),
            ("config_parameter_consistency", ConfigParameterConsistencyAnalyzer(self.logger.getChild("CPCA"))),
            ("api_documentation_consistency", APIDocumentationConsistencyAnalyzer(self.logger.getChild("ADCA"))),
        ]

        count = 0
        for analyzer_id, analyzer_instance in analyzers_to_register:
             try:
                  self._registry.register_analyzer(analyzer_id, analyzer_instance)
                  count += 1
             except (ValueError, TypeError, AnalysisError) as e:
                  self.logger.error(f"Failed to register analyzer '{analyzer_id}': {e}")
             except Exception as e:
                  self.logger.error(f"Unexpected error registering analyzer '{analyzer_id}': {e}", exc_info=True)
        self.logger.info(f"Registered {count}/{len(analyzers_to_register)} consistency analyzers.")


    def shutdown(self) -> None:
        """Performs cleanup for the consistency analysis component."""
        self.logger.info(f"Shutting down component '{self.name}'...")
        # Add cleanup logic if needed (e.g., stopping background analysis threads if any)
        self._repository = None
        self._registry = None
        self._engine = None
        self._impact_analyzer = None
        self._report_generator = None
        self._initialized = False
        self.logger.info(f"Component '{self.name}' shut down.")

    @property
    def is_initialized(self) -> bool:
        """Returns True if the component is initialized."""
        return self._initialized

    # --- Public API Methods ---

    def analyze_code_doc_consistency(self, code_file_path: str, doc_file_path: str) -> List[InconsistencyRecord]:
        """Analyzes consistency between a specific code file and documentation file."""
        if not self.is_initialized or not self._engine or not self._repository:
            raise ComponentNotInitializedError(self.name)
        self.logger.info(f"Requesting code-doc consistency analysis between '{code_file_path}' and '{doc_file_path}'.")
        inputs = {"code_file_path": code_file_path, "doc_file_path": doc_file_path}
        inconsistencies = self._engine.run_analysis(analysis_type="code_doc", inputs=inputs)
        # Persist detected inconsistencies
        for inc in inconsistencies:
             try:
                  self._repository.save(inc)
             except RepositoryError as e:
                  self.logger.error(f"Failed to save inconsistency record: {e}")
        return inconsistencies

    def analyze_doc_doc_consistency(self, doc_file_paths: List[str]) -> List[InconsistencyRecord]:
        """Analyzes consistency among a set of documentation files."""
        if not self.is_initialized or not self._engine or not self._repository:
            raise ComponentNotInitializedError(self.name)
        self.logger.info(f"Requesting doc-doc consistency analysis for {len(doc_file_paths)} files.")
        inputs = {"doc_file_paths": doc_file_paths}
        inconsistencies = self._engine.run_analysis(analysis_type="doc_doc", inputs=inputs)
        for inc in inconsistencies:
             try:
                  self._repository.save(inc)
             except RepositoryError as e:
                  self.logger.error(f"Failed to save inconsistency record: {e}")
        return inconsistencies

    def analyze_project_consistency(self, project_root: Optional[str] = None) -> List[InconsistencyRecord]:
        """Performs a comprehensive consistency analysis across the project."""
        if not self.is_initialized or not self._engine or not self._repository:
            raise ComponentNotInitializedError(self.name)
        self.logger.info(f"Requesting full project consistency analysis (Root: {project_root or 'Default'}).")
        inputs = {"project_root": project_root} if project_root else {}
        # Run multiple analysis types if needed, or have a dedicated 'full_project' type
        inconsistencies = self._engine.run_analysis(analysis_type="full_project", inputs=inputs)
        # Add results from other types if necessary
        # inconsistencies.extend(self._engine.run_analysis(analysis_type="code_doc", inputs=inputs)) # Example
        # inconsistencies.extend(self._engine.run_analysis(analysis_type="doc_doc", inputs=inputs)) # Example
        # Deduplicate results if running multiple types
        unique_inconsistencies = {inc.id: inc for inc in inconsistencies}.values() # Simple deduplication by generated ID

        for inc in unique_inconsistencies:
             try:
                  self._repository.save(inc)
             except RepositoryError as e:
                  self.logger.error(f"Failed to save inconsistency record: {e}")
        return list(unique_inconsistencies)


    def get_inconsistencies(self, **filters) -> List[InconsistencyRecord]:
        """Retrieves stored inconsistency records, optionally applying filters."""
        if not self.is_initialized or not self._repository:
            raise ComponentNotInitializedError(self.name)
        # Pass filters directly to the repository method
        return self._repository.get_inconsistencies(**filters)

    def generate_report(self, inconsistencies: List[InconsistencyRecord]) -> ConsistencyReport:
        """Generates a structured report from a list of inconsistencies."""
        if not self.is_initialized or not self._report_generator or not self._impact_analyzer:
            raise ComponentNotInitializedError(self.name)
        # Generate the basic report
        report = self._report_generator.generate(inconsistencies)
        # Enhance the report with impact analysis (modifies report in-place)
        self._impact_analyzer.analyze_impact(report)
        return report

    def mark_inconsistency_resolved(self, inconsistency_id: str) -> bool:
        """Marks a specific inconsistency as resolved in the database."""
        if not self.is_initialized or not self._repository:
            raise ComponentNotInitializedError(self.name)
        try:
            record = self._repository.get(inconsistency_id)
            if not record:
                 self.logger.warning(f"Cannot resolve inconsistency: ID '{inconsistency_id}' not found.")
                 return False
            record.status = InconsistencyStatus.RESOLVED
            record.resolved_at = datetime.now(timezone.utc)
            self._repository.update(record)
            self.logger.info(f"Marked inconsistency '{inconsistency_id}' as RESOLVED.")
            return True
        except (RepositoryError, ValueError) as e:
             self.logger.error(f"Failed to mark inconsistency '{inconsistency_id}' as resolved: {e}")
             return False
