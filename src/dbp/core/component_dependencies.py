###############################################################################
# IMPORTANT: This header comment is designed for GenAI code review and maintenance
# Any GenAI tool working with this file MUST preserve and update this header
###############################################################################
# [GenAI coding tool directive]
# - Maintain this header with all modifications
# - Update History section with each change
# - Keep only the 4 most recent records in the history section. Sort from newer to older.
# - Preserve Intent, Design, and Constraints sections
# - Use this header as context for code reviews and modifications
# - Ensure all changes align with the design principles
# - Respect system prompt directives at all times
###############################################################################
# [Source file intent]
# Defines the component dependencies for the DBP system, serving as a centralized
# registry of all system components with their dependencies. This enables a clearer view
# of component relationships and simplifies the component registration process.
###############################################################################
# [Source file design principles]
# - Single responsibility for component dependency declarations
# - Separation of component declarations from registration logic
# - Clear declaration of component relationships
# - Centralized management of component dependency graph
###############################################################################
# [Source file constraints]
# - Component declarations must include all necessary information for registration
# - Must be kept in sync with actual component implementations
# - Changes to this file affect the entire system's initialization
###############################################################################
# [Dependencies]
# codebase:- doc/design/COMPONENT_INITIALIZATION.md
###############################################################################
# [GenAI tool change history]
# 2025-04-25T09:07:45Z : Created component_dependencies.py by CodeAssistant
# * Extracted component declarations from lifecycle.py
# * Created centralized component declaration list
# * Structured as list of dictionaries for easier maintenance
###############################################################################

"""
[Module intent]
Provides a centralized list of all system components with their dependencies.

[Implementation details]
Component declarations are structured as dictionaries with import path,
component class name, component name, and dependency list.

[Design principles]
Centralized component declaration for clearer dependency management.
"""

# Component dependency declarations
# Each component is declared with:
# - import_path: Path to import the component module
# - component_class: Name of the component class
# - name: Component name (matches what the component's name property returns)
# - dependencies: List of component names this component depends on

COMPONENT_DECLARATIONS = [
    # Core components
    {
        "import_path": "dbp.core.file_access_component",
        "component_class": "FileAccessComponent",
        "name": "file_access",
        "dependencies": ["filter", "config_manager"]
    },
    
    # Database component
    {
        "import_path": "dbp.database.database",
        "component_class": "DatabaseComponent",
        "name": "database",
        "dependencies": ["config_manager"]
    },
    
    # File system monitoring components
    {
        "import_path": "dbp.fs_monitor.component",
        "component_class": "FSMonitorComponent",
        "name": "fs_monitor",
        "dependencies": ["config_manager"]
    },
    {
        "import_path": "dbp.fs_monitor.filter",
        "component_class": "FilterComponent",
        "name": "filter",
        "dependencies": ["config_manager"]
    },
    
    # Memory cache component
    {
        "import_path": "dbp.memory_cache.component",
        "component_class": "MemoryCacheComponent",
        "name": "memory_cache",
        "dependencies": ["database", "config_manager"]
    },
    
    # Metadata extraction component
    {
        "import_path": "dbp.metadata_extraction.component",
        "component_class": "MetadataExtractionComponent",
        "name": "metadata_extraction",
        "dependencies": ["database"]
    },
    
    # Document relationships component
    {
        "import_path": "dbp.doc_relationships.component",
        "component_class": "DocRelationshipsComponent",
        "name": "doc_relationships",
        "dependencies": ["database", "metadata_extraction", "file_access"]
    },
    
    # Consistency analysis component
    {
        "import_path": "dbp.consistency_analysis.component",
        "component_class": "ConsistencyAnalysisComponent",
        "name": "consistency_analysis",
        "dependencies": ["database", "doc_relationships", "metadata_extraction"]
    },
    
    # Recommendation generator component
    {
        "import_path": "dbp.recommendation_generator.component",
        "component_class": "RecommendationGeneratorComponent",
        "name": "recommendation_generator",
        "dependencies": ["consistency_analysis", "database", "llm_coordinator"]
    },
    
    # Scheduler component
    {
        "import_path": "dbp.scheduler.component",
        "component_class": "SchedulerComponent",
        "name": "scheduler",
        "dependencies": ["config_manager", "fs_monitor", "metadata_extraction"]
    },
    
    # LLM coordinator component
    {
        "import_path": "dbp.llm_coordinator.component",
        "component_class": "LLMCoordinatorComponent",
        "name": "llm_coordinator",
        "dependencies": ["config_manager", "mcp_server"]
    },
    
    # MCP server component
    {
        "import_path": "dbp.mcp_server.component",
        "component_class": "MCPServerComponent",
        "name": "mcp_server",
        "dependencies": ["config_manager"]
    },
]
