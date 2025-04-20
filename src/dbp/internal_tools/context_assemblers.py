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
# Implements context assemblers for the various internal LLM tools. Each assembler
# is responsible for gathering the specific information (e.g., file contents,
# headers, changelogs) required as context for its corresponding LLM tool, using
# the FileAccessService.
###############################################################################
# [Source file design principles]
# - Abstract base class `ContextAssembler` defines the common interface.
# - Each concrete assembler implements the logic for gathering context specific to one tool.
# - Uses `FileAccessService` to interact with the filesystem.
# - Includes basic error handling and logging.
# - Placeholder logic used for complex parsing (header/changelog extraction).
# - Design Decision: Separate Assembler Classes (2025-04-15)
#   * Rationale: Isolates the context gathering logic for each tool, making it easier to manage and modify individual tool contexts.
#   * Alternatives considered: Single assembler with conditional logic (less modular).
###############################################################################
# [Source file constraints]
# - Depends on `FileAccessService`.
# - Placeholder logic for header/changelog extraction needs replacement with robust parsing.
# - Performance depends on filesystem access speed and the number of files accessed.
# - Assumes file paths and directory structures are consistent.
###############################################################################
# [Dependencies]
# - doc/DESIGN.md
# - doc/design/INTERNAL_LLM_TOOLS.md
# - src/dbp/internal_tools/file_access.py
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:12:30Z : Initial creation of Context Assembler classes by CodeAssistant
# * Implemented ABC and concrete assemblers with placeholder extraction logic.
###############################################################################

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import os
import re # For placeholder extraction logic

# Assuming FileAccessService is accessible
try:
    from .file_access import FileAccessService
except ImportError:
    logging.getLogger(__name__).error("Failed to import FileAccessService for ContextAssemblers.")
    # Placeholder
    class FileAccessService:
        def list_files(self, directory: str = "") -> List[str]: return []
        def read_file(self, file_path_rel: str) -> str: return ""

logger = logging.getLogger(__name__)

class ContextAssembler(ABC):
    """Abstract base class for context assemblers used by internal LLM tools."""

    def __init__(self, logger_override: Optional[logging.Logger] = None):
        """Initializes the ContextAssembler."""
        self.logger = logger_override or logger.getChild(self.__class__.__name__)
        self.logger.debug("ContextAssembler initialized.")

    @abstractmethod
    def assemble(self, parameters: Dict[str, Any], file_access: FileAccessService) -> Dict[str, Any]:
        """
        Assembles the necessary context for a specific internal LLM tool.

        Args:
            parameters: Parameters provided in the InternalToolJob, which might influence context gathering.
            file_access: An instance of FileAccessService to interact with the filesystem.

        Returns:
            A dictionary containing the assembled context data required by the tool's prompt.
        """
        pass

    def _extract_header_placeholder(self, content: str) -> Optional[str]:
        """Placeholder: Extracts the GenAI header comment block."""
        # Simple regex placeholder - replace with robust parsing if needed
        match = re.search(r"^(###############################################################################.*?###############################################################################)", content, re.DOTALL | re.MULTILINE)
        if match:
            return match.group(1)
        # Fallback: Look for common comment styles at the beginning
        lines = content.splitlines()
        header_lines = []
        for line in lines[:30]: # Check first 30 lines
             if line.strip().startswith('#') or line.strip().startswith('//') or line.strip().startswith('/*') or line.strip().startswith(' *'):
                  header_lines.append(line)
             elif header_lines: # Stop if non-comment line encountered after comments started
                  break
        return "\n".join(header_lines) if header_lines else None


    def _extract_change_history_placeholder(self, content: str) -> Optional[str]:
        """Placeholder: Extracts the '[GenAI tool change history]' section."""
        history_marker = "[GenAI tool change history]"
        start_index = content.find(history_marker)
        if start_index == -1:
            return None
        # Find the end marker (next ### block or end of file)
        end_marker = "###############################################################################"
        end_index = content.find(end_marker, start_index)
        if end_index == -1:
            return content[start_index:] # Return till end of file
        else:
            # Find the start of the end marker line
            start_of_end_line = content.rfind('\n', start_index, end_index)
            if start_of_end_line == -1: start_of_end_line = start_index # Should not happen if start_index > 0
            return content[start_index:start_of_end_line].strip()


