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
# Implements the InternalToolExecutionEngine class, which is responsible for
# executing the specific logic of each internal LLM tool. It coordinates the
# context assembly, LLM invocation (using the appropriate instance), response
# parsing, and result formatting for each tool type.
###############################################################################
# [Source file design principles]
# - Provides distinct methods for executing each internal tool.
# - Injects dependencies for context assemblers, LLM instances, parsers, and formatters.
# - Orchestrates the step-by-step execution flow for a given tool job.
# - Includes error handling for each step of the tool execution process.
# - Placeholder methods return mock data until full implementation.
# - Design Decision: Central Execution Engine (2025-04-15)
#   * Rationale: Consolidates the execution logic for all internal tools, making it easier to manage the workflow and dependencies.
#   * Alternatives considered: Implementing execution logic within each tool's definition (less organized), Direct calls from JobManager (mixes concerns).
###############################################################################
# [Source file constraints]
# - Requires instances of all assemblers, LLM interfaces, parsers, and formatters.
# - Placeholder methods need to be replaced with actual logic involving dependency calls.
# - Error handling needs to be robust to failures in any step (context, LLM, parsing, formatting).
# - Needs access to configuration for LLM parameters (passed via job or config).
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - doc/design/INTERNAL_LLM_TOOLS.md
# - All other files in src/dbp/internal_tools/
# - src/dbp/llm_coordinator/data_models.py (InternalToolJob)
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:15:10Z : Initial creation of InternalToolExecutionEngine by CodeAssistant
# * Implemented placeholder methods for executing each internal tool.
###############################################################################

import logging
from typing import Dict, Any, Optional

# Assuming necessary imports - adjust paths as needed
try:
    from .context_assemblers import (
        CodebaseContextAssembler, CodebaseChangelogAssembler,
        DocumentationContextAssembler, DocumentationChangelogAssembler,
        ExpertAdviceContextAssembler
    )
    from .llm_interface import NovaLiteInstance, ClaudeInstance
    from .response_handlers import (
        CodebaseContextParser, CodebaseContextFormatter,
        CodebaseChangelogParser, CodebaseChangelogFormatter,
        DocumentationContextParser, DocumentationContextFormatter,
        DocumentationChangelogParser, DocumentationChangelogFormatter,
        ExpertAdviceParser, ExpertAdviceFormatter
    )
    from .file_access import FileAccessService
    from .prompt_loader import PromptLoader
    from ..llm_coordinator.data_models import InternalToolJob # For type hinting
    # Import config type if defined
    # from ...config import InternalToolsConfig # Example
    InternalToolsConfig = Any # Placeholder
except ImportError as e:
    logging.getLogger(__name__).error(f"InternalToolExecutionEngine ImportError: {e}. Check package structure.", exc_info=True)
    # Placeholders
    CodebaseContextAssembler, CodebaseChangelogAssembler = object, object
    DocumentationContextAssembler, DocumentationChangelogAssembler = object, object
    ExpertAdviceContextAssembler = object
    NovaLiteInstance, ClaudeInstance = object, object
    CodebaseContextParser, CodebaseContextFormatter = object, object
    CodebaseChangelogParser, CodebaseChangelogFormatter = object, object
    DocumentationContextParser, DocumentationContextFormatter = object, object
    DocumentationChangelogParser, DocumentationChangelogFormatter = object, object
    ExpertAdviceParser, ExpertAdviceFormatter = object, object
    FileAccessService = object
    PromptLoader = object
    InternalToolJob = object
    InternalToolsConfig = object


logger = logging.getLogger(__name__)

class InternalToolError(Exception):
    """Custom exception for errors during internal tool execution."""
    pass

