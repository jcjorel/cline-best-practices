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
# Implements the ExtractionResultProcessor class, responsible for taking the
# raw, parsed dictionary output from the LLM (via ResponseParser) and transforming
# it into a validated, structured FileMetadata Pydantic object. It handles data
# cleaning, type conversion (e.g., timestamps), and calculates additional metadata
# like file size and MD5 hash.
###############################################################################
# [Source file design principles]
# - Decouples the final data structuring logic from the initial LLM response parsing.
# - Uses the Pydantic models defined in `data_structures.py` for validation and type coercion.
# - Includes helper methods for processing nested structures (headers, functions, classes).
# - Calculates supplementary metadata (size, hash, timestamps) not provided by the LLM.
# - Handles potential errors during data transformation and type conversion gracefully.
# - Design Decision: Separate Result Processor (2025-04-15)
#   * Rationale: Isolates the logic for converting the LLM's potentially variable output into the strict internal data model, making the system more robust to LLM variations.
#   * Alternatives considered: Processing directly in ResponseParser (mixes concerns), Processing in DatabaseWriter (too late in the pipeline).
###############################################################################
# [Source file constraints]
# - Depends on the Pydantic models defined in `data_structures.py`.
# - Relies on the input dictionary having the basic structure validated by `ResponseParser`.
# - Requires `hashlib` for MD5 calculation.
# - Timestamp parsing assumes ISO 8601 format from the LLM.
###############################################################################
# [Dependencies]
# - doc/DATA_MODEL.md
# - src/dbp/metadata_extraction/data_structures.py
# - src/dbp/metadata_extraction/response_parser.py
###############################################################################
# [GenAI tool change history]
# 2025-04-15T09:52:30Z : Initial creation of ExtractionResultProcessor by CodeAssistant
# * Implemented processing logic to convert parsed dict to FileMetadata model. Added helper methods.
###############################################################################

import logging
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

# Assuming data_structures.py defines the Pydantic models
try:
    from .data_structures import (
        FileMetadata, HeaderSections, ChangeRecord, DocSections,
        FunctionMetadata, ClassMetadata, LineRange
    )
except ImportError:
    # Define placeholders if run standalone or structure differs
    logging.getLogger(__name__).error("Failed to import data structures for ResultProcessor.")
    # Define dummy classes to allow class definition
    class BaseModel: pass
    class FileMetadata(BaseModel): pass
    class HeaderSections(BaseModel): pass
    class ChangeRecord(BaseModel): pass
    class DocSections(BaseModel): pass
    class FunctionMetadata(BaseModel): pass
    class ClassMetadata(BaseModel): pass
    class LineRange(BaseModel): pass


logger = logging.getLogger(__name__)

class ExtractionProcessingError(Exception):
    """Custom exception for errors during the processing of parsed LLM results."""
    pass

