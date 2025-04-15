# Internal LLM Tools Implementation Plan

## Overview

This document outlines the implementation plan for the Internal LLM Tools component, which provides specialized tools for extracting and processing different types of context within the Documentation-Based Programming system.

## Documentation Context

This implementation is based on the following documentation:
- [DESIGN.md](../../doc/DESIGN.md) - MCP Server Implementation section
- [design/INTERNAL_LLM_TOOLS.md](../../doc/design/INTERNAL_LLM_TOOLS.md) - Detailed specification
- [design/LLM_COORDINATION.md](../../doc/design/LLM_COORDINATION.md) - LLM Coordination Architecture
- [SECURITY.md](../../doc/SECURITY.md) - Security considerations
- [doc/llm/prompts/README.md](../../doc/llm/prompts/README.md) - Prompt templates structure

## Requirements

The Internal LLM Tools component must:
1. Implement five specialized internal tools as specified in the documentation
2. Each tool must use its own dedicated LLM instance with specialized prompts
3. Process different types of context (codebase, documentation, etc.)
4. Integrate with the LLM Coordinator component
5. Implement proper error handling and recovery strategies
6. Support budget constraints and timeout management
7. Adhere to security principles defined in SECURITY.md

## Design

### Internal Tools Architecture

Each internal tool follows a similar architecture pattern:

```
┌─────────────────────┐      ┌─────────────────────┐      ┌─────────────────────┐
│                     │      │                     │      │                     │
│  Context Assembler  │─────▶│  LLM Instance       │─────▶│  Response Parser    │
│                     │      │                     │      │                     │
└─────────────────────┘      └─────────────────────┘      └─────────────────────┘
          │                                                        │
          │                                                        │
          ▼                                                        ▼
┌─────────────────────┐                                 ┌─────────────────────┐
│                     │                                 │                     │
│  File Access        │                                 │  Result Formatter   │
│                     │                                 │                     │
└─────────────────────┘                                 └─────────────────────┘
```

### Core Components

The internal tools system provides these five specialized tools:

1. **coordinator_get_codebase_context**
   - **Purpose**: Extract relevant file header information based on query context
   - **Implementation**: Dedicated Amazon Nova Lite instance
   - **Context Construction**: File headers focusing on "[Source file intent]" and "[Reference documentation]" sections

2. **coordinator_get_codebase_changelog_context**
   - **Purpose**: Analyze historical code changes across the codebase
   - **Implementation**: Dedicated Amazon Nova Lite instance
   - **Context Construction**: All "[GenAI tool change history]" sections from file headers

3. **coordinator_get_documentation_context**
   - **Purpose**: Answer questions about project documentation
   - **Implementation**: Dedicated Amazon Nova Lite instance
   - **Context Construction**: Content of all documentation markdown files

4. **coordinator_get_documentation_changelog_context**
   - **Purpose**: Analyze historical documentation changes
   - **Implementation**: Dedicated Amazon Nova Lite instance
   - **Context Construction**: All MARKDOWN_CHANGELOG.md file contents

5. **coordinator_get_expert_architect_advice**
   - **Purpose**: Provide advanced architectural reasoning and guidance
   - **Implementation**: Claude 3.7 Sonnet
   - **Context Construction**: All sections from relevant file headers

### Core Classes and Interfaces

1. **InternalToolsComponent**

