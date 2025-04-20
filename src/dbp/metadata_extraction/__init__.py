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
# Metadata Extraction package for the Documentation-Based Programming system.
# Provides functionality to extract metadata from code and documentation files.
###############################################################################
# [Source file design principles]
# - Exports only the essential classes and functions needed by other components
# - Maintains a clean public API with implementation details hidden
# - Uses explicit imports rather than wildcard imports
###############################################################################
# [Source file constraints]
# - Must avoid circular imports
# - Should maintain backward compatibility for public interfaces
###############################################################################
# [Dependencies]
# - doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T21:58:23Z : Added GenAI header to comply with documentation standards by CodeAssistant
# * Added complete header template with appropriate sections
# 2025-04-16T14:10:50Z : Fixed import path for LLMPromptManager by CodeAssistant
# * Changed import from local prompts module to centralized llm.prompt_manager
# * Added PromptLoadError import with alias to maintain backward compatibility
###############################################################################


# src/dbp/metadata_extraction/__init__.py

"""
Metadata Extraction package for the Documentation-Based Programming system.

Handles the extraction of structured metadata (header sections, functions, classes,
documentation) from source code files using LLMs (e.g., Amazon Nova Lite via Bedrock).

Key components:
- MetadataExtractionComponent: The main component conforming to the core framework.
- MetadataExtractionService: Orchestrates the extraction workflow.
- LLMPromptManager: Manages prompts for the LLM.
- BedrockClient: Interacts with the AWS Bedrock service.
- ResponseParser: Parses the LLM's response.
- ExtractionResultProcessor: Transforms parsed data into structured FileMetadata.
- DatabaseWriter: Persists extracted metadata to the database.
- data_structures: Defines Pydantic models for the extracted metadata.
"""

# Expose key classes for easier import
from .data_structures import FileMetadata
from .service import MetadataExtractionService
from .component import MetadataExtractionComponent, ComponentNotInitializedError
from ..llm.prompt_manager import LLMPromptManager, PromptLoadError as TemplateLoadError
from .bedrock_client import BedrockClient, BedrockInvocationError, BedrockClientInitializationError
from .response_parser import ResponseParser, ResponseParsingError, ResponseValidationError
from .result_processor import ExtractionResultProcessor, ExtractionProcessingError
from .database_writer import DatabaseWriter, DatabaseWriteError


__all__ = [
    "MetadataExtractionComponent",
    "MetadataExtractionService",
    "FileMetadata",
    "ComponentNotInitializedError",
    # Expose helper classes if they might be needed externally, otherwise keep internal
    "LLMPromptManager",
    "BedrockClient",
    "ResponseParser",
    "ExtractionResultProcessor",
    "DatabaseWriter",
    # Expose custom exceptions
    "TemplateLoadError",
    "BedrockInvocationError",
    "BedrockClientInitializationError",
    "ResponseParsingError",
    "ResponseValidationError",
    "ExtractionProcessingError",
    "DatabaseWriteError",
]
