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
from .prompts import LLMPromptManager, TemplateLoadError
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
