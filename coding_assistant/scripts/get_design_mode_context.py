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
# This script generates MIME mail formatted messages with document attachments for two
# different scenarios: master documentation and HSTC files. It's designed to be used
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
# 2025-04-24T06:43:55Z : Refactored code and made paths relative by CodeAssistant
# * Created add_dbp_headers helper function to make X-DBP-CodebaseFilePath relative to project root
# * Created check_size_limit helper function to eliminate code duplication
# * Refactored create_mime_message to use these helpers (DRY principle)
# 2025-04-24T03:33:12Z : Fixed TypeError in EmailMessage.add_attachment by CodeAssistant
# * Corrected parameters for text vs non-text attachments
# * Used different parameter sets based on content type
# * Added special handling for non-standard text MIME types
# 2025-04-24T03:30:10Z : Completely redesigned message creation approach by CodeAssistant
# * Switched to EmailMessage API to properly handle text attachments without base64 encoding
# * Used add_attachment method with explicit parameters for better control
# * Implemented proper payload management for size limits
# * Added help text to include default value information
# 2025-04-24T03:08:21Z : Added message size limit functionality by CodeAssistant
# * Implemented --max-message-size command-line option
# * Added size checking logic to keep message under specified byte limit
# * Prioritized top-tier documents when truncating
# 2025-04-24T02:59:51Z : Added explicit MIME type registration by CodeAssistant
# * Registered markdown MIME type to ensure proper content type detection
# 2025-04-24T02:58:47Z : Fixed encoding for markdown files by CodeAssistant
# * Explicitly set Content-Transfer-Encoding to 8bit for text files to prevent base64 encoding
# 2025-04-24T02:56:47Z : Updated text file handling by CodeAssistant
# * Added proper MIME type detection for text files
# * Avoided base64 encoding for text files using MIMEText
# 2025-04-24T02:50:32Z : Initial creation by CodeAssistant
# * Created script to generate MIME mail messages with document attachments
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
    Parse command line arguments to determine which MIME message type to generate.
    
    [Design principles]
    Simple interface with mutually exclusive options for clarity.
    
    [Implementation details]
    Uses argparse to create a parser with two mutually exclusive arguments.
    
    Returns:
        argparse.Namespace: Parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description='Generate MIME messages with document attachments.')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--master-documents', action='store_true',
                       help='Generate MIME message with markdown documents from doc/ and templates')
    group.add_argument('--hstc', action='store_true',
                       help='Generate MIME message with all HSTC.md files')
    parser.add_argument('--max-message-size', type=int, default=150000, metavar='BYTES',
                       help='Maximum size of the MIME message in bytes (default: 150000). Truncates attachments if needed.')
    return parser.parse_args()


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


