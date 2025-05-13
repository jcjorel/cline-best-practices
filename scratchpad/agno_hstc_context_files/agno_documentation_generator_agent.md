# Documentation Generator Agent for HSTC

## Overview

The Documentation Generator Agent is responsible for processing extracted code metadata and comments to generate comprehensive and standardized documentation that meets HSTC requirements. This agent uses the Claude 3.7 model from Anthropic, leveraging its advanced reasoning capabilities to produce high-quality documentation based on code context and dependencies.

## Agent Implementation

The Documentation Generator Agent is implemented as an Agno agent with the Claude 3.7 model:

```python
from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.tools import ReasoningTools
import json
from pathlib import Path
from typing import Dict, List, Optional, Any

class DocumentationGeneratorAgent(Agent):
    """Agent for generating HSTC-compliant documentation using Claude 3.7."""
    
    def __init__(
        self,
        model_id: str = "claude-3-5-sonnet-20241022",
        **kwargs
    ):
        # Initialize Claude 3.7 model for documentation generation
        model = Claude(id=model_id)
        super().__init__(model=model, **kwargs)
        
        # Add reasoning tools for step-by-step analysis
        reasoning_tools = ReasoningTools()
        self.add_toolkit(reasoning_tools)
        
        # Initialize state for storage
        self.generated_documentation = {}
```

## Processing Pipeline

The Documentation Generator Agent operates with a multi-stage processing pipeline:

1. **Input Processing** - Accept file metadata, comments, and dependencies
2. **Documentation Analysis** - Assess existing documentation and required updates
3. **Documentation Generation** - Generate new or updated documentation
4. **Validation** - Ensure compliance with HSTC standards
5. **Output Formatting** - Structure results for the implementation plan

### Input Processing

The agent receives structured data from the File Analyzer Agent:

```python
def process_file_documentation(
    self, 
    file_path: str, 
    file_metadata: Dict[str, Any], 
    dependency_metadata: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Process file metadata and generate updated documentation
    
    Args:
        file_path: Path to the file being processed
        file_metadata: Metadata about the file from the File Analyzer
        dependency_metadata: Metadata about dependencies from the File Analyzer
        
    Returns:
        Dict containing updated documentation
    """
    # Extract key information from metadata
    file_type = file_metadata.get("file_type", "unknown")
    
    # Process differently based on file type
    if file_type == "source_code":
        return self._process_source_file(file_path, file_metadata, dependency_metadata)
    elif file_type == "markdown":
        return self._process_markdown_file(file_path, file_metadata)
    else:
        # For other file types, just return basic documentation
        return {
            "path": file_path,
            "file_type": file_type,
            "documentation_updated": False,
            "reason": f"File type {file_type} does not require HSTC documentation"
        }
```

### Processing Source Code Files

For source code files, the agent implements detailed documentation processing:

```python
def _process_source_file(
    self, 
    file_path: str, 
    file_metadata: Dict[str, Any], 
    dependency_metadata: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Process a source code file and generate documentation
    
    Args:
        file_path: Path to the file
        file_metadata: Metadata about the file
        dependency_metadata: Metadata about dependencies
        
    Returns:
        Dict containing updated documentation
    """
    language = file_metadata.get("language", "unknown")
    definitions = file_metadata.get("definitions", [])
    dependencies = file_metadata.get("dependencies", [])
    
    # Step 1: Analyze existing documentation
    thinking_prompt = self._build_documentation_analysis_prompt(file_path, file_metadata, dependency_metadata)
    analysis_response = self.tools.think(
        title="Documentation Analysis",
        thought=thinking_prompt,
        action="Analyze existing documentation and determine necessary updates",
        confidence=0.9
    )
    
    # Step 2: Generate updated documentation for the file header
    header_prompt = self._build_header_documentation_prompt(file_path, file_metadata, dependency_metadata, analysis_response)
    header_response = self.query(header_prompt)
    
    # Step 3: Generate documentation for each function/method/class
    definitions_documentation = []
    for definition in definitions:
        definition_prompt = self._build_definition_documentation_prompt(definition, file_metadata, dependency_metadata)
        definition_response = self.query(definition_prompt)
        
        try:
            definition_doc = json.loads(definition_response)
            definitions_documentation.append(definition_doc)
        except json.JSONDecodeError:
            # Handle parsing error
            definitions_documentation.append({
                "name": definition.get("name", "unknown"),
                "original_comment": definition.get("comments", ""),
                "updated_comment": definition_response,  # Use raw response as fallback
                "error": "Failed to parse response as JSON"
            })
    
    # Step 4: Validate and finalize documentation
    result = {
        "path": file_path,
        "file_type": "source_code",
        "language": language,
        "file_header": self._extract_header_documentation(header_response),
        "definitions": definitions_documentation,
        "documentation_updated": True,
        "analysis": analysis_response
    }
    
    # Store generated documentation
    self.generated_documentation[file_path] = result
    
    return result
```