```python
class InternalToolsComponent(Component):
    """Component for internal LLM tools."""
    
    @property
    def name(self) -> str:
        return "internal_tools"
    
    @property
    def dependencies(self) -> list[str]:
        return ["llm_coordinator"]
    
    def initialize(self, context: InitializationContext) -> None:
        """Initialize the internal tools component."""
        self.config = context.config.internal_tools
        self.logger = context.logger.get_child("internal_tools")
        self.llm_coordinator_component = context.get_component("llm_coordinator")
        
        # Create the context assemblers
        self.codebase_context_assembler = CodebaseContextAssembler(self.logger)
        self.codebase_changelog_assembler = CodebaseChangelogAssembler(self.logger)
        self.documentation_context_assembler = DocumentationContextAssembler(self.logger)
        self.documentation_changelog_assembler = DocumentationChangelogAssembler(self.logger)
        self.expert_advice_assembler = ExpertAdviceContextAssembler(self.logger)
        
        # Create the LLM instances
        self.nova_lite_instance = NovaLiteInstance(
            config=self.config.nova_lite,
            logger=self.logger.get_child("nova_lite")
        )
        
        self.claude_instance = ClaudeInstance(
            config=self.config.claude,
            logger=self.logger.get_child("claude")
        )
        
        # Create the response parsers
        self.codebase_context_parser = CodebaseContextParser(self.logger)
        self.codebase_changelog_parser = CodebaseChangelogParser(self.logger)
        self.documentation_context_parser = DocumentationContextParser(self.logger)
        self.documentation_changelog_parser = DocumentationChangelogParser(self.logger)
        self.expert_advice_parser = ExpertAdviceParser(self.logger)
        
        # Create the result formatters
        self.codebase_context_formatter = CodebaseContextFormatter(self.logger)
        self.codebase_changelog_formatter = CodebaseChangelogFormatter(self.logger)
        self.documentation_context_formatter = DocumentationContextFormatter(self.logger)
        self.documentation_changelog_formatter = DocumentationChangelogFormatter(self.logger)
        self.expert_advice_formatter = ExpertAdviceFormatter(self.logger)
        
        # Create the file access service
        self.file_access = FileAccessService(self.logger)
        
        # Create the prompt loaders
        self.prompt_loader = PromptLoader(
            prompt_dir=self.config.prompt_templates_dir,
            logger=self.logger
        )
        
        # Load the prompt templates
        self._load_prompt_templates()
        
        # Register the tools with the LLM coordinator
        self._register_tools()
        
        self._initialized = True
    
    def _load_prompt_templates(self) -> None:
        """Load the prompt templates for all tools."""
        self.codebase_context_prompt = self.prompt_loader.load_prompt(
            "coordinator_get_codebase_context.txt"
        )
        self.codebase_changelog_prompt = self.prompt_loader.load_prompt(
            "coordinator_get_codebase_changelog_context.txt"
        )
        self.documentation_context_prompt = self.prompt_loader.load_prompt(
            "coordinator_get_documentation_context.txt"
        )
        self.documentation_changelog_prompt = self.prompt_loader.load_prompt(
            "coordinator_get_documentation_changelog_context.txt"
        )
        self.expert_advice_prompt = self.prompt_loader.load_prompt(
            "coordinator_get_expert_architect_advice.txt"
        )
    
    def _register_tools(self) -> None:
        """Register the tools with the LLM coordinator."""
        # This would be implemented in the actual code
        # In this implementation plan, we're just outlining the structure
        pass
    
    def get_codebase_context(self, job: InternalToolJob) -> Dict[str, Any]:
        """
        Get codebase context based on the query.
        
        Args:
            job: The internal tool job
        
        Returns:
            Dictionary with codebase context results
        """
        if not self._initialized:
            raise ComponentNotInitializedError(self.name)
        
        self.logger.info(f"Getting codebase context for job: {job.job_id}")
        
        try:
            # Assemble context
            context = self.codebase_context_assembler.assemble(
                job.parameters,
                self.file_access
            )
            
            # Create prompt
            prompt = self._create_codebase_context_prompt(job.parameters, context)
            
            # Invoke LLM
            response = self.nova_lite_instance.invoke(
                prompt=prompt,
                max_tokens=job.parameters.get("max_tokens", self.config.nova_lite.max_tokens),
                temperature=job.parameters.get("temperature", self.config.nova_lite.temperature)
            )
            
            # Parse response
            parsed_response = self.codebase_context_parser.parse(response)
            
            # Format result
            result = self.codebase_context_formatter.format(parsed_response)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting codebase context: {e}")
            raise InternalToolError(f"Failed to get codebase context: {e}")
    
    def get_codebase_changelog_context(self, job: InternalToolJob) -> Dict[str, Any]:
        """
        Get codebase changelog context based on the query.
        
        Args:
            job: The internal tool job
        
        Returns:
            Dictionary with codebase changelog context results
        """
        if not self._initialized:
            raise ComponentNotInitializedError(self.name)
        
        self.logger.info(f"Getting codebase changelog context for job: {job.job_id}")
        
        try:
            # Assemble context
            context = self.codebase_changelog_assembler.assemble(
                job.parameters,
                self.file_access
            )
            
            # Create prompt
            prompt = self._create_codebase_changelog_prompt(job.parameters, context)
            
            # Invoke LLM
            response = self.nova_lite_instance.invoke(
                prompt=prompt,
                max_tokens=job.parameters.get("max_tokens", self.config.nova_lite.max_tokens),
                temperature=job.parameters.get("temperature", self.config.nova_lite.temperature)
            )
            
            # Parse response
            parsed_response = self.codebase_changelog_parser.parse(response)
            
            # Format result
            result = self.codebase_changelog_formatter.format(parsed_response)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting codebase changelog context: {e}")
            raise InternalToolError(f"Failed to get codebase changelog context: {e}")
    
    def get_documentation_context(self, job: InternalToolJob) -> Dict[str, Any]:
        """
        Get documentation context based on the query.
        
        Args:
            job: The internal tool job
        
        Returns:
            Dictionary with documentation context results
        """
        if not self._initialized:
            raise ComponentNotInitializedError(self.name)
        
        self.logger.info(f"Getting documentation context for job: {job.job_id}")
        
        try:
            # Assemble context
            context = self.documentation_context_assembler.assemble(
                job.parameters,
                self.file_access
            )
            
            # Create prompt
            prompt = self._create_documentation_context_prompt(job.parameters, context)
            
            # Invoke LLM
            response = self.nova_lite_instance.invoke(
                prompt=prompt,
                max_tokens=job.parameters.get("max_tokens", self.config.nova_lite.max_tokens),
                temperature=job.parameters.get("temperature", self.config.nova_lite.temperature)
            )
            
            # Parse response
            parsed_response = self.documentation_context_parser.parse(response)
            
            # Format result
            result = self.documentation_context_formatter.format(parsed_response)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting documentation context: {e}")
            raise InternalToolError(f"Failed to get documentation context: {e}")
    
    def get_documentation_changelog_context(self, job: InternalToolJob) -> Dict[str, Any]:
        """
        Get documentation changelog context based on the query.
        
        Args:
            job: The internal tool job
        
        Returns:
            Dictionary with documentation changelog context results
        """
        if not self._initialized:
            raise ComponentNotInitializedError(self.name)
        
        self.logger.info(f"Getting documentation changelog context for job: {job.job_id}")
        
        try:
            # Assemble context
            context = self.documentation_changelog_assembler.assemble(
                job.parameters,
                self.file_access
            )
            
            # Create prompt
            prompt = self._create_documentation_changelog_prompt(job.parameters, context)
            
            # Invoke LLM
            response = self.nova_lite_instance.invoke(
                prompt=prompt,
                max_tokens=job.parameters.get("max_tokens", self.config.nova_lite.max_tokens),
                temperature=job.parameters.get("temperature", self.config.nova_lite.temperature)
            )
            
            # Parse response
            parsed_response = self.documentation_changelog_parser.parse(response)
            
            # Format result
            result = self.documentation_changelog_formatter.format(parsed_response)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting documentation changelog context: {e}")
            raise InternalToolError(f"Failed to get documentation changelog context: {e}")
    
    def get_expert_architect_advice(self, job: InternalToolJob) -> Dict[str, Any]:
        """
        Get expert architect advice based on the query.
        
        Args:
            job: The internal tool job
        
        Returns:
            Dictionary with expert architect advice results
        """
        if not self._initialized:
            raise ComponentNotInitializedError(self.name)
        
        self.logger.info(f"Getting expert architect advice for job: {job.job_id}")
        
        try:
            # Assemble context
            context = self.expert_advice_assembler.assemble(
                job.parameters,
                self.file_access
            )
            
            # Create prompt
            prompt = self._create_expert_advice_prompt(job.parameters, context)
            
            # Invoke LLM (using Claude for this tool)
            response = self.claude_instance.invoke(
                prompt=prompt,
                max_tokens=job.parameters.get("max_tokens", self.config.claude.max_tokens),
                temperature=job.parameters.get("temperature", self.config.claude.temperature)
            )
            
            # Parse response
            parsed_response = self.expert_advice_parser.parse(response)
            
            # Format result
            result = self.expert_advice_formatter.format(parsed_response)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting expert architect advice: {e}")
            raise InternalToolError(f"Failed to get expert architect advice: {e}")
    
    def _create_codebase_context_prompt(self, parameters: Dict, context: Dict) -> str:
        """Create a prompt for the codebase context tool."""
        return self.codebase_context_prompt.format(
            query=parameters.get("query", ""),
            file_list=context.get("file_list", ""),
            file_headers=context.get("file_headers", ""),
            reference_documentation=context.get("reference_documentation", "")
        )
    
    def _create_codebase_changelog_prompt(self, parameters: Dict, context: Dict) -> str:
        """Create a prompt for the codebase changelog context tool."""
        return self.codebase_changelog_prompt.format(
            query=parameters.get("query", ""),
            change_history=context.get("change_history", "")
        )
    
    def _create_documentation_context_prompt(self, parameters: Dict, context: Dict) -> str:
        """Create a prompt for the documentation context tool."""
        return self.documentation_context_prompt.format(
            query=parameters.get("query", ""),
            documentation_content=context.get("documentation_content", "")
        )
    
    def _create_documentation_changelog_prompt(self, parameters: Dict, context: Dict) -> str:
        """Create a prompt for the documentation changelog context tool."""
        return self.documentation_changelog_prompt.format(
            query=parameters.get("query", ""),
            changelog_content=context.get("changelog_content", "")
        )
    
    def _create_expert_advice_prompt(self, parameters: Dict, context: Dict) -> str:
        """Create a prompt for the expert architect advice tool."""
        return self.expert_advice_prompt.format(
            query=parameters.get("query", ""),
            file_headers=context.get("file_headers", ""),
            documentation_content=context.get("documentation_content", ""),
            change_history=context.get("change_history", "")
        )
    
    def shutdown(self) -> None:
        """Shutdown the component gracefully."""
        self.logger.info("Shutting down internal tools component")
        
        if hasattr(self, 'nova_lite_instance'):
            self.nova_lite_instance.shutdown()
        
        if hasattr(self, 'claude_instance'):
            self.claude_instance.shutdown()
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized
```

