# LLM Integration and Metadata Extraction Implementation Plan

## Overview

This document details the implementation plan for the LLM-based metadata extraction system of the Documentation-Based Programming (DBP) project. Based on the project documentation, this component is responsible for extracting structured metadata from code files using Claude 3.7 Sonnet's natural language understanding capabilities.

## Requirements

From the project documentation, specifically [DESIGN.md](../doc/DESIGN.md), [DATA_MODEL.md](../doc/DATA_MODEL.md), and [DESIGN_DECISIONS.md](../doc/DESIGN_DECISIONS.md), the metadata extraction system must:

1. Use Claude 3.7 Sonnet to extract metadata from codebase files
2. Rely exclusively on LLM capabilities with no programmatic fallback, as per the design decision in DESIGN_DECISIONS.md
3. Extract header sections, function documentation, class documentation, and other metadata
4. Maintain an in-memory cache synchronized with persistent storage
5. Process files within 10 seconds of detected changes
6. Support metadata extraction across various programming languages
7. Use semantic understanding rather than keyword-based parsing
8. Consume minimal resources (<5% CPU, <100MB RAM)
9. Ensure thread-safety for all operations

## Implementation Components

### 1. LLM Integration Service

This component will handle the integration with Claude 3.7 Sonnet:

```python
class LLMIntegrationService:
    def __init__(self, config):
        """Initialize LLM integration service with configuration."""
        self.config = config
        self.model_name = config.get('llm.model_name', 'claude-3-7-sonnet')
        self.max_retries = config.get('llm.max_retries', 3)
        self.retry_delay = config.get('llm.retry_delay_seconds', 2)
        self.timeout = config.get('llm.timeout_seconds', 30)
        self.token_limit = config.get('llm.token_limit', 10000)
        # Add appropriate client initialization based on final LLM provider choice
        self._init_client()
        
    def _init_client(self):
        """Initialize the LLM client."""
        # AWS Bedrock client initialization for Claude 3.7 Sonnet
        # This is a placeholder that will be replaced with actual implementation
        try:
            # Initialize actual client (AWS Bedrock)
            pass
        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")
            raise LLMIntegrationError(f"LLM client initialization failed: {str(e)}")
        
    def extract_metadata(self, file_path, file_content, file_type=None):
        """Extract metadata from file content using LLM."""
        try:
            # Prepare prompt for metadata extraction
            prompt = self._build_extraction_prompt(file_content, file_path, file_type)
            
            # Call LLM with retry logic
            response = self._call_llm_with_retry(prompt)
            
            # Parse and validate response
            metadata = self._parse_response(response, file_path)
            
            return metadata
        except Exception as e:
            logger.error(f"Metadata extraction failed for {file_path}: {e}")
            raise MetadataExtractionError(f"Failed to extract metadata from {file_path}: {str(e)}")
    
    def _build_extraction_prompt(self, content, file_path, file_type=None):
        """Build prompt for metadata extraction."""
        # Get file extension if file_type not provided
        if not file_type and file_path:
            file_type = os.path.splitext(file_path)[1][1:]
            
        # Load the appropriate template based on file type or use default
        template_path = self._get_template_path(file_type)
        
        try:
            with open(template_path, 'r') as f:
                template = f.read()
        except Exception as e:
            logger.error(f"Failed to load extraction template: {e}")
            raise TemplateError(f"Failed to load extraction template: {str(e)}")
            
        # Replace placeholders in template
        prompt = template.replace("{FILE_CONTENT}", content)
        prompt = prompt.replace("{FILE_PATH}", file_path or "")
        prompt = prompt.replace("{FILE_TYPE}", file_type or "")
        
        return prompt
    
    def _call_llm_with_retry(self, prompt):
        """Call LLM with retry logic."""
        retries = 0
        last_error = None
        
        while retries < self.max_retries:
            try:
                # Call LLM API (actual implementation depends on final LLM provider)
                # This is a placeholder
                response = self._call_llm(prompt)
                return response
            except Exception as e:
                logger.warning(f"LLM call failed (attempt {retries+1}/{self.max_retries}): {e}")
                last_error = e
                retries += 1
                time.sleep(self.retry_delay * (2 ** (retries - 1)))  # Exponential backoff
        
        # All retries failed
        logger.error(f"All LLM call attempts failed: {last_error}")
        raise LLMCallError(f"Failed to call LLM after {self.max_retries} attempts: {str(last_error)}")
    
    def _call_llm(self, prompt):
        """Make the actual LLM API call."""
        # This is a placeholder for the actual API call
        # Will be implemented based on the chosen LLM provider's SDK
        pass
    
    def _parse_response(self, response, file_path):
        """Parse and validate LLM response."""
        try:
            # Attempt to parse JSON response
            metadata = json.loads(response)
            
            # Validate against expected schema
            self._validate_metadata(metadata)
            
            return metadata
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response for {file_path}: {e}")
            raise ResponseParsingError(f"Invalid JSON response: {str(e)}")
        except ValidationError as e:
            logger.error(f"Metadata validation failed for {file_path}: {e}")
            raise ResponseParsingError(f"Metadata validation failed: {str(e)}")
    
    def _validate_metadata(self, metadata):
        """Validate metadata against expected schema."""
        # Check for required fields
        required_fields = ['path', 'language']
        for field in required_fields:
            if field not in metadata:
                raise ValidationError(f"Missing required field: {field}")
        
        # Validate structure based on file type
        if 'functions' in metadata and not isinstance(metadata['functions'], list):
            raise ValidationError("'functions' must be an array")
            
        if 'classes' in metadata and not isinstance(metadata['classes'], list):
            raise ValidationError("'classes' must be an array")
            
        if 'headerSections' in metadata and not isinstance(metadata['headerSections'], dict):
            raise ValidationError("'headerSections' must be an object")
```