class ExtractionResultProcessor:
    """
    Processes the parsed dictionary output from the LLM (via ResponseParser)
    and transforms it into a validated FileMetadata Pydantic object.
    """

    def __init__(self, logger_override: Optional[logging.Logger] = None):
        """
        Initializes the ExtractionResultProcessor.

        Args:
            logger_override: Optional logger instance to use.
        """
        self.logger = logger_override or logger
        self.logger.debug("ExtractionResultProcessor initialized.")

    def process(self, parsed_response: Dict[str, Any], file_path: str, file_content: str) -> FileMetadata:
        """
        Processes the parsed LLM response dictionary into a FileMetadata object.

        Args:
            parsed_response: The dictionary parsed from the LLM's JSON output.
            file_path: The absolute path to the source file.
            file_content: The raw content of the source file.

        Returns:
            A FileMetadata object populated with extracted and calculated data.

        Raises:
            ExtractionProcessingError: If processing fails due to data inconsistencies or errors.
        """
        self.logger.info(f"Processing extracted metadata for: {file_path}")
        try:
            # Calculate additional metadata
            size_bytes = len(file_content.encode('utf-8'))
            md5_digest = self._calculate_md5(file_content)
            extraction_time = datetime.now(timezone.utc) # Use timezone-aware UTC time

            # Get filesystem last modified time (use extraction time as fallback)
            try:
                last_modified_timestamp = os.path.getmtime(file_path)
                last_modified_dt = datetime.fromtimestamp(last_modified_timestamp, timezone.utc)
            except OSError as e:
                self.logger.warning(f"Could not get filesystem last modified time for {file_path}: {e}. Using extraction time.")
                last_modified_dt = extraction_time

            # Process nested structures, handling potential None values from parser
            header_data = parsed_response.get("headerSections") or {}
            functions_data = parsed_response.get("functions") or []
            classes_data = parsed_response.get("classes") or []

            # Create the FileMetadata object using Pydantic validation
            metadata = FileMetadata(
                path=file_path, # Use the provided file_path
                language=parsed_response.get("language"), # Optional field
                header_sections=self._process_header_sections(header_data),
                functions=self._process_functions(functions_data),
                classes=self._process_classes(classes_data),
                size_bytes=size_bytes,
                md5_digest=md5_digest,
                last_modified=last_modified_dt,
                extraction_timestamp=extraction_time
            )

            self.logger.info(f"Successfully processed metadata for: {file_path}")
            return metadata

        except Exception as e:
            self.logger.error(f"Failed to process extraction results for {file_path}: {e}", exc_info=True)
            # Wrap the original exception
            raise ExtractionProcessingError(f"Failed to process extraction results for {file_path}: {e}") from e

    def _process_header_sections(self, header_data: Dict[str, Any]) -> HeaderSections:
        """Safely processes the headerSections dictionary."""
        return HeaderSections(
            intent=header_data.get("intent"),
            design_principles=header_data.get("designPrinciples", []),
            constraints=header_data.get("constraints", []),
            reference_documentation=header_data.get("referenceDocumentation", []),
            change_history=self._process_change_history(header_data.get("changeHistory", []))
        )

    def _process_change_history(self, history_data: List[Dict[str, Any]]) -> List[ChangeRecord]:
        """Safely processes the changeHistory list."""
        records = []
        for i, record_data in enumerate(history_data):
            if not isinstance(record_data, dict):
                 self.logger.warning(f"Skipping invalid change history item at index {i}: not a dictionary.")
                 continue
            try:
                # Attempt to parse timestamp, fallback gracefully
                timestamp_str = record_data.get("timestamp")
                timestamp_dt = self._parse_iso_timestamp(timestamp_str) if timestamp_str else None

                records.append(ChangeRecord(
                    timestamp=timestamp_dt,
                    summary=record_data.get("summary"),
                    details=record_data.get("details", [])
                ))
            except Exception as e:
                self.logger.warning(f"Failed to process change record at index {i}: {record_data}. Error: {e}", exc_info=True)
                # Append a record with None values or skip? Let's skip.
        return records

    def _process_functions(self, functions_data: List[Dict[str, Any]]) -> List[FunctionMetadata]:
        """Safely processes the functions list."""
        processed_functions = []
        for i, func_data in enumerate(functions_data):
             if not isinstance(func_data, dict):
                  self.logger.warning(f"Skipping invalid function item at index {i}: not a dictionary.")
                  continue
             try:
                  processed_functions.append(FunctionMetadata(
                       name=func_data.get("name"),
                       doc_sections=self._process_doc_sections(func_data.get("docSections") or {}),
                       parameters=func_data.get("parameters", []),
                       line_range=self._process_line_range(func_data.get("lineRange") or {})
                  ))
             except Exception as e:
                  self.logger.warning(f"Failed to process function at index {i}: {func_data}. Error: {e}", exc_info=True)
        return processed_functions

    def _process_classes(self, classes_data: List[Dict[str, Any]]) -> List[ClassMetadata]:
        """Safely processes the classes list."""
        processed_classes = []
        for i, class_data in enumerate(classes_data):
             if not isinstance(class_data, dict):
                  self.logger.warning(f"Skipping invalid class item at index {i}: not a dictionary.")
                  continue
             try:
                  processed_classes.append(ClassMetadata(
                       name=class_data.get("name"),
                       doc_sections=self._process_doc_sections(class_data.get("docSections") or {}),
                       methods=self._process_functions(class_data.get("methods") or []), # Recursively process methods
                       line_range=self._process_line_range(class_data.get("lineRange") or {})
                  ))
             except Exception as e:
                  self.logger.warning(f"Failed to process class at index {i}: {class_data}. Error: {e}", exc_info=True)
        return processed_classes

    def _process_doc_sections(self, doc_data: Dict[str, Any]) -> DocSections:
        """Safely processes the docSections dictionary."""
        return DocSections(
            intent=doc_data.get("intent"),
            design_principles=doc_data.get("designPrinciples", []),
            implementation_details=doc_data.get("implementationDetails"),
            design_decisions=doc_data.get("designDecisions")
        )

    def _process_line_range(self, range_data: Dict[str, Any]) -> LineRange:
        """Safely processes the lineRange dictionary."""
        # Attempt to convert start/end to int, defaulting to None on failure
        start = None
        end = None
        try:
            start_raw = range_data.get("start")
            if start_raw is not None:
                start = int(start_raw)
        except (ValueError, TypeError):
            self.logger.warning(f"Could not parse line range start value: {range_data.get('start')}")
        try:
            end_raw = range_data.get("end")
            if end_raw is not None:
                end = int(end_raw)
        except (ValueError, TypeError):
            self.logger.warning(f"Could not parse line range end value: {range_data.get('end')}")

        return LineRange(start=start, end=end)

    def _parse_iso_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parses an ISO 8601 timestamp string into a timezone-aware datetime object."""
        if not timestamp_str or not isinstance(timestamp_str, str):
            return None
        try:
            # Handle 'Z' for UTC timezone
            if timestamp_str.endswith('Z'):
                timestamp_str = timestamp_str[:-1] + '+00:00'
            dt = datetime.fromisoformat(timestamp_str)
            # Ensure datetime is timezone-aware (assume UTC if no tzinfo)
            if dt.tzinfo is None:
                 dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            self.logger.warning(f"Could not parse timestamp string '{timestamp_str}' into ISO 8601 format.")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error parsing timestamp '{timestamp_str}': {e}", exc_info=True)
            return None

    def _calculate_md5(self, content: str) -> str:
        """Calculates the MD5 hash of the given string content."""
        try:
            return hashlib.md5(content.encode('utf-8')).hexdigest()
        except Exception as e:
             self.logger.error(f"Failed to calculate MD5 hash: {e}", exc_info=True)
             return "md5_error" # Return a placeholder on error