2. **Context Assemblers**

```python
class ContextAssembler(ABC):
    """Abstract base class for context assemblers."""
    
    def __init__(self, logger: Logger):
        self.logger = logger
    
    @abstractmethod
    def assemble(self, parameters: Dict, file_access: FileAccessService) -> Dict:
        """
        Assemble context for the tool.
        
        Args:
            parameters: Tool parameters
            file_access: File access service
        
        Returns:
            Dictionary with assembled context
        """
        pass


class CodebaseContextAssembler(ContextAssembler):
    """Assembles context for the codebase context tool."""
    
    def assemble(self, parameters: Dict, file_access: FileAccessService) -> Dict:
        """Assemble context for the codebase context tool."""
        self.logger.info("Assembling codebase context")
        
        # Get list of files
        file_list = file_access.list_files()
        
        # Get file headers
        file_headers = []
        for file_path in file_list[:100]:  # Limit to 100 files for now
            try:
                content = file_access.read_file(file_path)
                header = self._extract_header(content)
                if header:
                    file_headers.append({
                        "path": file_path,
                        "header": header
                    })
            except Exception as e:
                self.logger.warning(f"Error reading file {file_path}: {e}")
        
        # Get reference documentation
        reference_documentation = []
        for doc_path in file_access.list_files("doc"):
            try:
                content = file_access.read_file(f"doc/{doc_path}")
                reference_documentation.append({
                    "path": f"doc/{doc_path}",
                    "content": content[:1000]  # First 1000 characters
                })
            except Exception as e:
                self.logger.warning(f"Error reading doc file doc/{doc_path}: {e}")
        
        return {
            "file_list": file_list,
            "file_headers": file_headers,
            "reference_documentation": reference_documentation
        }
    
    def _extract_header(self, content: str) -> Optional[str]:
        """Extract header from file content."""
        # This is a placeholder implementation
        # In the real implementation, this would use regex or other parsing techniques
        if "###############################################################################" in content:
            header_end = content.find("###############################################################################", 100)
            if header_end > 0:
                return content[:header_end]
        
        return None


class CodebaseChangelogAssembler(ContextAssembler):
    """Assembles context for the codebase changelog context tool."""
    
    def assemble(self, parameters: Dict, file_access: FileAccessService) -> Dict:
        """Assemble context for the codebase changelog context tool."""
        self.logger.info("Assembling codebase changelog context")
        
        # Get list of files
        file_list = file_access.list_files()
        
        # Get change history
        change_history = []
        for file_path in file_list[:100]:  # Limit to 100 files for now
            try:
                content = file_access.read_file(file_path)
                history = self._extract_change_history(content)
                if history:
                    change_history.append({
                        "path": file_path,
                        "history": history
                    })
            except Exception as e:
                self.logger.warning(f"Error reading file {file_path}: {e}")
        
        return {
            "change_history": change_history
        }
    
    def _extract_change_history(self, content: str) -> Optional[str]:
        """Extract change history from file content."""
        # This is a placeholder implementation
        # In the real implementation, this would use regex or other parsing techniques
        if "[GenAI tool change history]" in content:
            history_start = content.find("[GenAI tool change history]")
            history_end = content.find("###############################################################################", history_start)
            if history_end > 0:
                return content[history_start:history_end]
        
        return None


class DocumentationContextAssembler(ContextAssembler):
    """Assembles context for the documentation context tool."""
    
    def assemble(self, parameters: Dict, file_access: FileAccessService) -> Dict:
        """Assemble context for the documentation context tool."""
        self.logger.info("Assembling documentation context")
        
        # Get documentation content
        documentation_content = []
        for doc_path in file_access.list_files("doc"):
            try:
                if doc_path.endswith(".md") and "MARKDOWN_CHANGELOG.md" not in doc_path:
                    content = file_access.read_file(f"doc/{doc_path}")
                    documentation_content.append({
                        "path": f"doc/{doc_path}",
                        "content": content
                    })
            except Exception as e:
                self.logger.warning(f"Error reading doc file doc/{doc_path}: {e}")
        
        return {
            "documentation_content": documentation_content
        }


class DocumentationChangelogAssembler(ContextAssembler):
    """Assembles context for the documentation changelog context tool."""
    
    def assemble(self, parameters: Dict, file_access: FileAccessService) -> Dict:
        """Assemble context for the documentation changelog context tool."""
        self.logger.info("Assembling documentation changelog context")
        
        # Get changelog content
        changelog_content = []
        for doc_path in file_access.list_files("doc"):
            try:
                if "MARKDOWN_CHANGELOG.md" in doc_path:
                    content = file_access.read_file(f"doc/{doc_path}")
                    changelog_content.append({
                        "path": f"doc/{doc_path}",
                        "content": content
                    })
            except Exception as e:
                self.logger.warning(f"Error reading changelog file doc/{doc_path}: {e}")
        
        return {
            "changelog_content": changelog_content
        }


class ExpertAdviceContextAssembler(ContextAssembler):
    """Assembles context for the expert architect advice tool."""
    
    def assemble(self, parameters: Dict, file_access: FileAccessService) -> Dict:
        """Assemble context for the expert architect advice tool."""
        self.logger.info("Assembling expert advice context")
        
        # Get file headers
        file_list = file_access.list_files()
        file_headers = []
        for file_path in file_list[:50]:  # Limit to 50 files for now
            try:
                content = file_access.read_file(file_path)
                header = self._extract_header(content)
                if header:
                    file_headers.append({
                        "path": file_path,
                        "header": header
                    })
            except Exception as e:
                self.logger.warning(f"Error reading file {file_path}: {e}")
        
        # Get documentation content
        documentation_content = []
        for doc_path in file_access.list_files("doc"):
            try:
                if doc_path.endswith(".md"):
                    content = file_access.read_file(f"doc/{doc_path}")
                    documentation_content.append({
                        "path": f"doc/{doc_path}",
                        "content": content
                    })
            except Exception as e:
                self.logger.warning(f"Error reading doc file doc/{doc_path}: {e}")
        
        # Get change history
        change_history = []
        for file_path in file_list[:50]:  # Limit to 50 files for now
            try:
                content = file_access.read_file(file_path)
                history = self._extract_change_history(content)
                if history:
                    change_history.append({
                        "path": file_path,
                        "history": history
                    })
            except Exception as e:
                self.logger.warning(f"Error reading file {file_path}: {e}")
        
        return {
            "file_headers": file_headers,
            "documentation_content": documentation_content,
            "change_history": change_history
        }
    
    def _extract_header(self, content: str) -> Optional[str]:
        """Extract header from file content."""
        # This is a placeholder implementation
        # In the real implementation, this would use regex or other parsing techniques
        if "###############################################################################" in content:
            header_end = content.find("###############################################################################", 100)
            if header_end > 0:
                return content[:header_end]
        
        return None
    
    def _extract_change_history(self, content: str) -> Optional[str]:
        """Extract change history from file content."""
        # This is a placeholder implementation
        # In the real implementation, this would use regex or other parsing techniques
        if "[GenAI tool change history]" in content:
            history_start = content.find("[GenAI tool change history]")
            history_end = content.find("###############################################################################", history_start)
            if history_end > 0:
                return content[history_start:history_end]
        
        return None
```

