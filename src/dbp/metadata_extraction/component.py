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
# Implements the MetadataExtractionComponent class, which conforms to the core
# Component protocol. This component encapsulates the entire metadata extraction
# subsystem, initializing its internal services (prompt manager, Bedrock client,
# parser, processor, writer, extraction service) and providing the main interface
# for triggering metadata extraction.
###############################################################################
# [Source file design principles]
# - Conforms to the Component protocol defined in `src/dbp/core/component.py`.
# - Declares its dependencies (e.g., 'database', 'config_manager_comp').
# - Initializes all internal services during its `initialize` phase.
# - Provides a clear public method (`extract_and_store_metadata`) to perform extraction.
# - Delegates the core extraction logic to the `MetadataExtractionService`.
# - Manages its own initialization state.
# - Design Decision: Component Facade (2025-04-15)
#   * Rationale: Presents the complex metadata extraction subsystem as a single, manageable component within the application's lifecycle framework.
#   * Alternatives considered: Exposing the service directly (less aligned with the component model).
###############################################################################
# [Source file constraints]
# - Depends on the core component framework (`Component`, `InitializationContext`).
# - Depends on the centralized LLMPromptManager from src/dbp/llm package.
# - Depends on helper classes within the `metadata_extraction` package.
# - Requires dependent components (like 'database') to be registered and initialized first.
# - Assumes configuration for metadata extraction is available via the InitializationContext.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - doc/design/COMPONENT_INITIALIZATION.md
# - src/dbp/core/component.py
# - All other files in src/dbp/metadata_extraction/
###############################################################################
# [GenAI tool change history]
# 2025-04-16T12:40:00Z : Updated to use centralized LLMPromptManager by Cline
# * Switched to import LLMPromptManager from dbp.llm instead of local module
# * Removed dependency on local prompts.py module that was deprecated
# 2025-04-15T09:55:45Z : Initial creation of MetadataExtractionComponent by CodeAssistant
# * Implemented Component protocol methods and initialization of internal services.
###############################################################################

import logging
from typing import List, Optional, Any

# Core component imports
try:
    from ..core.component import Component, InitializationContext
    # Import config type if defined, else use Any
    # from ..config import AppConfig # Example
    Config = Any
except ImportError:
    logging.getLogger(__name__).error("Failed to import core component types.", exc_info=True)
    # Define placeholders
    class Component: pass
    class InitializationContext: pass
    Config = Any

# Imports for internal services
try:
    from ..llm import LLMPromptManager
    from .bedrock_client import BedrockClient
    from .response_parser import ResponseParser
    from .result_processor import ExtractionResultProcessor
    from .database_writer import DatabaseWriter
    from .service import MetadataExtractionService
    from .data_structures import FileMetadata
except ImportError as e:
    logging.getLogger(__name__).error(f"MetadataExtractionComponent ImportError: {e}. Check package structure.", exc_info=True)
    # Define placeholders
    LLMPromptManager = object
    BedrockClient = object
    ResponseParser = object
    ExtractionResultProcessor = object
    DatabaseWriter = object
    MetadataExtractionService = object
    FileMetadata = object


logger = logging.getLogger(__name__)

class ComponentNotInitializedError(Exception):
    """Exception raised when a component method is called before initialization."""
    pass

class MetadataExtractionComponent(Component):
    """
    DBP system component responsible for orchestrating the extraction of
    metadata from source code files using LLMs.
    """
    _initialized: bool = False
    _service: Optional[MetadataExtractionService] = None

    @property
    def name(self) -> str:
        """Returns the unique name of the component."""
        return "metadata_extraction"

    @property
    def dependencies(self) -> List[str]:
        """Returns the list of component names this component depends on."""
        # Depends on database for writing results and config for settings.
        # Assuming config is accessed via context, not a separate component dependency here.
        # If BedrockClient needs specific AWS config component, add it here.
        return ["database"] # Add other dependencies like 'llm_coordinator' if needed by BedrockClient indirectly

    def initialize(self, context: InitializationContext):
        """
        [Function intent]
        Initializes the metadata extraction component and its internal services.
        
        [Implementation details]
        Uses the strongly-typed configuration for component setup.
        Creates internal sub-components for metadata extraction.
        Sets the _initialized flag when initialization succeeds.
        
        [Design principles]
        Explicit initialization with strong typing.
        Type-safe configuration access.
        
        Args:
            context: Initialization context with typed configuration and resources
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

            # Get dependent components
            db_manager = context.get_component("database").get_manager() # Access manager through getter

            # Instantiate internal services, passing relevant config parts
            # TODO: Refine how config is passed (pass entire config or specific sub-sections?)
            prompt_manager = LLMPromptManager(config=context.config, logger_override=self.logger.getChild("prompts"))
            bedrock_client = BedrockClient(config=context.config, logger_override=self.logger.getChild("bedrock"))
            response_parser = ResponseParser(logger_override=self.logger.getChild("parser"))
            result_processor = ExtractionResultProcessor(logger_override=self.logger.getChild("processor"))
            db_writer = DatabaseWriter(db_manager=db_manager, logger_override=self.logger.getChild("db_writer"))

            # Instantiate the main service
            self._service = MetadataExtractionService(
                prompt_manager=prompt_manager,
                bedrock_client=bedrock_client,
                response_parser=response_parser,
                result_processor=result_processor,
                db_writer=db_writer,
                config=component_config, # Pass component-specific config to service
                logger_override=self.logger.getChild("service")
            )

            self._initialized = True
            self.logger.info(f"Component '{self.name}' initialized successfully.")

        except KeyError as e:
             self.logger.error(f"Initialization failed: Missing dependency component '{e}'. Ensure it's registered.")
             self._initialized = False
             raise RuntimeError(f"Missing dependency during {self.name} initialization: {e}") from e
        except Exception as e:
            self.logger.error(f"Initialization failed for component '{self.name}': {e}", exc_info=True)
            self._initialized = False
            # Re-raise the exception to signal failure to the orchestrator
            raise RuntimeError(f"Failed to initialize {self.name}") from e

    def shutdown(self) -> None:
        """Performs cleanup for the metadata extraction component."""
        self.logger.info(f"Shutting down component '{self.name}'...")
        # Add cleanup logic here if needed (e.g., close persistent connections if any)
        # For now, mainly relies on dependencies (like database) shutting down correctly.
        self._service = None # Release service instance
        self._initialized = False
        self.logger.info(f"Component '{self.name}' shut down.")

    @property
    def is_initialized(self) -> bool:
        """Returns True if the component is initialized, False otherwise."""
        return self._initialized

    # --- Public API Methods ---

    def extract_and_store_metadata(self, file_path: str, file_content: str, project_id: int) -> Optional[FileMetadata]:
        """
        Extracts metadata from the given file content and stores it in the database.

        This is the primary public method exposed by this component.

        Args:
            file_path: The absolute path to the source file.
            file_content: The content of the source file.
            project_id: The ID of the project this file belongs to.

        Returns:
            A FileMetadata object if extraction and storage were successful, otherwise None.

        Raises:
            ComponentNotInitializedError: If called before the component is initialized.
        """
        if not self.is_initialized or self._service is None:
            self.logger.error(f"Attempted to call extract_and_store_metadata on uninitialized component '{self.name}'.")
            raise ComponentNotInitializedError(f"Component '{self.name}' is not initialized.")

        # Delegate the actual work to the service layer
        return self._service.extract_and_store(file_path, file_content, project_id)
