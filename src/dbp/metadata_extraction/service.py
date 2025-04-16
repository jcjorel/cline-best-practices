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
# Implements the MetadataExtractionService class, which orchestrates the end-to-end
# process of extracting metadata from a given source file. It utilizes the
# LLMPromptManager, BedrockClient, ResponseParser, ExtractionResultProcessor,
# and DatabaseWriter to perform the extraction and persistence workflow.
###############################################################################
# [Source file design principles]
# - Acts as a facade for the metadata extraction subsystem.
# - Coordinates interactions between the various helper classes (prompt, client, parser, processor, writer).
# - Handles the overall workflow for extracting metadata for a single file.
# - Includes error handling and logging for the extraction process.
# - Ensures thread safety for concurrent extraction requests if necessary (using a lock).
# - Design Decision: Service Facade Pattern (2025-04-15)
#   * Rationale: Provides a simple, unified interface for metadata extraction, hiding the complexity of the underlying components.
#   * Alternatives considered: Exposing individual components directly (more complex for clients).
###############################################################################
# [Source file constraints]
# - Depends on all other classes within the `metadata_extraction` package and the `DatabaseWriter`.
# - Requires instances of its dependencies to be injected during initialization.
# - Assumes configuration is provided for underlying components.
# - Overall performance depends on the combined performance of its dependencies (especially LLM invocation).
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - All other files in src/dbp/metadata_extraction/
###############################################################################
# [GenAI tool change history]
# 2025-04-16T12:25:00Z : Updated service to use the new LLMPromptManager by Cline
# * Changed import to use the centralized LLM prompt manager from src/dbp/llm
# * Updated extract_and_store to use format_prompt method with the new template
# * Fixed exception handling to use PromptLoadError instead of TemplateLoadError
# 2025-04-15T09:53:45Z : Initial creation of MetadataExtractionService by CodeAssistant
# * Implemented the main extraction workflow coordinating helper classes.
###############################################################################

import logging
import threading
import os
from typing import Optional, Any

# Assuming imports from the same package and database writer
try:
    from ..llm import LLMPromptManager, PromptLoadError
    from .bedrock_client import BedrockClient, BedrockInvocationError, BedrockClientInitializationError
    from .response_parser import ResponseParser, ResponseParsingError, ResponseValidationError
    from .result_processor import ExtractionResultProcessor, ExtractionProcessingError
    from .database_writer import DatabaseWriter, DatabaseWriteError
    from .data_structures import FileMetadata
    # Import config type if defined, else use Any
    # from ..config import AppConfig # Example
    Config = Any
except ImportError as e:
    logging.getLogger(__name__).error(f"MetadataExtractionService ImportError: {e}. Check package structure.", exc_info=True)
    # Define placeholders
    LLMPromptManager = object
    BedrockClient = object
    ResponseParser = object
    ExtractionResultProcessor = object
    DatabaseWriter = object
    FileMetadata = object
    Config = object
    PromptLoadError = Exception
    BedrockInvocationError = Exception
    BedrockClientInitializationError = Exception
    ResponseParsingError = Exception
    ResponseValidationError = Exception
    ExtractionProcessingError = Exception
    DatabaseWriteError = Exception


logger = logging.getLogger(__name__)

class MetadataExtractionService:
    """
    Service layer responsible for orchestrating the metadata extraction process for a file.
    """

    def __init__(
        self,
        prompt_manager: LLMPromptManager,
        bedrock_client: BedrockClient,
        response_parser: ResponseParser,
        result_processor: ExtractionResultProcessor,
        db_writer: DatabaseWriter,
        config: Config, # Pass the relevant part of the config if possible
        logger_override: Optional[logging.Logger] = None
    ):
        """
        Initializes the MetadataExtractionService.

        Args:
            prompt_manager: Instance of LLMPromptManager.
            bedrock_client: Instance of BedrockClient.
            response_parser: Instance of ResponseParser.
            result_processor: Instance of ExtractionResultProcessor.
            db_writer: Instance of DatabaseWriter.
            config: Configuration object.
            logger_override: Optional logger instance.
        """
        self.prompt_manager = prompt_manager
        self.bedrock_client = bedrock_client
        self.response_parser = response_parser
        self.result_processor = result_processor
        self.db_writer = db_writer
        self.config = config # Store config if needed for service-level decisions
        self.logger = logger_override or logger
        self._lock = threading.RLock() # Lock for potential future concurrent use
        self.logger.debug("MetadataExtractionService initialized.")

    def extract_and_store(self, file_path: str, file_content: str, project_id: int) -> Optional[FileMetadata]:
        """
        Performs the complete metadata extraction and storage workflow for a single file.

        Args:
            file_path: The absolute path to the source file.
            file_content: The content of the source file.
            project_id: The ID of the project this file belongs to.

        Returns:
            The processed FileMetadata object if successful, otherwise None.
        """
        self.logger.info(f"Starting metadata extraction for: {file_path}")
        # Using a lock here if the service instance might be called concurrently
        # For single-threaded background processing, it might not be strictly necessary
        # but provides safety if the usage pattern changes.
        with self._lock:
            metadata: Optional[FileMetadata] = None
            try:
                # 1. Create Prompt using the new format_prompt method
                _, extension = os.path.splitext(file_path)
                prompt = self.prompt_manager.format_prompt(
                    "metadata_extraction", 
                    file_path=file_path,
                    file_extension=extension,
                    file_content=file_content
                )

                # 2. Invoke LLM
                llm_response = self.bedrock_client.invoke_model(prompt)

                # 3. Parse Response
                parsed_response = self.response_parser.parse(llm_response, file_path)

                # 4. Process Result into FileMetadata object
                metadata = self.result_processor.process(parsed_response, file_path, file_content)

                # 5. Write to Database
                # Pass project_id for correct association
                write_success = self.db_writer.write(metadata, project_id)
                if not write_success:
                    # Error is logged within db_writer, but we might want to raise or handle here
                    self.logger.error(f"Database write failed for {file_path}, but processing completed.")
                    # Depending on requirements, maybe return metadata anyway or return None
                    # Returning metadata allows caller to know extraction worked, even if DB failed.
                    # return metadata # Option 1: Return metadata despite DB error
                    return None # Option 2: Return None if DB write fails

                self.logger.info(f"Successfully extracted and stored metadata for: {file_path}")
                return metadata

            # Handle specific exceptions from each step
            except PromptLoadError as e: # Prompt loading errors
                self.logger.error(f"Prompt template loading failed for {file_path}: {e}", exc_info=True)
                return None
            except ValueError as e: # Other prompt creation errors
                self.logger.error(f"Prompt creation failed for {file_path}: {e}", exc_info=True)
                return None
            except BedrockInvocationError as e: # LLM invocation errors
                self.logger.error(f"Bedrock invocation failed for {file_path}: {e}", exc_info=True)
                return None
            except (ResponseParsingError, ResponseValidationError) as e: # Parsing/Validation errors
                self.logger.error(f"LLM response parsing/validation failed for {file_path}: {e}", exc_info=True)
                return None
            except ExtractionProcessingError as e: # Result processing errors
                self.logger.error(f"Metadata processing failed for {file_path}: {e}", exc_info=True)
                return None
            # DatabaseWriteError is handled above by checking write_success
            except Exception as e: # Catch any other unexpected errors
                self.logger.critical(f"Unexpected critical error during metadata extraction for {file_path}: {e}", exc_info=True)
                return None