3. **LLM Instances**

```python
class LLMInstance(ABC):
    """Abstract base class for LLM instances."""
    
    def __init__(self, config: Dict, logger: Logger):
        self.config = config
        self.logger = logger
    
    @abstractmethod
    def invoke(self, prompt: str, max_tokens: int, temperature: float) -> str:
        """
        Invoke the LLM instance.
        
        Args:
            prompt: The prompt to send to the LLM
            max_tokens: Maximum tokens to generate
            temperature: Temperature parameter
        
        Returns:
            LLM response as a string
        """
        pass
    
    @abstractmethod
    def shutdown(self) -> None:
        """Shutdown the LLM instance."""
        pass


class NovaLiteInstance(LLMInstance):
    """Amazon Nova Lite LLM instance."""
    
    def __init__(self, config: Dict, logger: Logger):
        super().__init__(config, logger)
        self._client = self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the AWS Bedrock client."""
        self.logger.info(f"Initializing AWS Bedrock client for model {self.config.model_id}")
        
        # This is a placeholder
        # In the real implementation, this would initialize the AWS Bedrock client
        return None
    
    def invoke(self, prompt: str, max_tokens: int, temperature: float) -> str:
        """Invoke the Nova Lite model."""
        self.logger.debug(f"Invoking Nova Lite model with prompt: {prompt[:100]}...")
        
        # This is a placeholder
        # In the real implementation, this would call the AWS Bedrock API
        return f"Mock response from Nova Lite model"
    
    def shutdown(self) -> None:
        """Shutdown the LLM instance."""
        self.logger.info("Shutting down Nova Lite instance")
        # Cleanup resources if needed


class ClaudeInstance(LLMInstance):
    """Claude LLM instance."""
    
    def __init__(self, config: Dict, logger: Logger):
        super().__init__(config, logger)
        self._client = self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the AWS Bedrock client for Claude."""
        self.logger.info(f"Initializing AWS Bedrock client for model {self.config.model_id}")
        
        # This is a placeholder
        # In the real implementation, this would initialize the AWS Bedrock client
        return None
    
    def invoke(self, prompt: str, max_tokens: int, temperature: float) -> str:
        """Invoke the Claude model."""
        self.logger.debug(f"Invoking Claude model with prompt: {prompt[:100]}...")
        
        # This is a placeholder
        # In the real implementation, this would call the AWS Bedrock API
        return f"Mock response from Claude model"
    
    def shutdown(self) -> None:
        """Shutdown the LLM instance."""
        self.logger.info("Shutting down Claude instance")
        # Cleanup resources if needed
```

