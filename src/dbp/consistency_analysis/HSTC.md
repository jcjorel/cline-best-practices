# Hierarchical Semantic Tree Context - Consistency Analysis Module

This directory contains the consistency analysis components for the Document-Based Programming (DBP) system. It provides a framework for detecting inconsistencies between code, documentation, and configuration artifacts.

## Child Directory Summaries
*No child directories with HSTC.md files.*

## Local File Headers

### Filename 'component.py':
**Intent:** Implements the ConsistencyAnalysisComponent class, the main entry point for the consistency analysis subsystem. It conforms to the Component protocol, initializes and manages the lifecycle of its internal parts (repository, registry, engine, analyzers, reporter), registers the analyzers, and provides the public API for running analyses and managing inconsistency records.

**Design principles:**
- Conforms to the Component protocol (`src/dbp/core/component.py`).
- Encapsulates the entire consistency analysis logic.
- Declares dependencies on other components ('database', 'doc_relationships', 'metadata_extraction').
- Initializes sub-components (repository, registry, engine, etc.) in `initialize`.
- Registers concrete analyzer implementations with the `AnalysisRegistry`.
- Provides high-level methods for triggering different analysis scopes.
- Manages its own initialization state.
- Design Decision: Component Facade for Consistency Analysis (2025-04-15)
  * Rationale: Presents the consistency analysis subsystem as a single component.
  * Alternatives considered: Exposing engine/registry directly (more complex).

**Constraints:**
- Depends on the core component framework and other system components.
- Requires all helper classes within the `consistency_analysis` package.
- Assumes configuration is available via InitializationContext.
- Relies on placeholder implementations within the concrete analyzers.

**Change History:**
- 2025-04-20T01:21:25Z : Completed dependency injection refactoring
- 2025-04-20T00:09:49Z : Added dependency injection support
- 2025-04-15T10:32:00Z : Initial creation of ConsistencyAnalysisComponent

### Filename 'analyzer.py':
**Intent:** Defines the abstract base class `ConsistencyAnalyzer` and provides placeholder implementations for various specialized analyzers responsible for detecting specific types of inconsistencies (e.g., code-doc metadata, cross-references, terminology) within the DBP system.

**Design principles:**
- Abstract Base Class (`ConsistencyAnalyzer`) defines the common interface for all analyzers.
- Each concrete analyzer focuses on a specific type of consistency check.
- Analyzers declare the rules they implement via `get_rules()`.
- Analyzers implement the logic to apply their rules via `apply_rule()`.
- Placeholder implementations allow the framework to be built and tested before complex analysis logic is fully implemented.
- Design Decision: Specialized Analyzer Classes (2025-04-15)
  * Rationale: Promotes modularity and separation of concerns, making it easier to add, remove, or modify specific consistency checks.
  * Alternatives considered: Single large analyzer class (harder to maintain).

**Constraints:**
- Depends on `data_models.py` for rule and inconsistency structures.
- Concrete implementations require access to necessary components (e.g., metadata extraction, doc relationships) passed via their `apply_rule` inputs or potentially during initialization.
- Placeholder `apply_rule` methods need to be replaced with actual analysis logic.

**Change History:**
- 2025-04-16T14:11:30Z : Fixed placeholder classes for import failures
- 2025-04-15T10:30:45Z : Initial creation of analyzer classes

### Filename 'data_models.py':
**Intent:** Defines the core data structures (enums and dataclasses) used by the Consistency Analysis component. This includes representations for inconsistency types, severities, statuses, individual inconsistency records, analysis rules, and the final consistency report.

**Design principles:**
- Uses Enums for controlled vocabularies (Type, Severity, Status).
- Uses standard Python dataclasses for structured data representation.
- Defines clear fields for each data structure based on the design plan.
- Includes type hints for clarity and static analysis.

**Constraints:**
- Requires Python 3.7+ for dataclasses and Enum.
- Enum values should be kept consistent with their usage in analyzers and reports.

**Change History:**
- 2025-04-15T17:53:10Z : Fixed parameter ordering and missing import
- 2025-04-15T10:27:45Z : Initial creation of consistency analysis data models

### Filename 'engine.py':
**Intent:** Implements the RuleEngine class which orchestrates the execution of consistency checks. It leverages the AnalysisRegistry to find relevant analyzers for requested analysis types, executes the analysis by applying rules, and aggregates the results.

**Design principles:**
- Central orchestration for consistency checks
- Delegation to specialized analyzers via the registry
- Support for different analysis scopes (code_doc, doc_doc, full_project)
- Flexible input handling based on analysis type
- Design Decision: Rule Engine Pattern (2025-04-15)
  * Rationale: Separates orchestration from implementation details
  * Alternatives considered: Embedded analysis logic within component

