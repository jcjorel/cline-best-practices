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
# Implements the DocRelationshipsComponent class, the main component responsible
# for managing and analyzing relationships between documentation files within the
# DBP system. It conforms to the Component protocol and integrates the graph,
# repository, analyzer, visualizer, and query interface for document relationships.
###############################################################################
# [Source file design principles]
# - Conforms to the Component protocol (`src/dbp/core/component.py`).
# - Encapsulates the documentation relationship subsystem.
# - Declares dependencies (e.g., 'database', 'metadata_extraction').
# - Initializes internal parts (repository, graph, analyzer, etc.) during `initialize`.
# - Loads existing relationships from the database on startup.
# - Provides public methods for analyzing relationships, finding impacts, detecting changes,
#   querying relationships, and generating visualizations.
# - Design Decision: Component Facade for Doc Relationships (2025-04-15)
#   * Rationale: Groups all relationship-related logic into a single manageable component.
#   * Alternatives considered: Exposing individual parts (more complex integration).
###############################################################################
# [Source file constraints]
# - Depends on the core component framework and other components like 'database'.
# - Requires all helper classes within the `doc_relationships` package.
# - Assumes configuration is available via InitializationContext.
# - Performance of analysis and loading depends on the number of documents and relationships.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - doc/DOCUMENT_RELATIONSHIPS.md
# - src/dbp/core/component.py
# - All other files in src/dbp/doc_relationships/
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:24:40Z : Initial creation of DocRelationshipsComponent by CodeAssistant
# * Implemented Component protocol methods, initialization of sub-components, and public API.
###############################################################################

import logging
from typing import List, Optional, Any, Dict

# Core component imports
try:
    from ..core.component import Component, InitializationContext
    # Import config type if defined, else use Any
    # from ..config import AppConfig, DocRelationshipsConfig # Example
    Config = Any
    DocRelationshipsConfig = Any # Placeholder
except ImportError:
    logging.getLogger(__name__).error("Failed to import core component types for DocRelationshipsComponent.", exc_info=True)
    # Placeholders
    class Component: pass
    class InitializationContext: pass
    Config = Any
    DocRelationshipsConfig = Any

# Imports for internal services
try:
    from .data_models import DocumentRelationship, DocImpact, DocChangeImpact
    from .repository import RelationshipRepository, RepositoryError
    from .graph import RelationshipGraph
    from .analyzer import RelationshipAnalyzer
    from .impact_analyzer import ImpactAnalyzer
    from .change_detector import ChangeDetector
    from .visualization import GraphVisualization
    from .query_interface import QueryInterface
    # Import dependencies for type hints
    from ..database.database import DatabaseManager # Assuming db component provides this
    from ..metadata_extraction.component import MetadataExtractionComponent # Needed by analyzer? Check plan.
except ImportError as e:
    logging.getLogger(__name__).error(f"DocRelationshipsComponent ImportError: {e}. Check package structure.", exc_info=True)
    # Placeholders
    DocumentRelationship, DocImpact, DocChangeImpact = object, object, object
    RelationshipRepository, RepositoryError = object, Exception
    RelationshipGraph = object
    RelationshipAnalyzer = object
    ImpactAnalyzer = object
    ChangeDetector = object
    GraphVisualization = object
    QueryInterface = object
    DatabaseManager = object
    MetadataExtractionComponent = object


logger = logging.getLogger(__name__)

class ComponentNotInitializedError(Exception):
    """Exception raised when a component method is called before initialization."""
    pass

