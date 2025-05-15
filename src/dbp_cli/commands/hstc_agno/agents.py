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
# This file provides imports for the core HSTC agent classes used in the Agno framework.
# It serves as a central point for accessing both the File Analyzer and Documentation Generator
# agents, promoting a clean import structure throughout the codebase.
###############################################################################
# [Source file design principles]
# - Clean imports for all agent classes
# - Maintains backward compatibility with existing imports
# - Promotes separation of concerns through modular design
###############################################################################
# [Source file constraints]
# - Must maintain compatibility with existing import patterns
# - Should avoid circular imports
###############################################################################
# [Dependencies]
# codebase:src/dbp_cli/commands/hstc_agno/file_analyzer_agent.py
# codebase:src/dbp_cli/commands/hstc_agno/documentation_generator_agent.py
###############################################################################
# [GenAI tool change history]
# 2025-05-15T14:49:00Z : Split agents into separate files by CodeAssistant
# * Moved FileAnalyzerAgent to file_analyzer_agent.py
# * Moved DocumentationGeneratorAgent to documentation_generator_agent.py
# * Updated this file to import from the new locations
# 2025-05-13T17:38:00Z : Refactored to use AbstractAgnoAgent by CodeAssistant
# * Modified agents to inherit from AbstractAgnoAgent
# * Removed duplicated code for prompt display and response processing
# * Implemented abstract methods for state management
# 2025-05-13T10:59:00Z : Added model discovery for optimal region selection by CodeAssistant
# * Integrated BedrockModelDiscovery for finding best regions for each model
# * Used get_best_regions_for_model to automatically select optimal region
# 2025-05-13T10:54:00Z : Fixed AWS credentials issue by CodeAssistant
# * Added integration with AWS client factory for proper AWS credentials
# * Used session from AWS client factory for AwsBedrock model
###############################################################################

# Import the agents from their dedicated modules
from .file_analyzer_agent import FileAnalyzerAgent
from .documentation_generator_agent import DocumentationGeneratorAgent

# Define exports for better import control
__all__ = ['FileAnalyzerAgent', 'DocumentationGeneratorAgent']
