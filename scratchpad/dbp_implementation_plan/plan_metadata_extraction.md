# Metadata Extraction Implementation Plan

## Overview

This document outlines the implementation plan for the Metadata Extraction component, which is responsible for using Amazon Nova Lite LLM to extract structured metadata from source code files regardless of programming language.

## Documentation Context

This implementation is based on the following documentation:
- [DESIGN.md](../../doc/DESIGN.md) - Code Analysis Approach section
- [DATA_MODEL.md](../../doc/DATA_MODEL.md) - Metadata Extraction Model
- [DESIGN_DECISIONS.md](../../doc/DESIGN_DECISIONS.md) - LLM-Based Metadata Extraction decision
- [SECURITY.md](../../doc/SECURITY.md) - Security considerations
- [design/BACKGROUND_TASK_SCHEDULER.md](../../doc/design/BACKGROUND_TASK_SCHEDULER.md) - Metadata extraction process

## Requirements

The Metadata Extraction component must:
1. Extract metadata from source code files using Amazon Nova Lite LLM
2. Process any programming language without language-specific parsers
3. Extract header sections, function documentation, and design decisions
4. Implement the FileMetadata structure as defined in DATA_MODEL.md
5. Support the Background Task Scheduler workflow for efficient processing
6. Operate without any programmatic fallback for extraction (per DESIGN_DECISIONS.md)
7. Maintain strong security practices without transmitting code externally
8. Provide thread-safe access methods for other components

## Design

### Architecture Overview

The Metadata Extraction component follows a service-oriented architecture:

```
┌─────────────────────┐      ┌─────────────────────┐      ┌─────────────────────┐
│                     │      │                     │      │                     │
│ Metadata Extraction │─────▶│ LLM Prompt Manager  │─────▶│   Amazon Nova Lite  │
│     Service         │      │                     │      │     Integration     │
└─────────────────────┘      └─────────────────────┘      └─────────────────────┘
          │                                                        │
          │                                                        │
          ▼                                                        ▼
┌─────────────────────┐                                 ┌─────────────────────┐
│                     │                                 │                     │
│  Extraction Result  │◀────────────────────────────────│   Response Parser   │
│     Processor       │                                 │                     │
└─────────────────────┘                                 └─────────────────────┘
          │
          │
          ▼
┌─────────────────────┐
│                     │
│   Database Writer   │
│                     │
└─────────────────────┘
```

### Core Classes and Interfaces

1. **MetadataExtractionComponent**

```python
class MetadataExtractionComponent(Component):
    """Component for LLM-based metadata extraction."""
    
    @property
    def name(self) -> str:
        return "metadata_extraction"
    
    @property
    def dependencies(self) -> list[str]:
        return ["database"]
    
    def initialize(self, context: InitializationContext) -> None:
        """Initialize the metadata extraction component."""
        self.config = context.config.metadata_extraction
        self.logger = context.logger.get_child("metadata_extraction")
        self.db_component = context.get_component("database")
        
        # Create related services
        self.prompt_manager = LLMPromptManager(self.config, self.logger)
        self.bedrock_client = BedrockClient(self.config, self.logger)
        self.response_parser = ResponseParser(self.logger)
        self.result_processor = ExtractionResultProcessor(self.logger)
        self.db_writer = DatabaseWriter(self.db_component, self.logger)
        
        # Initialize the extraction service
        self.extraction_service = MetadataExtractionService(
            prompt_manager=self.prompt_manager,
            bedrock_client=self.bedrock_client,
            response_parser=self.response_parser,
            result_processor=self.result_processor,
            db_writer=self.db_writer,
            config=self.config,
            logger=self.logger
        )
        
        self._initialized = True
    
    def extract_metadata(self, file_path: str, file_content: str) -> Optional[FileMetadata]:
        """
        Extract metadata from a file using the LLM-based extraction service.
        
        Args:
            file_path: Path to the file
            file_content: Content of the file
        
        Returns:
            FileMetadata object or None if extraction failed
        """
        if not self._initialized:
            raise ComponentNotInitializedError(self.name)
        
        return self.extraction_service.extract(file_path, file_content)
    
    def shutdown(self) -> None:
        """Shutdown the component gracefully."""
        self.logger.info("Shutting down metadata extraction component")
        # Cleanup resources if needed
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized
```