### 2. File Metadata Extractor

This component will coordinate the metadata extraction process:

```python
class FileMetadataExtractor:
    def __init__(self, llm_service, cache_manager, db_repository):
        """Initialize file metadata extractor."""
        self.llm_service = llm_service
        self.cache_manager = cache_manager
        self.db_repository = db_repository
        
    def extract_file_metadata(self, file_path):
        """Extract metadata from a file."""
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract metadata using LLM
            metadata = self.llm_service.extract_metadata(file_path, content)
            
            # Add file path to metadata if not present
            if 'path' not in metadata:
                metadata['path'] = file_path
                
            # Add file stats
            file_stats = os.stat(file_path)
            metadata['size'] = file_stats.st_size
            metadata['last_modified'] = datetime.fromtimestamp(file_stats.st_mtime)
            
            # Calculate MD5 digest for change detection
            metadata['md5_digest'] = self._calculate_md5(content)
            
            # Store metadata in cache and database
            self.cache_manager.update_metadata(file_path, metadata)
            self.db_repository.save_file_metadata(metadata)
            
            return metadata
        except Exception as e:
            logger.error(f"Failed to extract metadata from {file_path}: {e}")
            raise MetadataExtractionError(f"Metadata extraction failed: {str(e)}")
    
    def _calculate_md5(self, content):
        """Calculate MD5 digest for file content."""
        import hashlib
        md5 = hashlib.md5()
        md5.update(content.encode('utf-8'))
        return md5.hexdigest()
```

### 3. In-Memory Metadata Cache

This component will provide fast access to frequently used metadata:

```python
class MetadataCache:
    def __init__(self, config):
        """Initialize metadata cache."""
        self.config = config
        self.cache = {}  # path -> metadata
        self.cache_lock = threading.RLock()  # Reentrant lock for thread safety
        self.max_size = config.get('cache.max_size', 1000)
        self.lru_queue = collections.deque()  # For LRU cache eviction
        
    def get_metadata(self, file_path):
        """Get metadata for a file from cache."""
        with self.cache_lock:
            if file_path in self.cache:
                # Update LRU status
                self.lru_queue.remove(file_path)
                self.lru_queue.append(file_path)
                return self.cache[file_path]
            return None
    
    def update_metadata(self, file_path, metadata):
        """Update or add metadata in cache."""
        with self.cache_lock:
            # Check if cache is full and needs eviction
            if file_path not in self.cache and len(self.cache) >= self.max_size:
                self._evict_lru()
                
            # Update or add metadata
            self.cache[file_path] = metadata
            
            # Update LRU status
            if file_path in self.lru_queue:
                self.lru_queue.remove(file_path)
            self.lru_queue.append(file_path)
    
    def remove_metadata(self, file_path):
        """Remove metadata from cache."""
        with self.cache_lock:
            if file_path in self.cache:
                del self.cache[file_path]
                self.lru_queue.remove(file_path)
    
    def clear(self):
        """Clear the entire cache."""
        with self.cache_lock:
            self.cache.clear()
            self.lru_queue.clear()
    
    def _evict_lru(self):
        """Evict least recently used entry from cache."""
        if self.lru_queue:
            lru_path = self.lru_queue.popleft()
            if lru_path in self.cache:
                del self.cache[lru_path]
```

### 4. Metadata Extraction Worker

This component will handle the asynchronous processing of file changes:

```python
class MetadataExtractionWorker:
    def __init__(self, config, file_extractor, db_repository):
        """Initialize metadata extraction worker."""
        self.config = config
        self.file_extractor = file_extractor
        self.db_repository = db_repository
        self.work_queue = queue.Queue()
        self.worker_threads = []
        self.num_threads = config.get('scheduler.worker_threads', 2)
        self.running = False
        
    def start(self):
        """Start worker threads."""
        if self.running:
            return
            
        self.running = True
        
        # Create worker threads
        for i in range(self.num_threads):
            thread = threading.Thread(target=self._worker_thread_func)
            thread.daemon = True
            thread.start()
            self.worker_threads.append(thread)
    
    def stop(self):
        """Stop worker threads."""
        self.running = False
        
        # Wait for threads to finish
        for thread in self.worker_threads:
            if thread.is_alive():
                thread.join(timeout=1.0)
                
        # Clear any remaining items in the queue
        while not self.work_queue.empty():
            try:
                self.work_queue.get_nowait()
                self.work_queue.task_done()
            except queue.Empty:
                break
    
    def schedule_extraction(self, file_path, event_type, timestamp=None):
        """Schedule a file for metadata extraction."""
        try:
            self.work_queue.put({
                'path': file_path,
                'event_type': event_type,
                'timestamp': timestamp or time.time()
            })
        except Exception as e:
            logger.error(f"Failed to schedule extraction for {file_path}: {e}")
    
    def _worker_thread_func(self):
        """Worker thread function."""
        while self.running:
            try:
                # Get work item from queue with timeout
                try:
                    work_item = self.work_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                try:
                    # Process work item
                    self._process_work_item(work_item)
                except Exception as e:
                    logger.error(f"Error processing work item {work_item['path']}: {e}")
                finally:
                    # Mark task as done
                    self.work_queue.task_done()
            except Exception as e:
                logger.error(f"Worker thread error: {e}")
                # Brief sleep to prevent tight loop in case of persistent errors
                time.sleep(0.1)
    
    def _process_work_item(self, work_item):
        """Process a work item."""
        path = work_item['path']
        event_type = work_item['event_type']
        
        # Handle different event types
        if event_type == 'deleted':
            # Remove metadata for deleted file
            self.db_repository.delete_file_metadata(path)
        else:  # created or modified
            # Check if file still exists
            if not os.path.exists(path):
                logger.info(f"File {path} no longer exists, skipping extraction")
                return
                
            # Extract metadata
            self.file_extractor.extract_file_metadata(path)
```

### 5. Metadata Extraction Service

This component will provide the main interface for the metadata extraction system:

```python
class MetadataExtractionService:
    def __init__(self, config, db_manager):
        """Initialize metadata extraction service."""
        self.config = config
        self.db_manager = db_manager
        
        # Create cache manager
        self.cache_manager = MetadataCache(config)
        
        # Create file metadata repository
        self.file_metadata_repo = FileMetadataRepository(db_manager)
        
        # Create LLM integration service
        self.llm_service = LLMIntegrationService(config)
        
        # Create file metadata extractor
        self.file_extractor = FileMetadataExtractor(
            self.llm_service, 
            self.cache_manager,
            self.file_metadata_repo
        )
        
        # Create extraction worker
        self.extraction_worker = MetadataExtractionWorker(
            config, 
            self.file_extractor,
            self.file_metadata_repo
        )
        
    def initialize(self):
        """Initialize the service."""
        # Start worker threads
        self.extraction_worker.start()
        
        # Preload cache with important files
        self._preload_cache()
        
    def shutdown(self):
        """Shut down the service."""
        # Stop worker threads
        self.extraction_worker.stop()
        
    def schedule_extraction(self, file_path, event_type, timestamp=None):
        """Schedule a file for metadata extraction."""
        self.extraction_worker.schedule_extraction(file_path, event_type, timestamp)
        
    def get_file_metadata(self, file_path):
        """Get metadata for a file."""
        # Try cache first
        metadata = self.cache_manager.get_metadata(file_path)
        if metadata is not None:
            return metadata
            
        # Get from database
        metadata = self.file_metadata_repo.get_by_path(file_path)
        if metadata is not None:
            # Update cache
            self.cache_manager.update_metadata(file_path, metadata)
            return metadata
            
        # Not found in cache or database, extract if file exists
        if os.path.exists(file_path):
            return self.file_extractor.extract_file_metadata(file_path)
            
        return None
    
    def _preload_cache(self):
        """Preload cache with important files."""
        # Get most frequently accessed files from database
        important_files = self.file_metadata_repo.get_most_important_files(
            limit=self.config.get('cache.preload_count', 100)
        )
        
        # Load into cache
        for metadata in important_files:
            self.cache_manager.update_metadata(metadata['path'], metadata)
```

### 6. Prompt Templates Management

This component will manage the prompt templates used for metadata extraction:

```python
class PromptTemplateManager:
    def __init__(self, config):
        """Initialize prompt template manager."""
        self.config = config
        self.templates_dir = config.get('llm.templates_dir', 'templates/extraction')
        self.templates_cache = {}
        
    def get_template(self, file_type):
        """Get extraction template for a file type."""
        # Check cache first
        if file_type in self.templates_cache:
            return self.templates_cache[file_type]
            
        # Try to find type-specific template
        template_path = os.path.join(self.templates_dir, f"{file_type}.md")
        if not os.path.exists(template_path):
            # Fall back to default template
            template_path = os.path.join(self.templates_dir, "default.md")
            if not os.path.exists(template_path):
                raise TemplateError(f"No default extraction template found")
        
        # Load template
        with open(template_path, 'r') as f:
            template = f.read()
            
        # Cache template
        self.templates_cache[file_type] = template
        
        return template
```

## Prompt Templates

The system will use a set of prompt templates for different file types. Each template will include:

1. Clear instructions for metadata extraction
2. Expected output format with JSON schema
3. Examples of how to handle common patterns
4. File-type specific guidance

### Example Default Template Structure