4. **Response Parsers and Formatters**

```python
class ResponseParser(ABC):
    """Abstract base class for response parsers."""
    
    def __init__(self, logger: Logger):
        self.logger = logger
    
    @abstractmethod
    def parse(self, response: str) -> Dict:
        """
        Parse the LLM response.
        
        Args:
            response: LLM response string
        
        Returns:
            Parsed response as a dictionary
        """
        pass


class CodebaseContextParser(ResponseParser):
    """Parser for codebase context responses."""
    
    def parse(self, response: str) -> Dict:
        """Parse the codebase context response."""
        # This is a placeholder implementation
        # In the real implementation, this would parse the LLM response
        
        try:
            # Try to parse as JSON
            return json.loads(response)
        except:
            # If not JSON, create a simple structure
            return {
                "relevant_files": [
                    {
                        "path": "src/main.py",
                        "intent": "Entry point for the application"
                    }
                ],
                "codebase_organization": {
                    "structure": "Standard Python package structure"
                }
            }


class CodebaseChangelogParser(ResponseParser):
    """Parser for codebase changelog responses."""
    
    def parse(self, response: str) -> Dict:
        """Parse the codebase changelog response."""
        # This is a placeholder implementation
        # In the real implementation, this would parse the LLM response
        
        try:
            # Try to parse as JSON
            return json.loads(response)
        except:
            # If not JSON, create a simple structure
            return {
                "recent_changes": [
                    {
                        "timestamp": "2025-04-10T14:30:00Z",
                        "file": "src/api.py",
                        "summary": "Added authentication endpoints"
                    },
                    {
                        "timestamp": "2025-04-12T09:15:00Z",
                        "file": "src/models.py",
                        "summary": "Updated user model with MFA support"
                    }
                ]
            }


class DocumentationContextParser(ResponseParser):
    """Parser for documentation context responses."""
    
    def parse(self, response: str) -> Dict:
        """Parse the documentation context response."""
        # This is a placeholder implementation
        # In the real implementation, this would parse the LLM response
        
        try:
            # Try to parse as JSON
            return json.loads(response)
        except:
            # If not JSON, create a simple structure
            return {
                "relevant_docs": [
                    {
                        "path": "doc/DESIGN.md",
                        "summary": "Overall system design and architecture"
                    },
                    {
                        "path": "doc/API.md",
                        "summary": "API documentation and usage examples"
                    }
                ],
                "relationships": {
                    "DESIGN.md": ["API.md", "SECURITY.md"],
                    "API.md": ["CONFIGURATION.md"]
                }
            }


class DocumentationChangelogParser(ResponseParser):
    """Parser for documentation changelog responses."""
    
    def parse(self, response: str) -> Dict:
        """Parse the documentation changelog response."""
        # This is a placeholder implementation
        # In the real implementation, this would parse the LLM response
        
        try:
            # Try to parse as JSON
            return json.loads(response)
        except:
            # If not JSON, create a simple structure
            return {
                "recent_doc_changes": [
                    {
                        "timestamp": "2025-04-08T16:45:00Z",
                        "file": "doc/API.md",
                        "summary": "Updated API documentation with authentication details"
                    },
                    {
                        "timestamp": "2025-04-11T10:20:00Z",
                        "file": "doc/SECURITY.md",
                        "summary": "Added MFA security considerations"
                    }
                ]
            }


class ExpertAdviceParser(ResponseParser):
    """Parser for expert architect advice responses."""
    
    def parse(self, response: str) -> Dict:
        """Parse the expert architect advice response."""
        # This is a placeholder implementation
        # In the real implementation, this would parse the LLM response
        
        try:
            # Try to parse as JSON
            return json.loads(response)
        except:
            # If not JSON, create a simple structure
            return {
                "advice": "Based on the codebase analysis, I recommend implementing the feature using the existing authentication framework rather than creating a new one.",
                "rationale": "The current framework already supports the required functionality and has been thoroughly tested.",
                "implementation_approach": [
                    "Extend the UserModel class",
                    "Add new methods to AuthenticationService",
                    "Update API documentation"
                ]
            }


class ResultFormatter(ABC):
    """Abstract base class for result formatters."""
    
    def __init__(self, logger: Logger):
        self.logger = logger
    
    @abstractmethod
    def format(self, parsed_response: Dict) -> Dict:
        """
        Format the parsed response.
        
        Args:
            parsed_response: Parsed LLM response
        
        Returns:
            Formatted result as a dictionary
        """
        pass


class CodebaseContextFormatter(ResultFormatter):
    """Formatter for codebase context results."""
    
    def format(self, parsed_response: Dict) -> Dict:
        """Format the codebase context result."""
        # This is a placeholder implementation
        # In the real implementation, this would format the parsed response
        
        return {
            "relevant_files": parsed_response.get("relevant_files", []),
            "codebase_organization": parsed_response.get("codebase_organization", {}),
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "tool": "coordinator_get_codebase_context"
            }
        }


class CodebaseChangelogFormatter(ResultFormatter):
    """Formatter for codebase changelog results."""
    
    def format(self, parsed_response: Dict) -> Dict:
        """Format the codebase changelog result."""
        # This is a placeholder implementation
        # In the real implementation, this would format the parsed response
        
        return {
            "recent_changes": parsed_response.get("recent_changes", []),
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "tool": "coordinator_get_codebase_changelog_context"
            }
        }


class DocumentationContextFormatter(ResultFormatter):
    """Formatter for documentation context results."""
    
    def format(self, parsed_response: Dict) -> Dict:
        """Format the documentation context result."""
        # This is a placeholder implementation
        # In the real implementation, this would format the parsed response
        
        return {
            "relevant_docs": parsed_response.get("relevant_docs", []),
            "relationships": parsed_response.get("relationships", {}),
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "tool": "coordinator_get_documentation_context"
            }
        }


class DocumentationChangelogFormatter(ResultFormatter):
    """Formatter for documentation changelog results."""
    
    def format(self, parsed_response: Dict) -> Dict:
        """Format the documentation changelog result."""
        # This is a placeholder implementation
        # In the real implementation, this would format the parsed response
        
        return {
            "recent_doc_changes": parsed_response.get("recent_doc_changes", []),
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "tool": "coordinator_get_documentation_changelog_context"
            }
        }


class ExpertAdviceFormatter(ResultFormatter):
    """Formatter for expert architect advice results."""
    
    def format(self, parsed_response: Dict) -> Dict:
        """Format the expert architect advice result."""
        # This is a placeholder implementation
        # In the real implementation, this would format the parsed response
        
        return {
            "advice": parsed_response.get("advice", ""),
            "rationale": parsed_response.get("rationale", ""),
            "implementation_approach": parsed_response.get("implementation_approach", []),
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "tool": "coordinator_get_expert_architect_advice"
            }
        }
```