**Constraints:**
- Depends on AnalysisRegistry for analyzer lookup
- Assumes analyzers handle their own dependencies
- Must handle partial analyzer failures gracefully

**Change History:**
- 2025-04-15T21:18:00Z : Enhanced error handling and reporting
- 2025-04-15T16:42:30Z : Added rule selection optimization
- 2025-04-15T10:33:15Z : Initial implementation of RuleEngine

### Filename 'registry.py':
**Intent:** Implements the AnalysisRegistry class that manages the collection of available ConsistencyAnalyzer implementations. Provides methods to register analyzers and find appropriate analyzers for specific rule types or analysis types.

**Design principles:**
- Central registry for all consistency analyzers
- Simple registration and lookup interface
- Support for finding analyzers by rule_id or analysis_type
- Thread-safe implementation for concurrent access
- Design Decision: Registry Pattern (2025-04-15)
  * Rationale: Provides dynamic discovery of analyzers without tight coupling
  * Alternatives considered: Direct instantiation (less flexible)

**Constraints:**
- Analyzers must conform to ConsistencyAnalyzer interface
- Rule IDs must be unique across all analyzers
- Registry must be thread-safe for concurrent analysis

**Change History:**
- 2025-04-16T11:35:00Z : Added analyzer validation on registration
- 2025-04-15T17:40:30Z : Enhanced thread safety with RLock
- 2025-04-15T10:32:30Z : Initial implementation of AnalysisRegistry

### Filename 'repository.py':
**Intent:** Implements the InconsistencyRepository class which provides persistent storage and retrieval for inconsistency records. It bridges between the consistency analysis system and the database layer, handling CRUD operations and query filtering.

**Design principles:**
- Abstracts database operations for inconsistency records
- Provides filtering capabilities for flexible queries
- Handles data conversion between domain objects and database models
- Thread-safe database access with proper connection management
- Design Decision: Repository Pattern (2025-04-15)
  * Rationale: Separates domain logic from data persistence concerns
  * Alternatives considered: Direct database access (less abstraction)

**Constraints:**
- Depends on DatabaseManager for database access
- Must handle database exceptions gracefully
- Requires appropriate indexes for efficient filtering

**Change History:**
- 2025-04-17T09:24:00Z : Added batch saving capability for performance
- 2025-04-16T14:35:45Z : Enhanced filtering with pagination support
- 2025-04-15T10:34:00Z : Initial implementation of InconsistencyRepository

### Filename 'report_generator.py':
**Intent:** Implements the ReportGenerator class responsible for creating structured ConsistencyReport objects from collections of InconsistencyRecord objects. It aggregates statistics, groups results, and formats data for presentation.

**Design principles:**
- Focused on report generation and formatting
- Aggregates metrics and statistics from raw inconsistency data
- Supports customizable report formats and grouping options
- Clean separation from analysis logic
- Design Decision: Dedicated Report Generator (2025-04-15)
  * Rationale: Separates analysis from presentation concerns
  * Alternatives considered: Embedded reporting in component (less flexible)

**Constraints:**
- Works with InconsistencyRecord objects from any source
- Must handle large numbers of records efficiently
- Should not modify the original inconsistency records

**Change History:**
- 2025-04-16T16:12:30Z : Added markdown and JSON export capabilities
- 2025-04-15T14:56:00Z : Enhanced summary statistics with severity breakdowns
- 2025-04-15T10:34:45Z : Initial implementation of ReportGenerator

### Filename 'impact_analyzer.py':
**Intent:** Implements the ConsistencyImpactAnalyzer class that evaluates the potential impact of detected inconsistencies on the broader system. It analyzes document relationships and dependency graphs to determine the scope of effects from each inconsistency.

**Design principles:**
- Enhances inconsistency records with impact assessments
- Leverages document relationships to trace potential effects
- Assigns impact scores based on severity and relationship depth
- Focuses on document relationships rather than code dependencies
- Design Decision: Impact Analysis as Post-Processing (2025-04-15)
  * Rationale: Allows base analysis to complete quickly before detailed impact analysis
  * Alternatives considered: Integrated impact analysis (slower initial results)

**Constraints:**
- Depends on DocRelationshipsComponent for relationship data
- Should not modify original inconsistency details, only add metadata
- May be computationally intensive for large relationship graphs

**Change History:**
- 2025-04-16T11:24:30Z : Added recursive relationship traversal with depth limit
- 2025-04-15T17:03:45Z : Enhanced impact scoring algorithm with configurable weights
- 2025-04-15T10:35:15Z : Initial implementation of ConsistencyImpactAnalyzer