2. **MetadataExtractionService**

```python
class MetadataExtractionService:
    """Service for extracting metadata from files using LLM."""
    
    def __init__(
        self,
        prompt_manager: LLMPromptManager,
        bedrock_client: BedrockClient,
        response_parser: ResponseParser,
        result_processor: ExtractionResultProcessor,
        db_writer: DatabaseWriter,
        config: MetadataExtractionConfig,
        logger: Logger
    ):
        self.prompt_manager = prompt_manager
        self.bedrock_client = bedrock_client
        self.response_parser = response_parser
        self.result_processor = result_processor
        self.db_writer = db_writer
        self.config = config
        self.logger = logger
        self._lock = threading.RLock()
    
    def extract(self, file_path: str, file_content: str) -> Optional[FileMetadata]:
        """
        Extract metadata from a file using LLM.
        
        Args:
            file_path: Path to the file
            file_content: Content of the file
        
        Returns:
            FileMetadata object or None if extraction failed
        """
        with self._lock:  # Ensure thread safety
            try:
                # Prepare prompt for LLM
                prompt = self.prompt_manager.create_extraction_prompt(file_path, file_content)
                
                # Call Amazon Nova Lite via AWS Bedrock
                llm_response = self.bedrock_client.invoke_model(prompt)
                
                # Parse the LLM response
                parsed_response = self.response_parser.parse(llm_response, file_path)
                
                # Process the extraction result
                metadata = self.result_processor.process(parsed_response, file_path, file_content)
                
                # Write to database
                self.db_writer.write(metadata)
                
                return metadata
            
            except Exception as e:
                self.logger.error(f"Metadata extraction failed for {file_path}: {e}")
                return None
```

3. **LLMPromptManager**

```python
class LLMPromptManager:
    """Manages prompt creation for LLM-based metadata extraction."""
    
    def __init__(self, config: MetadataExtractionConfig, logger: Logger):
        self.config = config
        self.logger = logger
        self.template_path = config.extraction_prompt_template
        self.output_schema_path = config.output_schema_template
        
        # Load templates
        self.extraction_template = self._load_template(self.template_path)
        self.output_schema = self._load_template(self.output_schema_path)
    
    def _load_template(self, path: str) -> str:
        """Load a template file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"Failed to load template {path}: {e}")
            raise TemplateLoadError(f"Failed to load template {path}: {e}")
    
    def create_extraction_prompt(self, file_path: str, file_content: str) -> str:
        """Create an extraction prompt for the given file."""
        # Get file extension to help LLM identify language
        _, extension = os.path.splitext(file_path)
        
        # Format the extraction prompt
        prompt = self.extraction_template.format(
            file_path=file_path,
            file_extension=extension,
            file_content=file_content,
            output_schema=self.output_schema
        )
        
        return prompt
```

4. **BedrockClient**

