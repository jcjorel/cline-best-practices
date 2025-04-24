# Development Guide

This document provides practical guidance for new developers to start working with the Documentation-Based Programming (DBP) system.

## Getting Started

### Prerequisites

Before you begin working with the DBP system, ensure you have the following prerequisites:

- **Python 3.8 or higher** - Required for running the core system
- **Git** - For version control and integrating with commit message generation
- **SQLite** - Included with Python, no separate installation required
- **AWS Account with Bedrock Access** - For Amazon Nova Lite LLM functionality

### Environment Setup

1. **Clone the repository**:

```bash
git clone https://github.com/your-org/dbp-system.git
cd dbp-system
```

2. **Set up a virtual environment**:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:

```bash
pip install -r requirements.txt
```

4. **Configure AWS credentials**:

```bash
# Option 1: Use AWS CLI
aws configure

# Option 2: Set environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-east-1  # or your preferred region
```

5. **Initialize the database**:

```bash
python -m dbp.database.alembic_manager upgrade head
```

## Configuration

The DBP system uses a YAML-based configuration file. Create a custom configuration:

```bash
# Create a custom configuration file
cp config/default_config.yaml config/my_config.yaml

# Edit the configuration file
# vim config/my_config.yaml
```

Key configuration options:

```yaml
# Example configuration
system:
  base_directory: /path/to/project  # Project root directory
  log_level: INFO                   # Logging level (DEBUG, INFO, WARNING, ERROR)

database:
  path: coding_assistant/dbp/database.db  # Path to SQLite database
  verbose_migrations: false               # Enable verbose Alembic output

scheduler:
  enabled: true                     # Enable background scheduler
  delay_seconds: 10                 # Debounce delay for change detection
  max_delay_seconds: 120            # Maximum delay for any file
  worker_threads: 2                 # Number of worker threads

llm:
  default_model: amazon.nova-lite   # Default LLM model
  max_budget_per_request: 0.10      # Maximum cost per request in USD
  timeout_seconds: 30               # Timeout for LLM requests
  extraction_template_path: coding_assistant/GENAI_FUNCTION_TEMPLATE.txt
  header_template_path: coding_assistant/GENAI_HEADER_TEMPLATE.txt

mcp_server:
  host: 127.0.0.1                   # Network binding address
  port: 8080                        # Port for MCP server
  auth_enabled: false               # Enable authentication
```

## Running the System

### Starting the System

The DBP system has several components you can start:

1. **Start the MCP server**:

```bash
python -m dbp.mcp_server --config config/my_config.yaml
```

2. **Start file monitoring only**:

```bash
python -m dbp.fs_monitor --config config/my_config.yaml
```

3. **Run database maintenance**:

```bash
python -m dbp.database.maintenance --config config/my_config.yaml
```

4. **Start the complete system**:

```bash
python -m dbp_cli start --config config/my_config.yaml
```

### CLI Commands

The DBP system provides a comprehensive CLI:

```bash
# Show all available commands
python -m dbp_cli --help

# Check system status
python -m dbp_cli status

# Generate a recommendation on-demand
python -m dbp_cli recommend --file path/to/changed/file.py

# Show pending recommendations
python -m dbp_cli recommendations list

# Accept a recommendation
python -m dbp_cli recommendations accept <recommendation_id>

# Generate a commit message
python -m dbp_cli commit-message
```

## Development Workflow

### Key Development Principles

When working on the DBP system, keep these principles in mind:

1. **Documentation First**: Update documentation before implementing changes
2. **Consistent File Headers**: Use the templates for all code files
3. **Complete Function Comments**: Follow the three-section documentation pattern
4. **Design Decision Recording**: Document significant decisions in DESIGN_DECISIONS.md

### Typical Development Workflow

```mermaid
flowchart TD
    A[Identify Feature/Bug] --> B[Update Documentation]
    B --> C[Record Design Decisions]
    C --> D[Implement Code Changes]
    D --> E[Run Tests]
    E -->|Pass| F[Update File Headers]
    E -->|Fail| D
    F --> G[Update HSTC.md]
    G --> H[Submit Pull Request]
```