class DocRelationshipsComponent(Component):
    """
    DBP system component responsible for managing and analyzing
    relationships between documentation files.
    """
    _initialized: bool = False
    _repository: Optional[RelationshipRepository] = None
    _graph: Optional[RelationshipGraph] = None
    _analyzer: Optional[RelationshipAnalyzer] = None
    _impact_analyzer: Optional[ImpactAnalyzer] = None
    _change_detector: Optional[ChangeDetector] = None
    _visualizer: Optional[GraphVisualization] = None
    _query_interface: Optional[QueryInterface] = None

    @property
    def name(self) -> str:
        """Returns the unique name of the component."""
        return "doc_relationships"

    @property
    def dependencies(self) -> List[str]:
        """Returns the list of component names this component depends on."""
        # Depends on database for persistence.
        # Analyzer might need metadata_extraction if analyzing code comments for refs.
        # Plan shows dependency on metadata_extraction for analyzer.
        return ["database", "metadata_extraction"]

    def initialize(self, context: InitializationContext):
        """
        Initializes the Documentation Relationships component and its sub-components.

        Args:
            context: The initialization context.
        """
        if self._initialized:
            logger.warning(f"Component '{self.name}' already initialized.")
            return

        self.logger = context.logger # Use logger from context
        self.logger.info(f"Initializing component '{self.name}'...")

        try:
            # Get component-specific configuration
            component_config = context.config.get(self.name, {}) # Assumes dict-like config

            # Get dependent components
            db_component = context.get_component("database")
            metadata_component = context.get_component("metadata_extraction") # Needed for analyzer

            # Ensure db_component provides DatabaseManager access
            if not hasattr(db_component, 'db_manager') or not isinstance(db_component.db_manager, DatabaseManager):
                 raise TypeError("Database component does not expose a valid 'db_manager' attribute.")
            db_manager = db_component.db_manager

            # Instantiate sub-components
            self._repository = RelationshipRepository(db_manager=db_manager, logger_override=self.logger.getChild("repository"))
            self._graph = RelationshipGraph(logger_override=self.logger.getChild("graph"))
            # Analyzer needs a way to access file content - assuming metadata component provides this or uses FileAccessService
            # For now, passing metadata_component, assuming analyzer knows how to use it.
            # TODO: Refine how analyzer gets file content if needed.
            file_access_service = getattr(metadata_component, 'file_access_service', None) # Example: try to get it
            if file_access_service is None:
                 self.logger.warning("Could not get FileAccessService from metadata_component for RelationshipAnalyzer. Analysis might be limited.")
                 # Create a dummy one? Or let analyzer handle it? Let analyzer handle potential None.
            self._analyzer = RelationshipAnalyzer(file_access_service=file_access_service, logger_override=self.logger.getChild("analyzer"))
            self._impact_analyzer = ImpactAnalyzer(relationship_graph=self._graph, logger_override=self.logger.getChild("impact"))
            self._change_detector = ChangeDetector(impact_analyzer=self._impact_analyzer, logger_override=self.logger.getChild("change"))
            self._visualizer = GraphVisualization(relationship_graph=self._graph, logger_override=self.logger.getChild("viz"))
            self._query_interface = QueryInterface(relationship_graph=self._graph, logger_override=self.logger.getChild("query"))

            # Load existing relationships from DB into the graph
            self._load_relationships()

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

    def _load_relationships(self):
        """Loads existing relationships from the repository into the in-memory graph."""
        if not self._repository or not self._graph: return
        self.logger.info("Loading existing document relationships into graph...")
        try:
            relationships = self._repository.get_all_relationships()
            count = 0
            for rel in relationships:
                self._graph.add_relationship(
                    source=rel.source_document,
                    target=rel.target_document,
                    relationship_type=rel.relationship_type,
                    topic=rel.topic,
                    scope=rel.scope,
                    metadata=rel.metadata
                )
                count += 1
            self.logger.info(f"Loaded {count} relationships into the graph.")
        except RepositoryError as e:
             self.logger.error(f"Failed to load relationships from repository: {e}", exc_info=True)
             # Continue with an empty graph? Or raise? Let's continue for now.
        except Exception as e:
             self.logger.error(f"Unexpected error loading relationships: {e}", exc_info=True)


    def shutdown(self) -> None:
        """Performs cleanup for the document relationships component."""
        self.logger.info(f"Shutting down component '{self.name}'...")
        # Clear in-memory graph? Or assume it's okay to lose on shutdown?
        if self._graph:
             self._graph.clear()
        self._repository = None
        self._graph = None
        self._analyzer = None
        self._impact_analyzer = None
        self._change_detector = None
        self._visualizer = None
        self._query_interface = None
        self._initialized = False
        self.logger.info(f"Component '{self.name}' shut down.")

    @property
    def is_initialized(self) -> bool:
        """Returns True if the component is initialized."""
        return self._initialized

    # --- Public API Methods ---

    def analyze_and_update_document_relationships(self, document_path: str) -> bool:
        """
        Analyzes a document for relationships and updates the graph and database.

        Args:
            document_path: The path of the document to analyze.

        Returns:
            True if analysis and update were successful, False otherwise.
        """
        if not self.is_initialized or not self._analyzer or not self._repository or not self._graph:
            raise ComponentNotInitializedError(self.name)
        self.logger.info(f"Analyzing and updating relationships for: {document_path}")
        try:
            # 1. Analyze the document to find current relationships
            extracted_relationships = self._analyzer.analyze_document(document_path)

            # 2. Get existing relationships from DB for this source document
            existing_relationships = self._repository.get_relationships_by_source(document_path)
            existing_map = {(rel.target_document, rel.relationship_type, rel.topic, rel.scope): rel for rel in existing_relationships}
            extracted_map = {(rel.target_document, rel.relationship_type, rel.topic, rel.scope): rel for rel in extracted_relationships}

            # 3. Determine changes (added, removed)
            added_rels = [rel for key, rel in extracted_map.items() if key not in existing_map]
            removed_rels = [rel for key, rel in existing_map.items() if key not in extracted_map]

            # 4. Update database and graph
            for rel_to_remove in removed_rels:
                 if rel_to_remove.id:
                      self._repository.delete_relationship(rel_to_remove.id)
                      self._graph.remove_relationship(rel_to_remove.source_document, rel_to_remove.target_document, rel_to_remove.relationship_type) # Might need key if multiple edges
                 else:
                      self.logger.warning(f"Cannot remove relationship without ID: {rel_to_remove}")

            for rel_to_add in added_rels:
                 new_id = self._repository.save_relationship(rel_to_add)
                 rel_to_add.id = new_id # Update dataclass with ID
                 self._graph.add_relationship(
                      source=rel_to_add.source_document,
                      target=rel_to_add.target_document,
                      relationship_type=rel_to_add.relationship_type,
                      topic=rel_to_add.topic,
                      scope=rel_to_add.scope,
                      metadata=rel_to_add.metadata
                 )
            self.logger.info(f"Updated relationships for {document_path}: {len(added_rels)} added, {len(removed_rels)} removed.")
            return True
        except Exception as e:
            self.logger.error(f"Failed to analyze and update relationships for {document_path}: {e}", exc_info=True)
            return False


    def get_impacted_documents(self, document_path: str) -> List[DocImpact]:
        """Delegates to ImpactAnalyzer to find documents impacted by changes."""
        if not self.is_initialized or not self._impact_analyzer:
            raise ComponentNotInitializedError(self.name)
        return self._impact_analyzer.analyze_impact(document_path)

    def detect_document_change_impacts(self, document_path: str, old_content: str, new_content: str) -> List[DocChangeImpact]:
        """Delegates to ChangeDetector to find impacts of specific content changes."""
        if not self.is_initialized or not self._change_detector:
            raise ComponentNotInitializedError(self.name)
        return self._change_detector.detect_changes_and_impact(document_path, old_content, new_content)

    def get_related_documents(self, document_path: str, relationship_type: Optional[str] = None) -> List[DocumentRelationship]:
        """Delegates to QueryInterface to find related documents."""
        if not self.is_initialized or not self._query_interface:
            raise ComponentNotInitializedError(self.name)
        return self._query_interface.get_related_documents(document_path, relationship_type)

    def get_mermaid_diagram(self, document_paths: Optional[List[str]] = None) -> str:
        """Delegates to GraphVisualization to generate a Mermaid diagram."""
        if not self.is_initialized or not self._visualizer:
            raise ComponentNotInitializedError(self.name)
        return self._visualizer.generate_mermaid_diagram(document_paths)