```python
class BedrockClient:
    """Client for interacting with AWS Bedrock for LLM services."""
    
    def __init__(self, config: MetadataExtractionConfig, logger: Logger):
        self.config = config
        self.logger = logger
        self.model_id = config.model_id
        self.max_retries = config.max_retries
        self.retry_delay = config.retry_delay
        
        # Initialize Bedrock client
        self.client = self._initialize_client()
    
    def _initialize_client(self):
        """Initialize AWS Bedrock client."""
        try:
            # No direct AWS credential handling per SECURITY.md
            # Use default credential provider chain
            return boto3.client('bedrock-runtime')
        except Exception as e:
            self.logger.error(f"Failed to initialize Bedrock client: {e}")
            raise BedrockClientInitializationError(f"Failed to initialize Bedrock client: {e}")
    
    def invoke_model(self, prompt: str) -> str:
        """Invoke the Amazon Nova Lite model with the given prompt."""
        retries = 0
        last_exception = None
        
        while retries <= self.max_retries:
            try:
                response = self.client.invoke_model(
                    modelId=self.model_id,
                    body=json.dumps({
                        "prompt": prompt,
                        "temperature": self.config.temperature,
                        "maxTokens": self.config.max_tokens
                    }),
                    contentType='application/json'
                )
                
                # Parse response
                response_body = json.loads(response['body'].read())
                return response_body['text']
            
            except Exception as e:
                retries += 1
                last_exception = e
                self.logger.warning(f"Bedrock invocation retry {retries}/{self.max_retries}: {e}")
                time.sleep(self.retry_delay * retries)  # Exponential backoff
        
        self.logger.error(f"Bedrock invocation failed after {self.max_retries} retries: {last_exception}")
        raise BedrockInvocationError(f"Bedrock invocation failed: {last_exception}")
```

5. **ResponseParser**

```python
class ResponseParser:
    """Parser for LLM responses to extract structured metadata."""
    
    def __init__(self, logger: Logger):
        self.logger = logger
    
    def parse(self, llm_response: str, file_path: str) -> dict:
        """
        Parse the LLM response into a structured dictionary.
        
        Args:
            llm_response: Raw response from the LLM
            file_path: Path of the processed file (for logging)
        
        Returns:
            Dictionary with parsed metadata
        """
        try:
            # The LLM is instructed to return JSON
            # Extract JSON content from the response (may be wrapped in markdown code blocks)
            json_content = self._extract_json(llm_response)
            
            # Parse JSON content
            parsed_data = json.loads(json_content)
            
            # Validate against expected schema
            self._validate_response_schema(parsed_data)
            
            return parsed_data
        
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse LLM response as JSON for {file_path}: {e}")
            self.logger.debug(f"Raw LLM response: {llm_response}")
            raise ResponseParsingError(f"Failed to parse LLM response as JSON: {e}")
        
        except ValidationError as e:
            self.logger.error(f"LLM response validation failed for {file_path}: {e}")
            raise ResponseValidationError(f"LLM response validation failed: {e}")
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON content from possibly markdown-formatted text."""
        # Check if response is wrapped in code blocks
        json_pattern = r"```(?:json)?(.*?)```"
        matches = re.findall(json_pattern, text, re.DOTALL)
        
        if matches:
            # Return the first JSON block found
            return matches[0].strip()
        else:
            # Assume the entire response is JSON
            return text.strip()
    
    def _validate_response_schema(self, data: dict) -> None:
        """Validate the response data against the expected schema."""
        # Define expected schema using pydantic FileMetadataSchema class
        # This will be implemented in the actual code
        # For now, just check for required top-level keys
        required_keys = ["path", "language", "headerSections", "functions", "classes"]
        
        for key in required_keys:
            if key not in data:
                raise ValidationError(f"Missing required field: {key}")
```

6. **ExtractionResultProcessor**