### Documentation Process

1. **Update Core Documentation**:
   - Modify relevant files in `doc/` directory
   - Add design decisions to DESIGN_DECISIONS.md 
   - Document relationships in DOCUMENT_RELATIONSHIPS.md

2. **Update Code Documentation**:
   - Follow three-section pattern: `[Intent]`, `[Design principles]`, `[Implementation details]`
   - Update file headers with changes

3. **Update HSTC Files**:
   - Run `python coding_assistant/scripts/identify_hstc_updates.py`
   - Check for any HSTC_REQUIRES_UPDATE.md files
   - Update affected HSTC.md files based on changes

## Project Structure

```
dbp-system/
├── alembic.ini                # Database migration configuration
├── coding_assistant/          # Templates and scripts
│   ├── GENAI_FUNCTION_TEMPLATE.txt
│   ├── GENAI_HEADER_TEMPLATE.txt
│   ├── scripts/
│   │   ├── get_design_mode_context.py
│   │   └── identify_hstc_updates.py
├── doc/                       # Core documentation
│   ├── API.md
│   ├── CODING_GUIDELINES.md
│   ├── CONFIGURATION.md
│   ├── DATA_MODEL.md
│   ├── DESIGN_DECISIONS.md
│   ├── DESIGN.md
│   ├── DOCUMENT_RELATIONSHIPS.md
│   ├── PR-FAQ.md
│   ├── SECURITY.md
│   ├── WORKING_BACKWARDS.md
│   ├── design/                # Detailed design documents
│   └── llm/                   # LLM-specific documentation
│       └── prompts/           # LLM prompt templates
├── requirements.txt
├── setup.py
├── src/
│   ├── dbp/                   # Core DBP modules
│   │   ├── config/            # Configuration management
│   │   ├── consistency_analysis/ # Consistency checking
│   │   ├── core/              # Core utilities and components
│   │   ├── database/          # Database layer
│   │   ├── doc_relationships/ # Document relationship tracking
│   │   ├── fs_monitor/        # File system monitoring
│   │   ├── internal_tools/    # Internal LLM tools
│   │   ├── llm/               # LLM client interfaces
│   │   ├── llm_coordinator/   # LLM coordination
│   │   ├── mcp_server/        # MCP protocol server
│   │   ├── memory_cache/      # In-memory caching
│   │   └── scheduler/         # Background task scheduling
│   └── dbp_cli/               # Command-line interface
└── tests/                     # Test suite
```

## Testing

The DBP system includes a comprehensive test suite:

```bash
# Run all tests
pytest

# Run specific test modules
pytest tests/test_fs_monitor.py

# Run with coverage
pytest --cov=src
```

### Writing Tests

When adding new features, include appropriate tests:

```python
# Example test
def test_file_monitor_detects_changes(tmp_path):
    """
    [Function intent]
    Test that the file monitor can detect file changes.
    
    [Design principles]
    Test isolation with temporary directory.
    Test file creation, modification, and deletion events.
    
    [Implementation details]
    Uses pytest's tmp_path fixture to create isolated test environment.
    """
    # Test setup
    monitor = FileSystemMonitor(str(tmp_path))
    monitor.start()
    
    # Create test file
    test_file = tmp_path / "test_file.txt"
    test_file.write_text("Initial content")
    
    # Wait for detection
    time.sleep(1)
    
    # Verify
    changes = monitor.get_detected_changes()
    assert len(changes) == 1
    assert changes[0].path == str(test_file)
    assert changes[0].type == ChangeType.Created
    
    # Cleanup
    monitor.stop()
```

## Common Development Tasks

### Adding a New Component

1. Create the component class implementing the Component interface:

```python
from dbp.core.component import Component

class MyNewComponent(Component):
    """
    [Class intent]
    A new component that implements feature X.
    
    [Design principles]
    Follows the Component interface pattern.
    Maintains single responsibility for feature X.
    
    [Implementation details]
    Implements the Component interface methods.
    Uses dependency injection for required services.
    """
    
    @property
    def name(self) -> str:
        return "my_new_component"
    
    def initialize(self, context, dependencies):
        # Get dependencies
        config_manager = self.get_dependency(dependencies, "config_manager")
        db_component = self.get_dependency(dependencies, "database")
        
        # Initialize component
        self.logger = context.logger
        self.logger.info("Initializing MyNewComponent")
        
        # Component-specific initialization
        self.do_initialization()
        
        self._initialized = True
    
    def shutdown(self):
        self.logger.info("Shutting down MyNewComponent")
        # Component-specific shutdown
        self._initialized = False
```

2. Register the component in the system:

```python
# In the component registry setup
registry.register_component(
    component_class=MyNewComponent,
    dependencies=["config_manager", "database"],
    enabled=True
)
```

### Creating a New Consistency Rule

Add a new rule to the consistency analysis engine:

```python
from dbp.consistency_analysis.engine import ConsistencyRule

class DocumentationReferenceRule(ConsistencyRule):
    """
    [Class intent]
    Checks that documentation references exist and are valid.
    
    [Design principles]
    Single responsibility for validating documentation references.
    Clear and actionable error messages.
    
    [Implementation details]
    Uses document relationship graph to validate references.
    """
    
    def check(self, document, relationship_graph):
        """
        [Function intent]
        Apply the consistency rule to a document.
        
        [Design principles]
        Complete validation of all references.
        
        [Implementation details]
        Checks header references against relationship graph.
        """
        inconsistencies = []
        
        # Get references from header
        references = document.header_sections.reference_documentation
        
        for ref in references:
            if not relationship_graph.has_node(ref):
                # Reference doesn't exist
                inconsistencies.append(self.create_inconsistency(
                    document=document,
                    severity=Severity.Major,
                    description=f"Reference to non-existent document: {ref}",
                    suggestion=f"Update or remove the reference to {ref}"
                ))
        
        return inconsistencies
```

### Adding a New MCP Tool

Implement a new MCP tool for AI assistant integration:

```python
from dbp.mcp_server.tools import register_tool
from pydantic import BaseModel, Field

class MyToolRequestSchema(BaseModel):
    query: str = Field(..., description="The query to process")
    max_results: int = Field(10, description="Maximum number of results to return")

class MyToolResponseSchema(BaseModel):
    results: list = Field(..., description="The query results")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")

@register_tool(
    name="dbp_my_new_tool",
    description="A new tool for AI assistants to use feature X",
    request_schema=MyToolRequestSchema,
    response_schema=MyToolResponseSchema
)
async def my_new_tool(request, context):
    """
    [Function intent]
    Process AI assistant requests for feature X.
    
    [Design principles]
    Validate inputs and provide clear error messages.
    Use async processing for non-blocking operation.
    
    [Implementation details]
    Connects to internal components to fulfill the request.
    """
    # Get required services
    coordinator = context.services.get_service("llm_coordinator")
    
    # Process request
    start_time = time.time()
    results = await coordinator.process_query(request.query, max_results=request.max_results)
    processing_time = int((time.time() - start_time) * 1000)
    
    # Return results
    return MyToolResponseSchema(
        results=results,
        processing_time_ms=processing_time
    )
```

## Troubleshooting

### Common Issues and Solutions

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| MCP server won't start | Port already in use | Change the port in configuration or stop the process using the port |
| File changes not detected | File monitor not running or excluded by filter | Check monitor status and filter configuration |
| LLM extraction fails | AWS credentials missing or Bedrock access issues | Verify AWS credentials and Bedrock model access |
| SQLite database errors | Database locked or corrupted | Check for concurrent access issues or restore from backup |
| Memory usage grows over time | Memory leak in cache management | Restart the service and check cache invalidation logic |

### Logging and Debugging

The DBP system uses Python's logging system. To enable debug logging:

```yaml
# In your config file
system:
  log_level: DEBUG  # Set to DEBUG for verbose output
```

Log files are stored in `coding_assistant/logs/` by default.

### Performance Optimization

To optimize performance:

1. **Use WAL mode for SQLite**: Enables concurrent access
   ```yaml
   database:
     wal_mode: true
   ```