# --- Concrete Assembler Implementations ---

class CodebaseContextAssembler(ContextAssembler):
    """Assembles context for the 'coordinator_get_codebase_context' tool."""

    def assemble(self, parameters: Dict[str, Any], file_access: FileAccessService) -> Dict[str, Any]:
        self.logger.info("Assembling context for codebase_context tool...")
        context = {}
        max_files = parameters.get("max_files", 100) # Limit number of files processed

        try:
            # Get list of all files (relative paths)
            all_files = file_access.list_files()
            context["file_list"] = all_files # Provide the full list

            # Get headers from a subset of files
            file_headers = []
            files_to_process = all_files[:max_files] # Process only a subset
            self.logger.debug(f"Processing headers for {len(files_to_process)} files (max: {max_files}).")
            for file_path_rel in files_to_process:
                try:
                    content = file_access.read_file(file_path_rel)
                    header = self._extract_header_placeholder(content)
                    if header:
                        file_headers.append({
                            "path": file_path_rel,
                            "header_content": header
                        })
                except (FileNotFoundError, IOError) as e:
                    self.logger.warning(f"Could not read file for header extraction: {file_path_rel} - {e}")
                except Exception as e:
                     self.logger.error(f"Unexpected error processing file {file_path_rel} for header: {e}", exc_info=True)

            context["file_headers"] = file_headers
            self.logger.info(f"Assembled context with {len(file_headers)} file headers.")
            return context

        except Exception as e:
            self.logger.error(f"Failed to assemble codebase context: {e}", exc_info=True)
            return {"error": "Failed to assemble codebase context"}


class CodebaseChangelogAssembler(ContextAssembler):
    """Assembles context for the 'coordinator_get_codebase_changelog_context' tool."""

    def assemble(self, parameters: Dict[str, Any], file_access: FileAccessService) -> Dict[str, Any]:
        self.logger.info("Assembling context for codebase_changelog tool...")
        context = {}
        max_files = parameters.get("max_files", 100)

        try:
            all_files = file_access.list_files()
            change_histories = []
            files_to_process = all_files[:max_files]
            self.logger.debug(f"Processing changelogs for {len(files_to_process)} files (max: {max_files}).")

            for file_path_rel in files_to_process:
                try:
                    content = file_access.read_file(file_path_rel)
                    history = self._extract_change_history_placeholder(content)
                    if history:
                        change_histories.append({
                            "path": file_path_rel,
                            "history_content": history
                        })
                except (FileNotFoundError, IOError) as e:
                    self.logger.warning(f"Could not read file for changelog extraction: {file_path_rel} - {e}")
                except Exception as e:
                     self.logger.error(f"Unexpected error processing file {file_path_rel} for changelog: {e}", exc_info=True)

            context["change_histories"] = change_histories
            self.logger.info(f"Assembled context with {len(change_histories)} changelogs.")
            return context

        except Exception as e:
            self.logger.error(f"Failed to assemble codebase changelog context: {e}", exc_info=True)
            return {"error": "Failed to assemble codebase changelog context"}


class DocumentationContextAssembler(ContextAssembler):
    """Assembles context for the 'coordinator_get_documentation_context' tool."""

    def assemble(self, parameters: Dict[str, Any], file_access: FileAccessService) -> Dict[str, Any]:
        self.logger.info("Assembling context for documentation_context tool...")
        context = {}
        doc_dir = parameters.get("doc_dir", "doc") # Configurable doc directory
        max_files = parameters.get("max_files", 50) # Limit number of doc files

        try:
            doc_files = file_access.list_files(doc_dir)
            documentation_content = []
            files_to_process = [f for f in doc_files if f.endswith(".md") and "MARKDOWN_CHANGELOG.md" not in f][:max_files]
            self.logger.debug(f"Processing content for {len(files_to_process)} documentation files (max: {max_files}).")

            for file_path_rel in files_to_process:
                try:
                    content = file_access.read_file(file_path_rel)
                    documentation_content.append({
                        "path": file_path_rel,
                        "content": content # Include full content for documentation
                    })
                except (FileNotFoundError, IOError) as e:
                    self.logger.warning(f"Could not read documentation file: {file_path_rel} - {e}")
                except Exception as e:
                     self.logger.error(f"Unexpected error processing documentation file {file_path_rel}: {e}", exc_info=True)

            context["documentation_files"] = documentation_content
            self.logger.info(f"Assembled context with {len(documentation_content)} documentation files.")
            return context

        except Exception as e:
            self.logger.error(f"Failed to assemble documentation context: {e}", exc_info=True)
            return {"error": "Failed to assemble documentation context"}


