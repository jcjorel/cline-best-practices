#!/usr/bin/env python3
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
# This script generates MIME mail formatted messages with document attachments for
# different types of documentation (top-tier, second-tier, and HSTC files). It supports
# combining multiple document types in a single message. It's designed to be used
# in Design Mode to load necessary context documents for GenAI assistants.
###############################################################################
# [Source file design principles]
# - Single responsibility: Generate MIME messages for document collections
# - Modularity: Separate functions for different operations (arg parsing, file finding, MIME creation)
# - Clear error handling with informative messages
# - Efficient file traversal with minimal memory footprint
# - No external dependencies beyond Python standard library
###############################################################################
# [Source file constraints]
# - Must output to stdout only
# - Must correctly identify top-tier documents as specified in system prompt
# - Must properly encode all file content in MIME format
# - Must handle file reading errors gracefully
###############################################################################
# [Dependencies]
# codebase:coding_assistant/GENAI_HEADER_TEMPLATE.txt
# codebase:coding_assistant/GENAI_FUNCTION_TEMPLATE.txt
# codebase:doc/
# system:email.mime.multipart
# system:email.mime.text
# system:email.mime.application
# system:argparse
# system:os
# system:sys
###############################################################################
# [GenAI tool change history]
# 2025-04-24T07:47:40Z : Optimized pagination algorithm to minimize page count by CodeAssistant
# * Implemented advanced page packing algorithm to maximize document density per page
# * Added calculate_pages() function to pre-compute optimal page boundaries
# * Replaced simple size-based pagination with a more efficient space utilization approach
# * Fixed issue where multiple pages were created when files could fit in fewer pages
# 2025-04-24T07:38:20Z : Fixed duplicated headers and improved pagination reliability by CodeAssistant
# * Fixed issue where document headers were getting duplicated across attachments
# * Added header deduplication mechanism in add_dbp_headers()
# * Updated headers handling to only modify the most recently added attachment
# 2025-04-24T07:33:35Z : Improved command-line interface organization by CodeAssistant
# * Added documentation selection options as a logical argument group
# * Made option grouping more intuitive for users
# 2025-04-24T07:28:00Z : Updated pagination to use zero-based indexing by CodeAssistant
# * Modified page numbering to start at 0 with page 0 being the first page
# * Ensured deterministic file inclusion order for consistent pagination
# * Improved page display in subject and body (showing human-friendly 1-based in UI only)
# * Fixed pagination to ensure each page contains unique files not included in previous pages
# 2025-04-24T07:03:40Z : Added pagination mechanism for size-limited documents by CodeAssistant
# * Implemented --page-number command-line option for pagination control
# * Created paginate_files() helper function to split file lists into pages
# * Modified create_mime_message() to handle pagination and return pagination info
# * Updated subject line and body text to include page information
###############################################################################

import argparse
import email.mime.multipart
import email.mime.text
import email.mime.application
import os
import sys
import mimetypes
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# Register the markdown MIME type if not already registered
mimetypes.add_type('text/markdown', '.md')