## Using Step-by-Step Reasoning

The Documentation Generator Agent uses Claude 3.7's reasoning capabilities through Agno's ReasoningTools:

```python
def _build_documentation_analysis_prompt(
    self, 
    file_path: str, 
    file_metadata: Dict[str, Any], 
    dependency_metadata: Dict[str, Dict[str, Any]]
) -> str:
    """Build a prompt for analyzing documentation status and needs"""
    
    language = file_metadata.get("language", "unknown")
    definitions = file_metadata.get("definitions", [])
    dependencies = file_metadata.get("dependencies", [])
    
    # Extract dependency documentation information
    dependency_info = []
    for dep in dependencies:
        dep_name = dep.get("name", "unknown")
        dep_path = dep.get("path_or_package", "")
        dep_metadata = dependency_metadata.get(dep_path, {})
        
        dep_info = {
            "name": dep_name,
            "path": dep_path,
            "has_metadata": bool(dep_metadata)
        }
        
        if dep_metadata:
            # Include relevant header info from dependency
            if "file_header" in dep_metadata:
                dep_info["header"] = dep_metadata["file_header"]
                
            # Include imported function documentation if available
            imported_functions = dep.get("function_names", [])
            if imported_functions and "definitions" in dep_metadata:
                dep_info["imported_function_docs"] = []
                for func_name in imported_functions:
                    for def_info in dep_metadata.get("definitions", []):
                        if def_info.get("name") == func_name:
                            dep_info["imported_function_docs"].append(def_info)
        
        dependency_info.append(dep_info)
    
    # Build the prompt
    prompt = f"""
    Analyze the documentation status and needs for a {language} source file:
    
    File path: {file_path}
    
    # Existing Documentation Analysis
    
    ## File Header Documentation
    {file_metadata.get("header_comment", "No existing header comment found")}
    
    ## Function/Method/Class Documentation
    {len(definitions)} definitions found:
    {json.dumps(definitions, indent=2)}
    
    ## Dependencies
    {json.dumps(dependency_info, indent=2)}
    
    # HSTC Documentation Requirements
    
    According to HSTC standards, documentation must include:
    
    1. Source file header with:
       - Source file intent
       - Source file design principles
       - Source file constraints
       - Dependencies (with kind: codebase, system, or other)
       - Change history
    
    2. Function/Method/Class documentation with:
       - Function/Class method/Class intent
       - Design principles
       - Implementation details
    
    Analyze the current documentation against these standards and determine what updates are needed.
    Provide detailed reasoning and identify specific areas that need improvement.
    """
    
    return prompt
```

## Documentation Generation

The agent generates documentation that meets the HSTC standard requirements:

```python
def _build_header_documentation_prompt(
    self, 
    file_path: str, 
    file_metadata: Dict[str, Any], 
    dependency_metadata: Dict[str, Dict[str, Any]], 
    analysis: str
) -> str:
    """Build a prompt for generating file header documentation"""
    
    language = file_metadata.get("language", "unknown")
    comment_formats = file_metadata.get("comment_formats", {})
    existing_header = file_metadata.get("header_comment", "")
    
    # Determine appropriate comment syntax
    block_start = comment_formats.get("block_comment_start", "/*")
    block_end = comment_formats.get("block_comment_end", "*/")
    if not block_start or not block_end:
        # Fallback to language-specific defaults
        if language == "python":
            block_start = '"""'
            block_end = '"""'
        elif language in ["javascript", "typescript", "java", "c", "cpp", "csharp"]:
            block_start = "/*"
            block_end = "*/"
        elif language in ["ruby", "perl", "shell", "bash"]:
            block_start = "#"
            block_end = "#"
    
    prompt = f"""
    Generate a file header comment for a {language} source file that meets HSTC documentation standards.
    
    File path: {file_path}
    
    Based on the analysis:
    {analysis}
    
    The file header must follow this EXACT format:
    
    {block_start}
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
    # <Describe the detailed purpose of this file. Intent must be fully captured and contextualized.>
    ###############################################################################
    # [Source file design principles]
    # <List key design principles guiding this implementation>
    ###############################################################################
    # [Source file constraints]
    # <Document any limitations or requirements for this file>
    ###############################################################################
    # [Dependencies]
    # <File paths of others codebase and documentation files. List also language specific libraries if any>
    # <List of markdown files in doc/ that provide broader context for this file>
    # <Prefix the dependency with its kind like "<codebase|system|other>:<dependency>">
    ###############################################################################
    # [GenAI tool change history]
    # {self._get_current_timestamp()} : Initial documentation generated by HSTC tool
    # * Added standardized header documentation
    ###############################################################################
    {block_end}
    
    Use the file metadata and analysis to create a comprehensive header that fully captures the file's intent,
    design principles, constraints, and dependencies. Fill in ALL sections with meaningful content.
    
    Return the complete header in valid {language} comment syntax.
    Return ONLY the comment content as a raw string, without any JSON or code formatting.
    """
    
    return prompt
```