class DocumentationChangelogAssembler(ContextAssembler):
    """Assembles context for the 'coordinator_get_documentation_changelog_context' tool."""

    def assemble(self, parameters: Dict[str, Any], file_access: FileAccessService) -> Dict[str, Any]:
        self.logger.info("Assembling context for documentation_changelog tool...")
        context = {}
        doc_dir = parameters.get("doc_dir", "doc")
        max_files = parameters.get("max_files", 20) # Limit number of changelogs

        try:
            all_doc_files = file_access.list_files(doc_dir)
            changelog_content = []
            files_to_process = [f for f in all_doc_files if "MARKDOWN_CHANGELOG.md" in f][:max_files]
            self.logger.debug(f"Processing content for {len(files_to_process)} changelog files (max: {max_files}).")

            for file_path_rel in files_to_process:
                try:
                    content = file_access.read_file(file_path_rel)
                    changelog_content.append({
                        "path": file_path_rel,
                        "content": content
                    })
                except (FileNotFoundError, IOError) as e:
                    self.logger.warning(f"Could not read changelog file: {file_path_rel} - {e}")
                except Exception as e:
                     self.logger.error(f"Unexpected error processing changelog file {file_path_rel}: {e}", exc_info=True)

            context["changelog_files"] = changelog_content
            self.logger.info(f"Assembled context with {len(changelog_content)} changelog files.")
            return context

        except Exception as e:
            self.logger.error(f"Failed to assemble documentation changelog context: {e}", exc_info=True)
            return {"error": "Failed to assemble documentation changelog context"}


class ExpertAdviceContextAssembler(ContextAssembler):
    """Assembles comprehensive context for the 'coordinator_get_expert_architect_advice' tool."""

    def assemble(self, parameters: Dict[str, Any], file_access: FileAccessService) -> Dict[str, Any]:
        self.logger.info("Assembling context for expert_advice tool...")
        # This might combine context from multiple other assemblers or perform deeper analysis
        # For now, let's reuse parts of other assemblers as a placeholder

        max_code_files = parameters.get("max_code_files", 50)
        max_doc_files = parameters.get("max_doc_files", 20)
        doc_dir = parameters.get("doc_dir", "doc")

        context = {}
        try:
            all_files = file_access.list_files()
            files_to_process = all_files[:max_code_files]

            # Get file headers
            file_headers = []
            for file_path_rel in files_to_process:
                try:
                    content = file_access.read_file(file_path_rel)
                    header = self._extract_header_placeholder(content)
                    if header:
                        file_headers.append({"path": file_path_rel, "header_content": header})
                except Exception as e:
                    self.logger.warning(f"Could not process file {file_path_rel} for header: {e}")
            context["file_headers"] = file_headers

            # Get documentation content
            doc_files = file_access.list_files(doc_dir)
            documentation_content = []
            doc_files_to_process = [f for f in doc_files if f.endswith(".md")][:max_doc_files]
            for file_path_rel in doc_files_to_process:
                 try:
                      content = file_access.read_file(file_path_rel)
                      documentation_content.append({"path": file_path_rel, "content": content})
                 except Exception as e:
                      self.logger.warning(f"Could not read documentation file {file_path_rel}: {e}")
            context["documentation_files"] = documentation_content

            # Maybe add specific file contents based on query? (More advanced)
            # query = parameters.get("query")
            # if query and isinstance(query, dict) and "relevant_paths" in query:
            #    relevant_content = []
            #    for path in query["relevant_paths"]:
            #        try: relevant_content.append({"path": path, "content": file_access.read_file(path)})
            #        except: pass # Ignore errors reading specific files
            #    context["relevant_file_content"] = relevant_content

            self.logger.info("Assembled context for expert advice.")
            return context

        except Exception as e:
            self.logger.error(f"Failed to assemble expert advice context: {e}", exc_info=True)
            return {"error": "Failed to assemble expert advice context"}