```python
class ExtractionResultProcessor:
    """Processes extraction results from LLM."""
    
    def __init__(self, logger: Logger):
        self.logger = logger
    
    def process(self, parsed_response: dict, file_path: str, file_content: str) -> FileMetadata:
        """
        Process the parsed LLM response into a FileMetadata object.
        
        Args:
            parsed_response: Parsed response from the LLM
            file_path: Path to the file
            file_content: Original file content
        
        Returns:
            FileMetadata object
        """
        try:
            # Create FileMetadata object from parsed response
            metadata = FileMetadata(
                path=file_path,
                language=parsed_response.get("language", "unknown"),
                header_sections=self._process_header_sections(parsed_response.get("headerSections", {})),
                functions=self._process_functions(parsed_response.get("functions", [])),
                classes=self._process_classes(parsed_response.get("classes", [])),
                size_bytes=len(file_content.encode('utf-8')),
                md5_digest=self._calculate_md5(file_content),
                last_modified=datetime.now(),
                extraction_timestamp=datetime.now()
            )
            
            return metadata
        
        except Exception as e:
            self.logger.error(f"Failed to process extraction results for {file_path}: {e}")
            raise ExtractionProcessingError(f"Failed to process extraction results: {e}")
    
    def _process_header_sections(self, header_sections: dict) -> HeaderSections:
        """Process header sections from parsed response."""
        return HeaderSections(
            intent=header_sections.get("intent", ""),
            design_principles=header_sections.get("designPrinciples", []),
            constraints=header_sections.get("constraints", []),
            reference_documentation=header_sections.get("referenceDocumentation", []),
            change_history=self._process_change_history(header_sections.get("changeHistory", []))
        )
    
    def _process_change_history(self, change_history: list) -> List[ChangeRecord]:
        """Process change history from parsed response."""
        records = []
        for record in change_history:
            try:
                records.append(ChangeRecord(
                    timestamp=self._parse_timestamp(record.get("timestamp", "")),
                    summary=record.get("summary", ""),
                    details=record.get("details", [])
                ))
            except Exception as e:
                # Log but continue processing other records
                self.logger.warning(f"Failed to process change record: {e}")
        
        return records
    
    def _process_functions(self, functions: list) -> List[FunctionMetadata]:
        """Process functions from parsed response."""
        result = []
        for func in functions:
            try:
                result.append(FunctionMetadata(
                    name=func.get("name", ""),
                    doc_sections=self._process_doc_sections(func.get("docSections", {})),
                    parameters=func.get("parameters", []),
                    line_range=self._process_line_range(func.get("lineRange", {}))
                ))
            except Exception as e:
                # Log but continue processing other functions
                self.logger.warning(f"Failed to process function metadata: {e}")
        
        return result
    
    def _process_classes(self, classes: list) -> List[ClassMetadata]:
        """Process classes from parsed response."""
        result = []
        for cls in classes:
            try:
                result.append(ClassMetadata(
                    name=cls.get("name", ""),
                    doc_sections=self._process_doc_sections(cls.get("docSections", {})),
                    methods=self._process_functions(cls.get("methods", [])),
                    line_range=self._process_line_range(cls.get("lineRange", {}))
                ))
            except Exception as e:
                # Log but continue processing other classes
                self.logger.warning(f"Failed to process class metadata: {e}")
        
        return result
    
    def _process_doc_sections(self, doc_sections: dict) -> DocSections:
        """Process doc sections from parsed response."""
        return DocSections(
            intent=doc_sections.get("intent", ""),
            design_principles=doc_sections.get("designPrinciples", []),
            implementation_details=doc_sections.get("implementationDetails", ""),
            design_decisions=doc_sections.get("designDecisions", "")
        )
    
    def _process_line_range(self, line_range: dict) -> LineRange:
        """Process line range from parsed response."""
        return LineRange(
            start=line_range.get("start", 0),
            end=line_range.get("end", 0)
        )
    
    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse timestamp string into datetime object."""
        try:
            # Assuming ISO format timestamp
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except Exception:
            # Fall back to current time if parsing fails
            self.logger.warning(f"Failed to parse timestamp '{timestamp_str}', using current time")
            return datetime.now()
    
    def _calculate_md5(self, content: str) -> str:
        """Calculate MD5 digest for content."""
        return hashlib.md5(content.encode('utf-8')).hexdigest()
```

7. **DatabaseWriter**