## Function Documentation Generation

For each function, method, or class, the agent generates appropriate documentation:

```python
def _build_definition_documentation_prompt(
    self, 
    definition: Dict[str, Any], 
    file_metadata: Dict[str, Any], 
    dependency_metadata: Dict[str, Dict[str, Any]]
) -> str:
    """Build a prompt for generating documentation for a function/method/class"""
    
    language = file_metadata.get("language", "unknown")
    comment_formats = file_metadata.get("comment_formats", {})
    name = definition.get("name", "unknown")
    def_type = definition.get("type", "function")
    existing_comment = definition.get("comments", "")
    
    # Determine appropriate docstring format
    docstring_format = comment_formats.get("docstring_format")
    docstring_start = comment_formats.get("docstring_start")
    docstring_end = comment_formats.get("docstring_end")
    
    # Fallback to language-specific defaults
    if not docstring_format:
        if language == "python":
            docstring_format = "triple quotes"
            docstring_start = '"""'
            docstring_end = '"""'
        elif language in ["javascript", "typescript"]:
            docstring_format = "JSDoc"
            docstring_start = "/**"
            docstring_end = "*/"
        elif language in ["java", "c", "cpp", "csharp"]:
            docstring_format = "block comment"
            docstring_start = "/*"
            docstring_end = "*/"
    
    prompt = f"""
    Generate documentation for a {language} {def_type} named "{name}" that meets HSTC standards.
    
    Existing documentation:
    {existing_comment}
    
    The documentation must include these three sections in this exact order:
    1. [Function/Class method/Class intent] - Purpose and role description
    2. [Design principles] - Patterns and approaches used
    3. [Implementation details] - Key technical implementation notes
    
    Use the appropriate {language} documentation format ({docstring_format}).
    
    Return a JSON object with these fields:
    - name: The name of the function/method/class
    - type: The type ("function", "method", or "class")
    - original_comment: The existing comment
    - updated_comment: The new documentation that follows HSTC standards
    
    Ensure the updated_comment uses proper {language} documentation syntax.
    """
    
    return prompt
```

## Handling Multiple Documentation Styles

The Documentation Generator Agent adapts to different programming languages and documentation styles:

```python
def _extract_header_documentation(self, response: str) -> Dict[str, Any]:
    """Extract structured header documentation from the raw response"""
    
    # Parse the raw response to extract key sections
    sections = {
        "intent": self._extract_section(response, "[Source file intent]"),
        "design_principles": self._extract_section(response, "[Source file design principles]"),
        "constraints": self._extract_section(response, "[Source file constraints]"),
        "dependencies": self._extract_dependencies(response),
        "change_history": self._extract_change_history(response),
    }
    
    # Include the full raw header response
    sections["raw_header"] = response
    
    return sections

def _extract_section(self, text: str, section_marker: str) -> str:
    """Extract a specific section from the header text"""
    try:
        start_idx = text.find(section_marker)
        if start_idx == -1:
            return ""
        
        # Find the start of the actual content
        start_idx = text.find("\n", start_idx)
        if start_idx == -1:
            return ""
        
        # Find the end of the section (next section marker or end of header)
        end_idx = text.find("###############################################################################", start_idx)
        if end_idx == -1:
            end_idx = len(text)
        
        # Extract and clean up
        section_text = text[start_idx:end_idx].strip()
        # Remove comment markers
        section_text = section_text.replace("# ", "").replace("#", "")
        
        return section_text.strip()
    except Exception:
        return ""
```