class InternalToolExecutionEngine:
    """
    Orchestrates the execution of specific internal LLM tools by coordinating
    context assembly, LLM invocation, parsing, and formatting.
    """

    def __init__(self, config: InternalToolsConfig, logger_override: Optional[logging.Logger] = None):
        """
        Initializes the InternalToolExecutionEngine.

        Args:
            config: Configuration object for internal tools.
            logger_override: Optional logger instance.
        """
        self.config = config or {}
        self.logger = logger_override or logger

        # Instantiate necessary services/helpers (or receive them via injection)
        # These might be better managed by the main component and passed in,
        # but creating them here for simplicity based on the plan structure.
        self.file_access = FileAccessService(logger_override=self.logger.getChild("file_access"))
        # Assuming prompt dir comes from coordinator config or needs separate config key
        prompt_dir = self.config.get('prompt_templates_dir', 'doc/llm/prompts')
        self.prompt_loader = PromptLoader(prompt_dir=prompt_dir, logger_override=self.logger.getChild("prompt_loader"))

        # Context Assemblers
        self.codebase_context_assembler = CodebaseContextAssembler(logger_override=self.logger.getChild("asm_code_ctx"))
        self.codebase_changelog_assembler = CodebaseChangelogAssembler(logger_override=self.logger.getChild("asm_code_log"))
        self.documentation_context_assembler = DocumentationContextAssembler(logger_override=self.logger.getChild("asm_doc_ctx"))
        self.documentation_changelog_assembler = DocumentationChangelogAssembler(logger_override=self.logger.getChild("asm_doc_log"))
        self.expert_advice_assembler = ExpertAdviceContextAssembler(logger_override=self.logger.getChild("asm_expert"))

        # LLM Instances (using placeholders for now)
        self.nova_lite_instance = NovaLiteInstance(config=self.config.get('nova_lite',{}), logger_override=self.logger.getChild("nova_lite"))
        self.claude_instance = ClaudeInstance(config=self.config.get('claude',{}), logger_override=self.logger.getChild("claude"))

        # Response Parsers
        self.codebase_context_parser = CodebaseContextParser(logger_override=self.logger.getChild("parse_code_ctx"))
        self.codebase_changelog_parser = CodebaseChangelogParser(logger_override=self.logger.getChild("parse_code_log"))
        self.documentation_context_parser = DocumentationContextParser(logger_override=self.logger.getChild("parse_doc_ctx"))
        self.documentation_changelog_parser = DocumentationChangelogParser(logger_override=self.logger.getChild("parse_doc_log"))
        self.expert_advice_parser = ExpertAdviceParser(logger_override=self.logger.getChild("parse_expert"))

        # Result Formatters
        self.codebase_context_formatter = CodebaseContextFormatter(logger_override=self.logger.getChild("fmt_code_ctx"))
        self.codebase_changelog_formatter = CodebaseChangelogFormatter(logger_override=self.logger.getChild("fmt_code_log"))
        self.documentation_context_formatter = DocumentationContextFormatter(logger_override=self.logger.getChild("fmt_doc_ctx"))
        self.documentation_changelog_formatter = DocumentationChangelogFormatter(logger_override=self.logger.getChild("fmt_doc_log"))
        self.expert_advice_formatter = ExpertAdviceFormatter(logger_override=self.logger.getChild("fmt_expert"))

        self.logger.debug("InternalToolExecutionEngine initialized.")

    # --- Tool Execution Methods ---

    def execute_codebase_context_tool(self, job: InternalToolJob) -> Dict[str, Any]:
        """Executes the 'coordinator_get_codebase_context' tool."""
        self.logger.info(f"Executing tool '{job.tool_name}' for job ID: {job.job_id}")
        try:
            # 1. Assemble Context
            context = self.codebase_context_assembler.assemble(job.parameters, self.file_access)
            # 2. Create Prompt
            prompt_template = self.prompt_loader.load_prompt("coordinator_get_codebase_context.txt")
            prompt = prompt_template.format(query=job.parameters.get("query",""), **context) # Format with assembled context
            # 3. Invoke LLM
            response_text = self.nova_lite_instance.invoke(prompt) # Add params if needed
            # 4. Parse Response
            parsed_data = self.codebase_context_parser.parse(response_text)
            # 5. Format Result
            result = self.codebase_context_formatter.format(parsed_data)
            return result
        except Exception as e:
            self.logger.error(f"Error executing tool '{job.tool_name}': {e}", exc_info=True)
            raise InternalToolError(f"Execution failed for {job.tool_name}") from e

    def execute_codebase_changelog_tool(self, job: InternalToolJob) -> Dict[str, Any]:
        """Executes the 'coordinator_get_codebase_changelog_context' tool."""
        self.logger.info(f"Executing tool '{job.tool_name}' for job ID: {job.job_id}")
        try:
            context = self.codebase_changelog_assembler.assemble(job.parameters, self.file_access)
            prompt_template = self.prompt_loader.load_prompt("coordinator_get_codebase_changelog_context.txt")
            prompt = prompt_template.format(query=job.parameters.get("query",""), **context)
            response_text = self.nova_lite_instance.invoke(prompt)
            parsed_data = self.codebase_changelog_parser.parse(response_text)
            result = self.codebase_changelog_formatter.format(parsed_data)
            return result
        except Exception as e:
            self.logger.error(f"Error executing tool '{job.tool_name}': {e}", exc_info=True)
            raise InternalToolError(f"Execution failed for {job.tool_name}") from e

    def execute_documentation_context_tool(self, job: InternalToolJob) -> Dict[str, Any]:
        """Executes the 'coordinator_get_documentation_context' tool."""
        self.logger.info(f"Executing tool '{job.tool_name}' for job ID: {job.job_id}")
        try:
            context = self.documentation_context_assembler.assemble(job.parameters, self.file_access)
            prompt_template = self.prompt_loader.load_prompt("coordinator_get_documentation_context.txt")
            prompt = prompt_template.format(query=job.parameters.get("query",""), **context)
            response_text = self.nova_lite_instance.invoke(prompt)
            parsed_data = self.documentation_context_parser.parse(response_text)
            result = self.documentation_context_formatter.format(parsed_data)
            return result
        except Exception as e:
            self.logger.error(f"Error executing tool '{job.tool_name}': {e}", exc_info=True)
            raise InternalToolError(f"Execution failed for {job.tool_name}") from e

    def execute_documentation_changelog_tool(self, job: InternalToolJob) -> Dict[str, Any]:
        """Executes the 'coordinator_get_documentation_changelog_context' tool."""
        self.logger.info(f"Executing tool '{job.tool_name}' for job ID: {job.job_id}")
        try:
            context = self.documentation_changelog_assembler.assemble(job.parameters, self.file_access)
            prompt_template = self.prompt_loader.load_prompt("coordinator_get_documentation_changelog_context.txt")
            prompt = prompt_template.format(query=job.parameters.get("query",""), **context)
            response_text = self.nova_lite_instance.invoke(prompt)
            parsed_data = self.documentation_changelog_parser.parse(response_text)
            result = self.documentation_changelog_formatter.format(parsed_data)
            return result
        except Exception as e:
            self.logger.error(f"Error executing tool '{job.tool_name}': {e}", exc_info=True)
            raise InternalToolError(f"Execution failed for {job.tool_name}") from e

    def execute_expert_architect_advice_tool(self, job: InternalToolJob) -> Dict[str, Any]:
        """Executes the 'coordinator_get_expert_architect_advice' tool."""
        self.logger.info(f"Executing tool '{job.tool_name}' for job ID: {job.job_id}")
        try:
            context = self.expert_advice_assembler.assemble(job.parameters, self.file_access)
            prompt_template = self.prompt_loader.load_prompt("coordinator_get_expert_architect_advice.txt")
            prompt = prompt_template.format(query=job.parameters.get("query",""), **context)
            response_text = self.claude_instance.invoke(prompt) # Use Claude instance
            parsed_data = self.expert_advice_parser.parse(response_text)
            result = self.expert_advice_formatter.format(parsed_data)
            return result
        except Exception as e:
            self.logger.error(f"Error executing tool '{job.tool_name}': {e}", exc_info=True)
            raise InternalToolError(f"Execution failed for {job.tool_name}") from e