def parse_arguments():
    """
    [Function intent]
    Parse command line arguments to determine which document types to include in the MIME message.
    
    [Design principles]
    Flexible interface with multiple options that can be combined.
    Support for pagination when size limits are reached.
    Zero-based indexing for pagination.
    
    [Implementation details]
    Uses argparse to create a parser with multiple boolean flag options that can be combined.
    Adds pagination support through the page-number parameter, using 0-based indexing.
    
    Returns:
        argparse.Namespace: Parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description='Generate MIME messages with document attachments.')
    
    # Document selection options - can be combined
    doc_group = parser.add_argument_group('Document selection options (can be combined)')
    doc_group.add_argument('--include-top-tier-documents', action='store_true',
                       help='Include top-tier documentation files (GENAI templates and key doc/ files)')
    doc_group.add_argument('--include-second-tier-documents', action='store_true',
                       help='Include second-tier documentation files (remaining doc/ files)')
    doc_group.add_argument('--include-hstc-documents', action='store_true',
                       help='Include all HSTC.md files from the codebase')
    
    # Size limit and pagination options
    parser.add_argument('--max-message-size', type=int, default=150000, metavar='BYTES',
                       help='Maximum size of the MIME message in bytes (default: 150000). Truncates attachments if needed.')
    parser.add_argument('--page-number', type=int, default=0, metavar='N',
                       help='When size limits are reached, retrieve page N of documents (default: 0). Page numbering starts at 0.')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.page_number < 0:
        parser.error("Page number must be a non-negative integer (starting at 0).")
    
    # Ensure at least one document type is selected
    if not (args.include_top_tier_documents or args.include_second_tier_documents or args.include_hstc_documents):
        parser.error("At least one document type option must be specified.")
    
    return args


def is_top_tier_document(filepath):
    """
    [Function intent]
    Determine if a document is a top-tier document as specified in system prompt.
    
    [Design principles]
    Simple lookup based on document paths mentioned in system prompt.
    
    [Implementation details]
    Checks if the file path matches any of the top-tier documents.
    
    Args:
        filepath (str): Path to the document
    
    Returns:
        bool: True if the document is a top-tier document, False otherwise
    """
    # List of top-tier documents from system prompt
    top_tier_docs = [
        "coding_assistant/GENAI_HEADER_TEMPLATE.txt",
        "coding_assistant/GENAI_FUNCTION_TEMPLATE.txt",
        "doc/DESIGN.md",
        "doc/DESIGN_DECISIONS.md",
        "doc/DATA_MODEL.md",
        "doc/API.md",
        "doc/DOCUMENT_RELATIONSHIPS.md",
        "doc/PR-FAQ.md",
        "doc/WORKING_BACKWARDS.md",
        "doc/SECURITY.md",
        "doc/CONFIGURATION.md",
        "doc/CODING_GUIDELINES.md"
    ]
    return filepath in top_tier_docs


def find_top_tier_documents(base_dir):
    """
    [Function intent]
    Find all top-tier documents as specified in system prompt.
    
    [Design principles]
    Clear identification of critical documentation files.
    
    [Implementation details]
    Uses the is_top_tier_document function to filter for specific files.
    
    Args:
        base_dir (str): Base directory of the project
    
    Returns:
        list: Paths to all top-tier documents
    """
    documents = []
    
    # Add template files
    template_files = [
        os.path.join(base_dir, "coding_assistant/GENAI_HEADER_TEMPLATE.txt"),
        os.path.join(base_dir, "coding_assistant/GENAI_FUNCTION_TEMPLATE.txt")
    ]
    documents.extend(template_files)
    
    # Add top-tier markdown files from doc/ directory
    top_tier_md_files = [
        "DESIGN.md",
        "DESIGN_DECISIONS.md",
        "DATA_MODEL.md",
        "API.md",
        "DOCUMENT_RELATIONSHIPS.md",
        "PR-FAQ.md",
        "WORKING_BACKWARDS.md",
        "SECURITY.md",
        "CONFIGURATION.md",
        "CODING_GUIDELINES.md"
    ]
    
    doc_dir = os.path.join(base_dir, "doc")
    for md_file in top_tier_md_files:
        full_path = os.path.join(doc_dir, md_file)
        if os.path.exists(full_path):
            documents.append(full_path)
    
    return documents


def find_second_tier_documents(base_dir):
    """
    [Function intent]
    Find all non-top-tier markdown documents in the doc/ directory.
    
    [Design principles]
    Comprehensive collection of secondary documentation.
    
    [Implementation details]
    Walks the doc/ directory and filters out top-tier documents.
    
    Args:
        base_dir (str): Base directory of the project
    
    Returns:
        list: Paths to all second-tier documents
    """
    documents = []
    top_tier_docs = find_top_tier_documents(base_dir)
    
    # Get all markdown files in doc/ directory
    doc_dir = os.path.join(base_dir, "doc")
    for root, _, files in os.walk(doc_dir):
        for file in files:
            if file.endswith(".md"):
                full_path = os.path.join(root, file)
                # Only include if not already in top-tier
                if full_path not in top_tier_docs:
                    documents.append(full_path)
    
    return documents


def is_text_file(filepath):
    """
    [Function intent]
    Determine if a file is a text file based on its extension and content.
    
    [Design principles]
    Simple detection for common text file types.
    
    [Implementation details]
    Uses file extension and mimetype detection.
    
    Args:
        filepath (str): Path to the file
    
    Returns:
        bool: True if the file is a text file, False otherwise
    """
    text_extensions = ['.md', '.txt', '.py', '.js', '.html', '.css', '.json', '.xml', '.yml', '.yaml']
    ext = os.path.splitext(filepath)[1].lower()
    
    if ext in text_extensions:
        return True
    
    # Use mimetypes to check if it's a text file
    mime_type, _ = mimetypes.guess_type(filepath)
    if mime_type and mime_type.startswith('text/'):
        return True
        
    return False


def find_hstc_files(base_dir):
    """
    [Function intent]
    Find all HSTC.md files in the entire codebase.
    
    [Design principles]
    Recursive search with specific targeting.
    
    [Implementation details]
    Recursively searches for HSTC.md files in all directories.
    
    Args:
        base_dir (str): Base directory of the project
    
    Returns:
        list: Paths to all HSTC.md files
    """
    hstc_files = []
    
    for root, _, files in os.walk(base_dir):
        # Skip the captured_chats directory which should not be included
        if "coding_assistant/captured_chats" in root:
            continue
            
        for file in files:
            if file == "HSTC.md":
                hstc_files.append(os.path.join(root, file))
    
    return hstc_files


def add_dbp_headers(msg, filename, filepath):
    """
    [Function intent]
    Add X-DBP headers to a MIME part, including CodebaseFilePath and TopTierDocument.
    
    [Design principles]
    Single-responsibility function to add consistent headers to MIME parts.
    Use relative paths from project root for file path headers.
    
    [Implementation details]
    Finds the part by filename and adds appropriate headers with values.
    Makes file paths relative to project root for consistent referencing.
    Ensures headers are not duplicated.
    
    Args:
        msg (EmailMessage): The MIME message
        filename (str): Filename to match the part
        filepath (str): Full path to use for CodebaseFilePath (will be made relative)
    """
    # Make filepath relative to project root
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    rel_filepath = os.path.relpath(filepath, base_dir)
    
    # Find only the last part with matching filename (most recently added)
    matching_parts = []
    for i, part in enumerate(msg.get_payload()):
        if part.get_filename() == filename:
            matching_parts.append((i, part))
    
    # Only add headers to the last matching part (most recently added)
    if matching_parts:
        idx, part = matching_parts[-1]
        # Remove any existing headers to prevent duplication
        for header in ['X-DBP-CodebaseFilePath', 'X-DBP-TopTierDocument']:
            if header in part:
                del part[header]
                
        # Add the headers
        part["X-DBP-CodebaseFilePath"] = rel_filepath
        part['X-DBP-TopTierDocument'] = 'True' if is_top_tier_document(rel_filepath) else 'False'


def determine_message_capacity(files, max_message_size):
    """
    [Function intent]
    Determine how many files from the list can fit in a message without exceeding size limit.
    
    [Design principles]
    Empirical capacity determination based on actual file sizes.
    Deterministic file inclusion order.
    
    [Implementation details]
    Creates a test message and adds files until reaching the size limit.
    
    Args:
        files (list): List of file paths to test
        max_message_size (int): Maximum size of the message in bytes
    
    Returns:
        int: Number of files that can fit in a single message
    """
    if not max_message_size or max_message_size <= 0 or not files:
        return len(files)
        
    # Create a test message
    import email.mime.multipart
    from email.message import EmailMessage
    
    msg = EmailMessage()
    msg['Subject'] = "Test Message"
    msg['From'] = 'design-mode-context@example.com'
    msg['To'] = 'genai-assistant@example.com'
    msg.set_content("Test content")
    
    # Add files until we hit the limit
    files_added = 0
    for filepath in files:
        try:
            filename = os.path.basename(filepath)
            
            if is_text_file(filepath):
                with open(filepath, 'r', encoding='utf-8') as file:
                    content = file.read()
                    
                mime_type, _ = mimetypes.guess_type(filepath)
                if not mime_type:
                    if filepath.lower().endswith('.md'):
                        mime_type = 'text/markdown'
                    else:
                        mime_type = 'text/plain'
                
                maintype, subtype = mime_type.split('/', 1)
                
                if maintype == 'text':
                    msg.add_attachment(
                        content,
                        subtype=subtype,
                        filename=filename,
                        disposition='attachment',
                        charset='utf-8'
                    )
                else:
                    msg.add_attachment(
                        content.encode('utf-8'),
                        maintype=maintype,
                        subtype=subtype,
                        filename=filename,
                        disposition='attachment'
                    )
            else:
                with open(filepath, 'rb') as file:
                    content = file.read()
                
                msg.add_attachment(
                    content,
                    maintype='application',
                    subtype='octet-stream',
                    filename=filename,
                    disposition='attachment'
                )
                
            # Check if we've exceeded the size limit
            if len(msg.as_string()) > max_message_size:
                # Remove the last attachment
                payload = msg.get_payload()
                payload.pop()
                break
                
            files_added += 1
            
        except Exception:
            # Skip any files that cause errors
            continue
    
    # Return at least 1 to avoid empty messages (unless there are no files)
    return max(1, files_added) if files else 0


def calculate_pages(files, max_message_size):
    """
    [Function intent]
    Calculate page boundaries to maximize file inclusion while staying under size limits.
    
    [Design principles]
    Optimize for minimum number of pages by packing files efficiently.
    Respect message size limits strictly.
    
    [Implementation details]
    Builds actual test messages for each page to get precise size calculations.
    Fills each page to maximum capacity before starting a new one.
    
    Args:
        files (list): List of file paths to paginate
        max_message_size (int): Maximum size of the message in bytes
    
    Returns:
        list: List of page boundaries where each item is (start_index, end_index, is_last_page)
    """
    if not max_message_size or max_message_size <= 0 or not files:
        return [(0, len(files), True)]
        
    page_boundaries = []
    current_page_start = 0
    
    while current_page_start < len(files):
        # Create a test message to calculate size
        import email.mime.multipart
        from email.message import EmailMessage
        
        msg = EmailMessage()
        msg['Subject'] = "Test Message"
        msg['From'] = 'design-mode-context@example.com'
        msg['To'] = 'genai-assistant@example.com'
        msg.set_content("Test content")
        
        # Add files until we hit the limit
        current_idx = current_page_start
        while current_idx < len(files):
            filepath = files[current_idx]
            try:
                filename = os.path.basename(filepath)
                
                if is_text_file(filepath):
                    with open(filepath, 'r', encoding='utf-8') as file:
                        content = file.read()
                        
                    mime_type, _ = mimetypes.guess_type(filepath)
                    if not mime_type:
                        if filepath.lower().endswith('.md'):
                            mime_type = 'text/markdown'
                        else:
                            mime_type = 'text/plain'
                    
                    maintype, subtype = mime_type.split('/', 1)
                    
                    if maintype == 'text':
                        msg.add_attachment(
                            content,
                            subtype=subtype,
                            filename=filename,
                            disposition='attachment',
                            charset='utf-8'
                        )
                    else:
                        msg.add_attachment(
                            content.encode('utf-8'),
                            maintype=maintype,
                            subtype=subtype,
                            filename=filename,
                            disposition='attachment'
                        )
                else:
                    with open(filepath, 'rb') as file:
                        content = file.read()
                    
                    msg.add_attachment(
                        content,
                        maintype='application',
                        subtype='octet-stream',
                        filename=filename,
                        disposition='attachment'
                    )
                    
                # Check if we've exceeded the size limit
                if len(msg.as_string()) > max_message_size:
                    # Remove the last attachment
                    payload = msg.get_payload()
                    payload.pop()
                    break
                    
                current_idx += 1
                
            except Exception:
                # Skip any files that cause errors
                current_idx += 1
                continue
        
        # Handle edge case where a single file might be too big
        if current_idx == current_page_start:
            current_idx = current_page_start + 1  # Force at least one file per page
        
        # Record this page's boundaries
        is_last_page = current_idx >= len(files)
        page_boundaries.append((current_page_start, current_idx, is_last_page))
        
        # Move to the next page
        current_page_start = current_idx
    
    return page_boundaries


def paginate_files(files, page_number, max_message_size):
    """
    [Function intent]
    Split a list of files into pages based on message size constraints and return the specified page.
    
    [Design principles]
    Precise pagination with deterministic file inclusion order.
    Zero-based page indexing.
    Each page contains unique files not included in previous pages.
    Maximize files per page to minimize total pages.
    
    [Implementation details]
    Calculates optimal page boundaries to pack files efficiently.
    Returns the specific page requested using zero-based indexing.
    
    Args:
        files (list): List of file paths to paginate
        page_number (int): The page number to return (0-based)
        max_message_size (int): Maximum size of the message in bytes
    
    Returns:
        tuple: (list of files for requested page, total number of pages)
    """
    # If no size limit, return all files as a single page
    if not max_message_size or max_message_size <= 0:
        return files, 1
    
    # Calculate page boundaries to optimize page count
    page_boundaries = calculate_pages(files, max_message_size)
    total_pages = len(page_boundaries)
    
    # Adjust page_number if it's out of range
    if page_number >= total_pages:
        page_number = total_pages - 1
    if page_number < 0:
        page_number = 0
    
    # Get the boundaries for the requested page
    start_idx, end_idx, _ = page_boundaries[page_number]
    
    # Return the files for the requested page and the total number of pages
    return files[start_idx:end_idx], total_pages


def create_mime_message(files, subject, max_message_size=None, page_number=0):
    """
    [Function intent]
    Create a MIME multipart message with the specified files as attachments.
    
    [Design principles]
    Reusable message creation with clear metadata.
    Use appropriate MIME types without base64 encoding for text files.
    Respect message size limits when specified.
    Support pagination for content that exceeds size limits using zero-based indexing.
    
    [Implementation details]
    Creates a MIME message with text body and file attachments, adding
    special headers for top-tier documents. Uses a completely different
    approach for text files to ensure they aren't base64 encoded.
    
    Args:
        files (list): List of file paths to attach
        subject (str): Subject line for the message
        max_message_size (int, optional): Maximum size of the MIME message in bytes
        page_number (int, optional): Page number for pagination (default: 0). Zero-based indexing.
    
    Returns:
        tuple: (MIMEMultipart message with attachments, dict with pagination info)
    """
    import email.policy
    from email.message import EmailMessage
    
    # Prioritize top-tier documents when size limits are specified
    if max_message_size is not None:
        files = sorted(files, key=lambda f: 0 if is_top_tier_document(f) else 1)
        
    # Paginate the files
    if max_message_size is not None:
        page_files, total_pages = paginate_files(files, page_number, max_message_size)
    else:
        page_files = files
        total_pages = 1
        
    # Create message container with SMTP policy (to avoid base64 encoding where possible)
    msg = EmailMessage()
    # Display page number as 1-based in subject for human readability
    msg['Subject'] = f"{subject} (Page {page_number + 1} of {total_pages})"
    msg['From'] = 'design-mode-context@example.com'
    msg['To'] = 'genai-assistant@example.com'
    msg.preamble = 'This is a multi-part message in MIME format.'
    
    # Set up for size tracking
    included_files = 0
    
    # Add informative body (using 1-based page numbers for display)
    body = f"This message contains document attachments for Design Mode context (Page {page_number + 1} of {total_pages})."
    msg.set_content(body)
    
    # Pagination info to return
    pagination_info = {
        "page_number": page_number,
        "total_pages": total_pages,
        "files_per_page": len(page_files) if page_files else 0,
    }
    
    # Process files to attach
    for filepath in page_files:
        try:
            filename = os.path.basename(filepath)
            
            # Process based on file type
            if is_text_file(filepath):
                with open(filepath, 'r', encoding='utf-8') as file:
                    content = file.read()
                
                # Determine content type
                mime_type, _ = mimetypes.guess_type(filepath)
                if not mime_type:
                    if filepath.lower().endswith('.md'):
                        mime_type = 'text/markdown'
                    else:
                        mime_type = 'text/plain'
                
                maintype, subtype = mime_type.split('/', 1)
                
                # Add the attachment with correct parameters for text
                # EmailMessage.add_attachment() has different params for text versus binary
                if maintype == 'text':
                    msg.add_attachment(
                        content,
                        subtype=subtype,
                        filename=filename,
                        disposition='attachment',
                        charset='utf-8'
                    )
                else:
                    # If it's not text/*, add as application/* with content encoded as bytes
                    msg.add_attachment(
                        content.encode('utf-8'),
                        maintype=maintype,
                        subtype=subtype,
                        filename=filename,
                        disposition='attachment'
                    )
            else:
                # Binary files
                with open(filepath, 'rb') as file:
                    content = file.read()
                
                # Use add_attachment to add binary files
                msg.add_attachment(
                    content,
                    maintype='application',
                    subtype='octet-stream',
                    filename=filename,
                    disposition='attachment'
                )
            
            # Add headers with relative paths
            add_dbp_headers(msg, filename, filepath)
            
            included_files += 1
                
        except IOError as e:
            sys.stderr.write(f"Warning: Could not read file {filepath}: {e}\n")
        except UnicodeDecodeError as e:
            # Fall back to binary mode if UTF-8 decoding fails
            sys.stderr.write(f"Warning: File {filepath} is not UTF-8 encoded, using binary mode: {e}\n")
            try:
                with open(filepath, 'rb') as file:
                    content = file.read()
                
                # Add as binary attachment
                msg.add_attachment(
                    content,
                    maintype='application',
                    subtype='octet-stream',
                    filename=filename,
                    disposition='attachment'
                )
                
                # Add headers with relative paths
                add_dbp_headers(msg, filename, filepath)
                
                included_files += 1
                    
            except Exception as e:
                sys.stderr.write(f"Error processing file {filepath}: {e}\n")
    
    # Update the body text with information about included files and pagination
    updated_body = (
        f"This message contains {included_files} document attachments for Design Mode context.\n"
        f"Page {page_number + 1} of {total_pages}."
    )
    
    # Replace the content of the main text part
    payload = msg.get_payload()
    for i, part in enumerate(payload):
        if part.get_content_type() == 'text/plain' and part.get('Content-Disposition') is None:
            # This is likely the main body text
            payload[i].set_content(updated_body)
            break
    
    return msg, pagination_info


def main():
    """
    [Function intent]
    Main function that orchestrates the MIME message generation process.
    
    [Design principles]
    Clear workflow with error handling.
    Flexible document selection based on command line flags.
    Support for pagination when size limits are reached.
    
    [Implementation details]
    Parses arguments, finds appropriate files based on selected options,
    creates MIME message with combined document types, and outputs to stdout.
    Handles pagination through the page-number parameter.
    """
    args = parse_arguments()
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    files = []
    subject_parts = ["Design Mode:"]
    
    # Collect files based on selected options
    if args.include_top_tier_documents:
        top_tier_files = find_top_tier_documents(base_dir)
        files.extend(top_tier_files)
        subject_parts.append("Top-Tier Docs")
    
    if args.include_second_tier_documents:
        second_tier_files = find_second_tier_documents(base_dir)
        files.extend(second_tier_files)
        subject_parts.append("Second-Tier Docs")
    
    if args.include_hstc_documents:
        hstc_files = find_hstc_files(base_dir)
        files.extend(hstc_files)
        subject_parts.append("HSTC Files")
    
    # Remove duplicates while preserving order
    seen = set()
    files = [x for x in files if x not in seen and not seen.add(x)]
    
    if not files:
        sys.stderr.write("No files found matching the specified criteria.\n")
        sys.exit(1)
    
    # Create subject line from selected document types
    subject = " + ".join(subject_parts)
    
    # Create and output the MIME message with pagination support
    mime_msg, pagination_info = create_mime_message(files, subject, args.max_message_size, args.page_number)
    
    # If the requested page is out of range, provide feedback
    if args.page_number >= pagination_info["total_pages"]:
        sys.stderr.write(f"Warning: Requested page {args.page_number} exceeds available pages ({pagination_info['total_pages']}).\n")
        sys.stderr.write(f"Returning the last available page ({pagination_info['total_pages'] - 1}).\n")
    
    # Output the MIME message
    sys.stdout.write(mime_msg.as_string())


if __name__ == "__main__":
    main()