5. **FileAccessService**

```python
class FileAccessService:
    """Service for accessing files in the filesystem."""
    
    def __init__(self, logger: Logger):
        self.logger = logger
    
    def list_files(self, directory: str = "") -> List[str]:
        """
        List files in a directory.
        
        Args:
            directory: Directory to list files from (relative to project root)
        
        Returns:
            List of file paths
        """
        try:
            if not directory:
                # List files in project root
                result = []
                for root, dirs, files in os.walk("."):
                    for file in files:
                        result.append(os.path.join(root, file))
                return result
            else:
                # List files in specified directory
                result = []
                for root, dirs, files in os.walk(directory):
                    for file in files:
                        result.append(os.path.join(root, file))
                return result
        except Exception as e:
            self.logger.error(f"Error listing files in directory {directory}: {e}")
            return []
    
    def read_file(self, file_path: str) -> str:
        """
        Read a file.
        
        Args:
            file_path: Path to the file
        
        Returns:
            File content as a string
        
        Raises:
            FileNotFoundError: If the file does not exist
            IOError: If the file cannot be read
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"Error reading file {file_path}: {e}")
            raise
```

6. **PromptLoader**

```python
class PromptLoader:
    """Loader for prompt templates."""
    
    def __init__(self, prompt_dir: str, logger: Logger):
        self.prompt_dir = prompt_dir
        self.logger = logger
        self._cache = {}
    
    def load_prompt(self, prompt_name: str) -> str:
        """
        Load a prompt template.
        
        Args:
            prompt_name: Name of the prompt template
        
        Returns:
            Prompt template as a string
        
        Raises:
            FileNotFoundError: If the prompt template does not exist
            IOError: If the prompt template cannot be read
        """
        # Check cache first
        if prompt_name in self._cache:
            return self._cache[prompt_name]
        
        try:
            # Load prompt template
            prompt_path = os.path.join(self.prompt_dir, prompt_name)
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt_template = f.read()
            
            # Cache prompt template
            self._cache[prompt_name] = prompt_template
            
            return prompt_template
        except Exception as e:
            self.logger.error(f"Error loading prompt template {prompt_name}: {e}")
            raise
```