```python
class DatabaseWriter:
    """Writes extracted metadata to the database."""
    
    def __init__(self, db_component: Component, logger: Logger):
        self.db_component = db_component
        self.logger = logger
    
    def write(self, metadata: FileMetadata) -> None:
        """
        Write metadata to the database.
        
        Args:
            metadata: FileMetadata object to write
        """
        try:
            # Get database session from database component
            session = self.db_component.get_session()
            
            with session.begin():
                # Check if file already exists in database
                existing = session.query(FileMetadataORM).filter_by(path=metadata.path).first()
                
                if existing:
                    # Update existing record
                    self._update_record(existing, metadata, session)
                else:
                    # Create new record
                    self._create_record(metadata, session)
                
                # Commit transaction
                session.commit()
            
            self.logger.debug(f"Successfully wrote metadata for {metadata.path} to database")
        
        except Exception as e:
            self.logger.error(f"Failed to write metadata for {metadata.path} to database: {e}")
            raise DatabaseWriteError(f"Failed to write metadata to database: {e}")
    
    def _update_record(self, existing: FileMetadataORM, metadata: FileMetadata, session) -> None:
        """Update an existing database record with new metadata."""
        # Implementation will update ORM object with values from metadata
        # This will depend on the specific ORM implementation
        pass
    
    def _create_record(self, metadata: FileMetadata, session) -> None:
        """Create a new database record for metadata."""
        # Implementation will create new ORM object with values from metadata
        # This will depend on the specific ORM implementation
        pass
```

8. **FileMetadata and Related Classes**

```python
@dataclass
class LineRange:
    """Line range for code entities."""
    start: int
    end: int

@dataclass
class ChangeRecord:
    """Record of a change to a file."""
    timestamp: datetime
    summary: str
    details: List[str]

@dataclass
class HeaderSections:
    """Header sections extracted from a file."""
    intent: str
    design_principles: List[str]
    constraints: List[str]
    reference_documentation: List[str]
    change_history: List[ChangeRecord]

@dataclass
class DocSections:
    """Documentation sections extracted from a function or class."""
    intent: str
    design_principles: List[str]
    implementation_details: str
    design_decisions: str

@dataclass
class FunctionMetadata:
    """Metadata for a function."""
    name: str
    doc_sections: DocSections
    parameters: List[str]
    line_range: LineRange

@dataclass
class ClassMetadata:
    """Metadata for a class."""
    name: str
    doc_sections: DocSections
    methods: List[FunctionMetadata]
    line_range: LineRange

@dataclass
class FileMetadata:
    """Metadata extracted from a file."""
    path: str
    language: str
    header_sections: HeaderSections
    functions: List[FunctionMetadata]
    classes: List[ClassMetadata]
    size_bytes: int
    md5_digest: str
    last_modified: datetime
    extraction_timestamp: datetime
```

### Configuration Parameters

The Metadata Extraction component will be configured through these parameters:

```python
@dataclass
class MetadataExtractionConfig:
    """Configuration for metadata extraction."""
    model_id: str  # Amazon Nova Lite model ID
    temperature: float  # Temperature parameter for LLM
    max_tokens: int  # Maximum tokens for LLM response
    max_retries: int  # Maximum number of retries for LLM API calls
    retry_delay: float  # Initial delay between retries (seconds)
    extraction_prompt_template: str  # Path to extraction prompt template
    output_schema_template: str  # Path to output schema template
```

Default configuration values (will be integrated with CONFIGURATION.md):

| Parameter | Description | Default | Valid Values |
|-----------|-------------|---------|-------------|
| `model_id` | Amazon Nova Lite model ID | `"amazon.nova-lite-v3"` | Valid model ID |
| `temperature` | LLM temperature | `0.0` | `0.0-1.0` |
| `max_tokens` | Maximum tokens in response | `4096` | `1-8192` |
| `max_retries` | Maximum retries for API calls | `3` | `0-10` |
| `retry_delay` | Initial delay between retries (seconds) | `1.0` | `0.1-10.0` |
| `extraction_prompt_template` | Path to extraction prompt template | `"prompts/metadata_extraction.txt"` | Valid file path |
| `output_schema_template` | Path to output schema template | `"prompts/metadata_schema.txt"` | Valid file path |