2. **Adjust worker thread count**: Match to your CPU core count
   ```yaml
   scheduler:
     worker_threads: 4  # Adjust based on CPU cores
   ```

3. **Tune debounce settings**: Balance responsiveness and efficiency
   ```yaml
   scheduler:
     delay_seconds: 5     # Shorter for faster response
     max_delay_seconds: 60  # Shorter for faster maximal response
   ```

4. **Optimize memory cache**: Adjust cache sizes
   ```yaml
   memory_cache:
     max_entries: 10000  # Adjust based on project size
     ttl_seconds: 3600   # Time-to-live for cache entries
   ```

## Advanced Topics

### Custom LLM Integration

The DBP system can work with alternative LLM providers:

1. Create a new LLM client that implements the base interface:

```python
from dbp.llm.base import BaseLLMClient

class MyCustomLLMClient(BaseLLMClient):
    """
    [Class intent]
    Custom LLM client implementation for alternative provider.
    
    [Design principles]
    Implement the required interface methods.
    Handle rate limiting and error conditions.
    
    [Implementation details]
    Uses the provider's API to request completions.
    """
    
    def __init__(self, config):
        super().__init__(config)
        # Client-specific initialization
        
    async def generate_completion(self, prompt, max_tokens=None, temperature=None):
        """
        [Function intent]
        Generate text completion from the LLM provider.
        
        [Design principles]
        Proper error handling with sensible defaults.
        
        [Implementation details]
        Calls the provider's API with appropriate parameters.
        """
        # Implementation
```

2. Register the client in the LLM module:

```python
from dbp.llm.client_registry import register_llm_client

register_llm_client("my_custom_llm", MyCustomLLMClient)
```

3. Configure the system to use your client:

```yaml
llm:
  default_model: my_custom_llm
  # Client-specific configuration
  my_custom_llm:
    api_key: your_api_key
    endpoint: https://api.example.com/v1/completions
```

### PostgreSQL Integration

To use PostgreSQL instead of SQLite:

1. Install PostgreSQL dependencies:

```bash
pip install psycopg2-binary alembic[postgresql]
```

2. Update your configuration:

```yaml
database:
  type: postgresql
  connection_string: postgresql://username:password@localhost/dbp_database
  pool_size: 10
```

3. Create the database:

```bash
createdb dbp_database
```

4. Run migrations:

```bash
python -m dbp.database.alembic_manager upgrade head
```

### Writing Custom Prompt Templates

To customize the LLM prompt templates:

1. Create a new template file in `doc/llm/prompts/`:

```markdown
# Custom Prompt Template

## System Instruction

You are a specialized AI assistant working as part of the Documentation-Based Programming system. Your role is to [describe purpose].

You have access to the following information:

```
{{context_variable}}
```

<!-- This template should be used by the custom_tool -->

## User Query Format

{{query}}

## Example Usage

[Example query and expected response]

## Response Format

Respond with a JSON object following this schema:

```json
{
  "field1": "type",
  "field2": ["array", "of", "items"],
  "field3": {
    "nested": "object"
  }
}
```
```

2. Register the template with the coordinator:

```python
from dbp.llm_coordinator.prompt_manager import register_prompt_template

register_prompt_template(
    name="custom_template",
    file_path="doc/llm/prompts/custom_template.md"
)
```

3. Use the template in your code:

```python
template = coordinator.get_template("custom_template")
formatted_prompt = template.format(
    context_variable=my_context,
    query=user_query
)
```

## Next Steps

Congratulations! You now have the knowledge needed to work with the Documentation-Based Programming system. Here are some suggested next steps:

1. **Explore the Codebase**: Look through the source code to understand implementation details
2. **Review Documentation**: Read through the core documentation files
3. **Set Up a Test Project**: Configure the DBP system on a small project to see how it works
4. **Contribute**: Consider contributing improvements or bug fixes to the project

If you have questions or need help, check out these resources:

- **GitHub Issues**: https://github.com/your-org/dbp-system/issues
- **Documentation**: https://dbp-system.readthedocs.io/
- **Community Chat**: https://gitter.im/dbp-system/community

Happy coding!