def find_master_documents(base_dir):
    """
    [Function intent]
    Find all markdown documents in doc/ directory and the template files.
    
    [Design principles]
    Centralized file collection for maintainability.
    
    [Implementation details]
    Collects all .md files in doc/ directory and adds GENAI template files.
    
    Args:
        base_dir (str): Base directory of the project
    
    Returns:
        list: Paths to all master documents
    """
    documents = []
    
    # Add template files
    documents.append(os.path.join(base_dir, "coding_assistant/GENAI_HEADER_TEMPLATE.txt"))
    documents.append(os.path.join(base_dir, "coding_assistant/GENAI_FUNCTION_TEMPLATE.txt"))
    
    # Add all markdown files in doc/ directory
    doc_dir = os.path.join(base_dir, "doc")
    for root, _, files in os.walk(doc_dir):
        for file in files:
            if file.endswith(".md"):
                documents.append(os.path.join(root, file))
    
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
    
    [Implementation details]
    Finds the part by filename and adds appropriate headers with values.
    
    Args:
        msg (EmailMessage): The MIME message
        filename (str): Filename to match the part
        filepath (str): Full path to use for CodebaseFilePath (will be made relative)
    """
    # Make filepath relative to project root
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    rel_filepath = os.path.relpath(filepath, base_dir)
    
    for part in msg.get_payload():
        if part.get_filename() == filename:
            part["X-DBP-CodebaseFilePath"] = rel_filepath
            part['X-DBP-TopTierDocument'] = 'True' if is_top_tier_document(rel_filepath) else 'False'


def check_size_limit(msg, filename, max_message_size):
    """
    [Function intent]
    Check if adding an attachment has exceeded the size limit and remove it if necessary.
    
    [Design principles]
    Single-responsibility function for size limit enforcement.
    
    [Implementation details]
    Checks message size against limit and removes the latest attachment if needed.
    
    Args:
        msg (EmailMessage): The MIME message
        filename (str): Filename of the attachment to check
        max_message_size (int): Maximum size in bytes, or None for no limit
        
    Returns:
        bool: True if attachment was kept, False if it was removed
    """
    if max_message_size is None:
        return True
        
    if len(msg.as_string()) > max_message_size:
        # Remove the attachment we just added
        payload = msg.get_payload()
        for i, part in enumerate(payload):
            if part.get_filename() == filename:
                payload.pop(i)
                return False
    return True


def create_mime_message(files, subject, max_message_size=None):
    """
    [Function intent]
    Create a MIME multipart message with the specified files as attachments.
    
    [Design principles]
    Reusable message creation with clear metadata.
    Use appropriate MIME types without base64 encoding for text files.
    Respect message size limits when specified.
    
    [Implementation details]
    Creates a MIME message with text body and file attachments, adding
    special headers for top-tier documents. Uses a completely different
    approach for text files to ensure they aren't base64 encoded.
    
    Args:
        files (list): List of file paths to attach
        subject (str): Subject line for the message
        max_message_size (int, optional): Maximum size of the MIME message in bytes
    
    Returns:
        MIMEMultipart: MIME message with attachments
    """
    import email.policy
    from email.message import EmailMessage
    
    # Create message container with SMTP policy (to avoid base64 encoding where possible)
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = 'design-mode-context@example.com'
    msg['To'] = 'genai-assistant@example.com'
    msg.preamble = 'This is a multi-part message in MIME format.'
    
    # Prioritize top-tier documents when size limits are specified
    if max_message_size is not None:
        files = sorted(files, key=lambda f: 0 if is_top_tier_document(f) else 1)
    
    # Set up for size tracking
    included_files = 0
    excluded_files = 0
    
    # Add informative body
    body = f"This message contains document attachments for Design Mode context."
    msg.set_content(body)
    
    # Add files as attachments
    for filepath in files:
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
            
            # Add headers and check size
            add_dbp_headers(msg, filename, filepath)
            
            if check_size_limit(msg, filename, max_message_size):
                included_files += 1
            else:
                excluded_files += 1
                
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
                
                # Add headers and check size
                add_dbp_headers(msg, filename, filepath)
                
                if check_size_limit(msg, filename, max_message_size):
                    included_files += 1
                else:
                    excluded_files += 1
                    
            except Exception as e:
                sys.stderr.write(f"Error processing file {filepath}: {e}\n")
    
    # Update the body text with information about included/excluded files if needed
    if max_message_size is not None and excluded_files > 0:
        updated_body = (
            f"This message contains {included_files} document attachments for Design Mode context.\n"
            f"Note: {excluded_files} files were excluded due to the message size limit of {max_message_size} bytes."
        )
        
        # Replace the content of the main text part
        payload = msg.get_payload()
        for i, part in enumerate(payload):
            if part.get_content_type() == 'text/plain' and part.get('Content-Disposition') is None:
                # This is likely the main body text
                payload[i].set_content(updated_body)
                break
    
    return msg


def main():
    """
    [Function intent]
    Main function that orchestrates the MIME message generation process.
    
    [Design principles]
    Clear workflow with error handling.
    
    [Implementation details]
    Parses arguments, finds appropriate files, creates MIME message and outputs to stdout.
    """
    args = parse_arguments()
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    if args.master_documents:
        files = find_master_documents(base_dir)
        subject = "Design Mode: Master Documentation Context"
    else:  # args.hstc
        files = find_hstc_files(base_dir)
        subject = "Design Mode: HSTC Documentation Context"
    
    if not files:
        sys.stderr.write("No files found matching the specified criteria.\n")
        sys.exit(1)
    
    # Create and output the MIME message
    mime_msg = create_mime_message(files, subject, args.max_message_size)
    sys.stdout.write(mime_msg.as_string())


if __name__ == "__main__":
    main()