## Dependency Documentation Management

The agent handles dependency documentation extraction carefully:

```python
def _extract_dependencies(self, text: str) -> List[Dict[str, str]]:
    """Extract dependency information from the header text"""
    dependencies_section = self._extract_section(text, "[Dependencies]")
    dependencies = []
    
    for line in dependencies_section.split('\n'):
        line = line.strip()
        if not line:
            continue
            
        if ":" in line:
            # Parse structured dependency with kind
            parts = line.split(":", 1)
            if len(parts) == 2:
                kind = parts[0].strip().strip("<>")
                path = parts[1].strip()
                dependencies.append({
                    "kind": kind,
                    "dependency": path
                })
        else:
            # Default to unknown kind
            dependencies.append({
                "kind": "unknown",
                "dependency": line
            })
    
    return dependencies
```

## Claude 3.7 Reasoning Capabilities

The agent leverages Claude 3.7's reasoning abilities to:

1. **Infer Intent** - Deduce file and function purpose from implementation
2. **Extract Principles** - Identify design patterns and architectural choices
3. **Identify Constraints** - Recognize limitations and requirements
4. **Establish Relationships** - Understand how components interact
5. **Maintain Consistency** - Ensure documentation aligns with implementation

This reasoning is critical for producing high-quality documentation that truly represents the code's purpose and structure.

## Integration with HSTC Manager

The Documentation Generator Agent integrates with the HSTC Manager:

```python
def get_generated_documentation(self, file_path: str) -> Optional[Dict[str, Any]]:
    """
    Get generated documentation for a specific file
    
    Args:
        file_path: Path to the file
        
    Returns:
        Dict containing documentation or None if not available
    """
    return self.generated_documentation.get(file_path)

def get_all_documentation(self) -> Dict[str, Dict[str, Any]]:
    """
    Get all generated documentation
    
    Returns:
        Dict mapping file paths to documentation
    """
    return self.generated_documentation
```

## Documentation Quality Checks

The agent performs several quality checks on generated documentation:

```python
def validate_documentation(self, file_path: str) -> Dict[str, Any]:
    """
    Validate documentation against HSTC standards
    
    Args:
        file_path: Path to the file with documentation to validate
        
    Returns:
        Dict containing validation results
    """
    doc = self.generated_documentation.get(file_path)
    if not doc:
        return {"valid": False, "reason": "No documentation found for this file"}
    
    # Initialize validation results
    validation = {
        "valid": True,
        "issues": [],
        "file_path": file_path
    }
    
    # Check file header required sections
    header = doc.get("file_header", {})
    for section in ["intent", "design_principles", "constraints"]:
        if not header.get(section):
            validation["valid"] = False
            validation["issues"].append(f"Missing or empty {section} section in file header")
    
    # Check individual definitions
    for definition in doc.get("definitions", []):
        updated_comment = definition.get("updated_comment", "")
        
        # Check required sections
        if "[Function/Class method/Class intent]" not in updated_comment and \
           "[Function intent]" not in updated_comment and \
           "[Class intent]" not in updated_comment and \
           "[Class method intent]" not in updated_comment:
            validation["valid"] = False
            validation["issues"].append(f"Missing intent section in {definition.get('name')} documentation")
            
        if "[Design principles]" not in updated_comment:
            validation["valid"] = False
            validation["issues"].append(f"Missing design principles in {definition.get('name')} documentation")
            
        if "[Implementation details]" not in updated_comment:
            validation["valid"] = False
            validation["issues"].append(f"Missing implementation details in {definition.get('name')} documentation")
    
    return validation
```

## Comparison with Nova Micro

While the File Analyzer Agent uses Nova Micro for efficient classification and extraction, the Documentation Generator Agent requires Claude 3.7's more advanced capabilities:

1. **Deeper Understanding** - Claude 3.7 can better comprehend code logic and purpose
2. **Quality Writing** - More nuanced and detailed documentation generation
3. **Reasoning** - Step-by-step reasoning for documentation decisions
4. **Context Integration** - Better incorporation of dependency information
5. **Standard Adherence** - Stronger ability to follow HSTC documentation patterns

This division of labor allows the system to use the right model for each task, optimizing both quality and efficiency.