### LLM Prompt Template Design

The extraction prompt template will be structured to guide the LLM in extracting metadata:

```
You are a code analyzer that extracts structured metadata from source code files.

INSTRUCTIONS:
1. Analyze the code provided below
2. Extract metadata according to the specified schema
3. Focus on identifying documentation sections in header comments, function docstrings, and class docstrings
4. Infer the programming language based on the file extension and content
5. Return the results as valid JSON matching the schema below

FILE PATH: {file_path}
FILE EXTENSION: {file_extension}

EXPECTED SCHEMA:
{output_schema}

FILE CONTENT:
{file_content}
```

The output schema template will define the expected JSON structure:

```json
{
  "path": "string", // File path
  "language": "string", // Programming language
  "headerSections": {
    "intent": "string", // File's purpose
    "designPrinciples": ["string"], // Design principles guiding implementation
    "constraints": ["string"], // Limitations or requirements
    "referenceDocumentation": ["string"], // Related documentation files
    "changeHistory": [
      {
        "timestamp": "ISO8601", // When change occurred
        "summary": "string", // Brief description of change
        "details": ["string"] // Detailed description of changes
      }
    ]
  },
  "functions": [
    {
      "name": "string", // Function name
      "docSections": {
        "intent": "string", // Purpose of function
        "designPrinciples": ["string"], // Design principles
        "implementationDetails": "string", // Technical approach
        "designDecisions": "string" // Why specific choices were made
      },
      "parameters": ["string"], // Function parameters
      "lineRange": {"start": number, "end": number} // Line numbers
    }
  ],
  "classes": [
    {
      "name": "string", // Class name
      "docSections": { /* Same structure as function docSections */ },
      "methods": [ /* Same structure as functions */ ],
      "lineRange": {"start": number, "end": number} // Line numbers
    }
  ]
}
```

## Implementation Plan

### Phase 1: Core Structure
1. Implement MetadataExtractionComponent as a system component
2. Define data structures for metadata (FileMetadata and related classes)
3. Create configuration class for metadata extraction
4. Implement error classes for specific error scenarios

### Phase 2: LLM Interaction
1. Implement LLMPromptManager for prompt creation
2. Create BedrockClient for Amazon Nova Lite interaction
3. Write prompt and schema template files
4. Implement response parsing logic in ResponseParser

### Phase 3: Metadata Processing
1. Implement ExtractionResultProcessor for LLM response processing
2. Create DatabaseWriter for persistence to SQLite/PostgreSQL
3. Implement linkages between components for data flow
4. Add thread safety mechanisms

### Phase 4: Integration and Testing
1. Integrate with Background Task Scheduler
2. Add metrics and logging for monitoring
3. Implement error recovery strategies
4. Create comprehensive test suite

## Security Considerations

The Metadata Extraction component implements these security measures:
- All processing performed locally without external transmission
- No AWS credentials directly handled (rely on default provider chain)
- Strict validation of LLM responses before processing
- Proper error handling and containment
- Thread safety for multi-threaded access
- No code execution from extracted metadata
- Protection against resource exhaustion

## Testing Strategy

### Unit Tests
- Test each class in isolation with mock dependencies
- Test prompt creation with various file types
- Test response parsing with valid and invalid responses
- Test error handling scenarios

### Integration Tests
- Test full metadata extraction flow with sample files
- Test database writing and retrieval
- Test interaction with AWS Bedrock (using mocks)

### System Tests
- Test integration with Background Task Scheduler
- Test extraction of metadata from various programming languages
- Test performance with large files
- Test resource usage during operation

## Dependencies on Other Plans

This plan depends on:
- Database Schema plan (for database integration)
- Component Initialization plan (for component framework)
- Background Task Scheduler plan (for integration)

## Implementation Timeline

1. Core Structure - 2 days
2. LLM Interaction - 3 days
3. Metadata Processing - 2 days
4. Integration and Testing - 3 days

Total: 10 days