### Configuration Classes

```python
@dataclass
class NovaLiteConfig:
    """Configuration for Amazon Nova Lite."""
    
    model_id: str  # AWS Bedrock model ID
    temperature: float  # Temperature parameter for LLM
    max_tokens: int  # Maximum tokens for LLM response
    retry_limit: int  # Maximum number of retries
    retry_delay_seconds: int  # Delay between retries


@dataclass
class ClaudeConfig:
    """Configuration for Claude."""
    
    model_id: str  # AWS Bedrock model ID
    temperature: float  # Temperature parameter for LLM
    max_tokens: int  # Maximum tokens for LLM response
    retry_limit: int  # Maximum number of retries
    retry_delay_seconds: int  # Delay between retries


@dataclass
class InternalToolsConfig:
    """Configuration for internal LLM tools."""
    
    nova_lite: NovaLiteConfig
    claude: ClaudeConfig
    prompt_templates_dir: str  # Directory containing prompt templates
```

Default configuration values:

| Parameter | Description | Default | Valid Values |
|-----------|-------------|---------|-------------|
| `nova_lite.model_id` | AWS Bedrock model ID | `"amazon.nova-lite-v3"` | Valid model ID |
| `nova_lite.temperature` | Temperature parameter | `0.0` | `0.0-1.0` |
| `nova_lite.max_tokens` | Maximum tokens | `4096` | `1-8192` |
| `nova_lite.retry_limit` | Maximum number of retries | `3` | `0-10` |
| `nova_lite.retry_delay_seconds` | Delay between retries | `1` | `1-60` |
| `claude.model_id` | AWS Bedrock model ID | `"anthropic.claude-3-7-sonnet-20240229-v1:0"` | Valid model ID |
| `claude.temperature` | Temperature parameter | `0.0` | `0.0-1.0` |
| `claude.max_tokens` | Maximum tokens | `4096` | `1-8192` |
| `claude.retry_limit` | Maximum number of retries | `3` | `0-10` |
| `claude.retry_delay_seconds` | Delay between retries | `1` | `1-60` |
| `prompt_templates_dir` | Prompt templates directory | `"doc/llm/prompts"` | Valid directory path |