```
### Metadata Extraction Task ###

You are analyzing a source code file to extract metadata based on the Documentation-Based Programming system requirements.

File Path: {FILE_PATH}
File Type: {FILE_TYPE}

Please extract the following information from the code:
1. Header sections following the GenAI header template pattern
2. Function definitions with their documentation
3. Class definitions with their documentation
4. Overall file language determination

Return the results in the following JSON format:

```json
{
  "path": "path/to/file",
  "language": "programming_language",
  "headerSections": {
    "intent": "File's purpose",
    "designPrinciples": ["Design principle 1", "Design principle 2"],
    "constraints": ["Constraint 1", "Constraint 2"],
    "referenceDocumentation": ["doc/FILENAME.md", "doc/OTHER.md"],
    "changeHistory": [
      {
        "timestamp": "YYYY-MM-DDThh:mm:ssZ",
        "summary": "Change summary",
        "details": ["Detail 1", "Detail 2"]
      }
    ]
  },
  "functions": [
    {
      "name": "functionName",
      "docSections": {
        "intent": "Function purpose",
        "designPrinciples": ["Design principle"],
        "implementationDetails": "Technical approach",
        "designDecisions": "Why specific choices were made"
      },
      "parameters": ["param1", "param2"],
      "lineRange": {"start": 10, "end": 20}
    }
  ],
  "classes": [
    {
      "name": "ClassName",
      "docSections": {
        "intent": "Class purpose",
        "designPrinciples": ["Design principle"],
        "implementationDetails": "Technical approach",
        "designDecisions": "Why specific choices were made"
      },
      "methods": ["method1", "method2"],
      "lineRange": {"start": 30, "end": 100}
    }
  ]
}
```

File Content:
```
{FILE_CONTENT}
```
```

## Integration with Background Task Scheduler

The metadata extraction system will integrate with the Background Task Scheduler as described in [BACKGROUND_TASK_SCHEDULER.md](../doc/design/BACKGROUND_TASK_SCHEDULER.md):

1. The File System Monitor will detect file changes
2. Changes will be added to the Change Detection Queue
3. After the debounce period, the Background Task Scheduler will call the Metadata Extraction Service
4. The Metadata Extraction Service will schedule the file for processing
5. The Metadata Extraction Worker will process the file and update the database and cache

## Error Handling Strategy

Following the "throw on error" principle from the project documentation:

1. All LLM operations will include proper error handling
2. Errors will be caught, logged, and re-thrown with clear context
3. Error messages will include both what failed and why it failed
4. Retry logic will be implemented for transient LLM failures
5. Failed extraction attempts will be logged for later analysis

## Performance Considerations

To meet the <5% CPU and <100MB RAM requirements:

1. **Efficient Caching**: Use LRU cache for frequently accessed metadata
2. **Parallel Processing**: Process multiple files concurrently with worker threads
3. **Throttled Extraction**: Limit concurrent LLM requests to avoid resource spikes
4. **Resource Monitoring**: Track CPU and memory usage, adjust behavior if needed
5. **Batched Database Updates**: Group database operations to reduce I/O overhead
6. **Metadata Compression**: Store only essential information in memory
7. **Incremental Extraction**: Only process changed files

## Security Considerations

As outlined in SECURITY.md:

1. All file access will respect filesystem permissions
2. No external transmission of file contents
3. Strict validation of LLM responses
4. Complete separation between indexed projects
5. Memory cleanup after processing sensitive files

## Implementation Order

1. Implement the LLM Integration Service for Claude 3.7 Sonnet
2. Create the File Metadata Extractor component
3. Develop the In-Memory Metadata Cache
4. Implement the Metadata Extraction Worker
5. Build the Metadata Extraction Service
6. Create prompt templates for various file types
7. Add comprehensive error handling and logging
8. Implement performance optimization and monitoring

## Testing Strategy

1. **Unit Tests**: Test individual components with mock LLM responses
2. **Integration Tests**: Test the complete extraction system with sample files
3. **Performance Tests**: Verify resource usage meets requirements
4. **Stress Tests**: Test with large number of files
5. **Recovery Tests**: Verify system recovers from LLM failures

## Special Considerations for Language Detection

As per the design decision in DESIGN_DECISIONS.md:

1. No programmatic language detection will be implemented
2. The LLM will perform language detection as part of the metadata extraction process
3. The LLM will be provided with file extension information to aid in detection
4. Language detection results will be stored along with other metadata
