# Markdown Documentation Changelog

This file tracks all changes made to documentation markdown files in this directory.

2025-04-15T21:43:00Z : [DOCUMENT_RELATIONSHIPS.md] Updated document relationships to include the new design decision about Default Network Binding
2025-04-15T21:42:00Z : [DESIGN_DECISIONS.md] Added design decision: Default Network Binding to 127.0.0.1 for security reasons
2025-04-15T00:59:00Z : [DATA_MODEL.md, DESIGN.md, PR-FAQ.md, WORKING_BACKWARDS.md, design/COMPONENT_INITIALIZATION.md] Removed references to FIFO recommendation management to reflect the simplified recommendation system
2025-04-15T00:12:03Z : [DOCUMENT_RELATIONSHIPS.md] Updated document relationships to include the new design decisions about LLM-Based Metadata Extraction, External Prompt Template Files, and LLM-Based Language Detection
2025-04-15T00:08:29Z : [DESIGN_DECISIONS.md] Added three new design decisions: LLM-Based Metadata Extraction, External Prompt Template Files, and LLM-Based Language Detection
2025-04-14T20:57:00Z : [DESIGN_DECISIONS.md] Cleaned file by removing implemented "Simplified Recommendation System" design decision
2025-04-14T19:55:41Z : [DESIGN.md] Updated file structure and recommendation workflow sections to implement simplified recommendation system
2025-04-14T19:55:41Z : [DATA_MODEL.md] Updated recommendation data model and generation process for simplified single-recommendation approach
2025-04-14T19:55:41Z : [DESIGN_DECISIONS.md] Added "Simplified Recommendation System" design decision
2025-04-14T19:40:00Z : [DOCUMENT_RELATIONSHIPS.md] Added relationships for the new Component Initialization design document
2025-04-14T19:38:00Z : [design/COMPONENT_INITIALIZATION.md] Created new design document for Component Initialization Sequence
2025-04-14T19:24:00Z : [design/INTERNAL_LLM_TOOLS.md] Added prompt template management design rationale
2025-04-14T19:20:00Z : [SECURITY.md] Added MCP client security design rationale
2025-04-14T19:16:00Z : [CONFIGURATION.md] Added configuration strategy design rationale
2025-04-14T19:13:00Z : [DESIGN.md] Enhanced implementation principles with design rationales
2025-04-14T19:10:00Z : [DATA_MODEL.md] Added database architecture decision details and MD5 digest rationale
2025-04-14T19:05:15Z : [design/MCP_SERVER_ENHANCED_DATA_MODEL.md] Added references to prompt templates and improved connection to LLM architecture
2025-04-14T19:03:19Z : [design/LLM_COORDINATION.md] Added references to prompt templates and connection to INTERNAL_LLM_TOOLS.md
2025-04-14T19:02:22Z : [design/INTERNAL_LLM_TOOLS.md] Added links to prompt templates for each tool
2025-04-14T18:56:26Z : [SECURITY.md] Added MCP client security information
2025-04-14T18:54:05Z : [CONFIGURATION.md] Updated configuration overview and added database type and recommendation lifecycle settings
2025-04-14T18:51:03Z : [DESIGN.md] Updated core architecture principles and added implementation principles section
2025-04-14T18:49:02Z : [DATA_MODEL.md] Updated database implementation for PostgreSQL/SQLite support, MD5 digest storage, and 7-day purge policy
2025-04-14T18:45:13Z : [DOCUMENT_RELATIONSHIPS.md] Updated relationships to include LLM prompt templates directory
2025-04-14T18:43:13Z : [llm/prompts/coordinator_get_expert_architect_advice.md] Created expert architect advice prompt template
2025-04-14T18:40:46Z : [llm/prompts/coordinator_get_documentation_changelog_context.md] Created documentation changelog context prompt template
2025-04-14T18:39:55Z : [llm/prompts/coordinator_get_codebase_changelog_context.md] Created codebase changelog context prompt template
2025-04-14T18:39:16Z : [llm/prompts/coordinator_get_documentation_context.md] Created documentation context prompt template
2025-04-14T18:38:21Z : [llm/prompts/coordinator_get_codebase_context.md] Created codebase context prompt template
2025-04-14T18:37:41Z : [llm/prompts/README.md] Created readme for LLM prompt templates
2025-04-14T18:33:40Z : [DESIGN_DECISIONS.md] Added architecture and implementation decisions for database, configuration, recommendations, code structure, LLM processing, prompt templates, metadata extraction, MCP client security, and implementation principles
2025-04-14T13:36:36Z : [DOCUMENT_RELATIONSHIPS.md] Added relationships for the new Background Task Scheduler design document
2025-04-14T13:35:52Z : [DATA_MODEL.md] Updated metadata extraction model to reference Amazon Nova Lite instead of Claude 3.7 Sonnet
2025-04-14T13:35:05Z : [CONFIGURATION.md] Added configuration parameters for the Background Task Scheduler component
2025-04-14T13:34:06Z : [DESIGN.md] Enhanced Documentation Monitoring section with Background Task Scheduler information
2025-04-14T13:32:09Z : [design/BACKGROUND_TASK_SCHEDULER.md] Created new design document for the Background Task Scheduler component
2025-04-14T13:23:33Z : [DOCUMENT_RELATIONSHIPS.md] Updated relationships for design/ directory documents
2025-04-14T13:22:45Z : [design/MCP_SERVER_ENHANCED_DATA_MODEL.md] Created new file documenting enhanced MCP server data models
2025-04-14T13:19:48Z : [design/INTERNAL_LLM_TOOLS.md] Created new file documenting internal LLM tools
2025-04-14T13:18:11Z : [design/LLM_COORDINATION.md] Created new file documenting LLM coordination architecture
2025-04-14T12:55:00Z : [DESIGN.md] Updated MCP Server Implementation section with LLM coordination details
2025-04-14T09:21:30Z : [DESIGN.md] Added Dynamic File Exclusion Strategy section
2025-04-14T09:06:14Z : [WORKING_BACKWARDS.md] Replaced specific LLM references with generic AI terminology
2025-04-14T09:03:27Z : [PR-FAQ.md] Replaced specific LLM references with generic AI terminology
2025-04-14T08:57:05Z : [WORKING_BACKWARDS.md] Updated to reflect SQLite database usage and fixed inconsistencies
2025-04-14T08:47:38Z : [PR-FAQ.md] Updated programming language analysis description to align with DESIGN.md
2025-04-14T01:46:50Z : [PR-FAQ.md] Updated documentation to accurately reflect SQLite database usage and added related documentation section
2025-04-14T01:38:33Z : [DOCUMENT_RELATIONSHIPS.md] Added SECURITY.md to documentation relationships and updated relationship graph
2025-04-14T01:37:22Z : [DESIGN.md] Updated Security and Data Handling section to reference SECURITY.md
2025-04-14T01:36:34Z : [SECURITY.md] Created new file with comprehensive security documentation
2025-04-14T01:12:17Z : [DATA_MODEL.md] Added background task progress to dbp_commit_message responses
2025-04-14T01:11:46Z : [DATA_MODEL.md] Added background task progress to dbp_general_query responses
2025-04-14T01:10:55Z : [DESIGN.md] Added background processing details to Documentation Monitoring component
2025-04-14T00:56:48Z : [DATA_MODEL.md] Added MCP Server Tool Data Model with time measurements in milliseconds
2025-04-14T00:47:31Z : [DESIGN.md] Added MCP Server Implementation section with tool descriptions
2025-04-14T00:23:49Z : [DOCUMENT_RELATIONSHIPS.md] Updated relationship graph to include CONFIGURATION.md
2025-04-14T00:19:00Z : [DOCUMENT_RELATIONSHIPS.md] Added CONFIGURATION.md to core documentation relationships
2025-04-14T00:18:25Z : [CONFIGURATION.md] Created new file with configuration parameters
2025-04-14T00:15:37Z : [DATA_MODEL.md] Added port configuration (default: 6231) to MCP server connection model
2025-04-14T00:13:57Z : [DESIGN.md] Updated Documentation Monitoring response time to clarify 10-second configurable delay
2025-04-14T00:13:27Z : [DESIGN.md] Updated Python CLI Client to note default MCP server port and Cline configuration
2025-04-14T00:07:34Z : [DOCUMENT_RELATIONSHIPS.md] Added Python CLI Client dependency relationship
2025-04-14T00:06:48Z : [DATA_MODEL.md] Added MCP CLI Client data model documentation
2025-04-14T00:06:01Z : [DESIGN.md] Added Python CLI Client component to system architecture

2025-04-13T23:46:34Z : [DATA_MODEL.md] Merged "Persistent SQLite Database for Metadata Storage" design decision
2025-04-13T23:46:34Z : [DESIGN.md] Updated Documentation Monitoring component with SQLite database design decision
2025-04-13T23:46:34Z : [DESIGN.md] Updated Security and Data Handling section to reflect SQLite database persistence
2025-04-13T23:46:34Z : [DESIGN_DECISIONS.md] Cleared content after merging decisions into appropriate files
2025-04-13T23:40:31Z : [DESIGN_DECISIONS.md] Added "Persistent SQLite Database for Metadata Storage" design decision
2025-04-13T23:32:30Z : [DESIGN.md] Merged design decisions into relevant component sections
2025-04-13T21:26:53Z : [DOCUMENT_RELATIONSHIPS.md] Updated document relationships after merging DESIGN_DECISIONS.md content
2025-04-13T21:17:16Z : [DESIGN.md] Added "Process Only One Codebase File at a Time During Background Tasks" design decision from DESIGN_DECISIONS.md
2025-04-13T21:17:16Z : [DESIGN_DECISIONS.md] Cleared content after merging decision into DESIGN.md