## Implementation Plan

### Phase 1: Core Structure
1. Implement InternalToolsComponent as a system component
2. Create configuration classes for Nova Lite and Claude models
3. Implement PromptLoader for loading prompt templates
4. Implement FileAccessService for accessing files

### Phase 2: Context Assemblers
1. Implement abstract ContextAssembler base class
2. Create specialized context assemblers for each tool
3. Implement file header extraction
4. Implement change history extraction

### Phase 3: LLM Integration
1. Implement abstract LLMInstance base class
2. Create NovaLiteInstance with AWS Bedrock integration
3. Create ClaudeInstance with AWS Bedrock integration
4. Implement retry logic and error handling

### Phase 4: Response Handling
1. Implement abstract ResponseParser base class
2. Create specialized response parsers for each tool
3. Implement abstract ResultFormatter base class
4. Create specialized result formatters for each tool

## Security Considerations

The Internal LLM Tools component implements these security measures:
- Secure handling of AWS Bedrock credentials
- No external data transmission outside AWS
- Validation of all file inputs
- Resource constraints through prompt size limitations
- Error isolation through component architecture
- Thread safety for concurrent operations
- Protection against prompt injection attacks
- Proper handling of file permissions

## Testing Strategy

### Unit Tests
- Test each context assembler with mock file access
- Test each LLM instance with mock AWS clients
- Test each response parser with sample responses
- Test each result formatter with sample parsed responses

### Integration Tests
- Test end-to-end flow for each internal tool
- Test integration with LLM Coordinator
- Test error handling and recovery
- Test with various input parameters

### System Tests
- Test with real AWS Bedrock models
- Test performance with large codebases
- Test memory usage during operation

## Dependencies on Other Plans

This plan depends on:
- LLM Coordinator plan (for integration)
- Component Initialization plan (for component framework)

## Implementation Timeline

1. Core Structure - 2 days
2. Context Assemblers - 2 days
3. LLM Integration - 2 days
4. Response Handling - 2 days

Total: 8 days
