# Hierarchical Semantic Tree Context: prompts

## Directory Purpose
The doc/llm/prompts directory contains the prompt templates and documentation used by the system's LLM components for various specialized tasks. These prompts are designed to guide the language models in performing specific functions like context gathering, document analysis, coordination, and expert advice generation. Each prompt follows a consistent structure with clear sections for context, task definition, and response format. This directory serves as the single source of truth for all LLM prompts used throughout the system, ensuring consistency and maintainability of AI interactions.

## Local Files

### `README.md`
```yaml
source_file_intent: |
  Provides an overview of the prompt directory structure, usage guidelines, and documentation for the prompt format.
  
source_file_design_principles: |
  - Clear navigation guide for prompt files
  - Standardized prompt structure documentation
  - Best practices for prompt development and modification
  
source_file_constraints: |
  - Must be kept updated as prompt files are added or modified
  - Must align with actual prompt implementation patterns
  
dependencies:
  - kind: codebase
    dependency: doc/llm/PROMPT_GUIDELINES.md
  
change_history:
  - timestamp: "2025-04-24T23:24:30Z"
    summary: "Created HSTC.md file"
    details: "Initial documentation of README.md in HSTC.md"
```

### `coordinator_general_query_classifier.md`
```yaml
source_file_intent: |
  Defines the prompt for classifying general queries received by the LLM coordinator to determine appropriate handling.
  
source_file_design_principles: |
  - Clear classification categories with examples
  - Consistent output formatting for downstream processing
  - Contextual understanding for accurate classification
  
source_file_constraints: |
  - Must produce structured output for programmatic consumption
  - Must align with the coordinator's classification categories
  
dependencies:
  - kind: codebase
    dependency: src/dbp/llm_coordinator/data_models.py
  
change_history:
  - timestamp: "2025-04-24T23:24:30Z"
    summary: "Created HSTC.md file"
    details: "Initial documentation of coordinator_general_query_classifier.md in HSTC.md"
```

### `coordinator_get_codebase_changelog_context.md`
```yaml
source_file_intent: |
  Defines the prompt for extracting relevant context from codebase changelogs to inform LLM operations.
  
source_file_design_principles: |
  - Temporal relevance filtering
  - Semantic importance prioritization
  - Structured output formatting
  
source_file_constraints: |
  - Must extract high-value context within token constraints
  - Must maintain chronological ordering where relevant
  
dependencies:
  - kind: codebase
    dependency: src/dbp/llm_coordinator/context_assemblers.py
  
change_history:
  - timestamp: "2025-04-24T23:24:30Z"
    summary: "Created HSTC.md file"
    details: "Initial documentation of coordinator_get_codebase_changelog_context.md in HSTC.md"
```

### `coordinator_get_codebase_context.md`
```yaml
source_file_intent: |
  Defines the prompt for extracting relevant context from the codebase structure and content for LLM operations.
  
source_file_design_principles: |
  - Hierarchical context aggregation
  - Code structure summarization
  - Relationship mapping between code entities
  
source_file_constraints: |
  - Must balance breadth and depth of context
  - Must prioritize contextually relevant code segments
  
dependencies:
  - kind: codebase
    dependency: src/dbp/internal_tools/context_assemblers.py
  
change_history:
  - timestamp: "2025-04-24T23:24:30Z"
    summary: "Created HSTC.md file"
    details: "Initial documentation of coordinator_get_codebase_context.md in HSTC.md"
```

### `coordinator_get_documentation_changelog_context.md`
```yaml
source_file_intent: |
  Defines the prompt for extracting relevant context from documentation changelogs to inform LLM operations.
  
source_file_design_principles: |
  - Recent change prioritization
  - Documentation impact assessment
  - Semantic relevance filtering
  
source_file_constraints: |
  - Must focus on documentation evolution patterns
  - Must highlight significant architectural changes
  
dependencies:
  - kind: codebase
    dependency: src/dbp/llm_coordinator/context_assemblers.py
  
change_history:
  - timestamp: "2025-04-24T23:24:30Z"
    summary: "Created HSTC.md file"
    details: "Initial documentation of coordinator_get_documentation_changelog_context.md in HSTC.md"
```

### `coordinator_get_documentation_context.md`
```yaml
source_file_intent: |
  Defines the prompt for extracting relevant context from project documentation for LLM operations.
  
source_file_design_principles: |
  - Documentation hierarchy traversal
  - Topic relevance scoring
  - Cross-document relationship mapping
  
source_file_constraints: |
  - Must prioritize authoritative documentation sources
  - Must include relationship context from DOCUMENT_RELATIONSHIPS.md
  
dependencies:
  - kind: codebase
    dependency: src/dbp/doc_relationships/component.py
  - kind: codebase
    dependency: src/dbp/internal_tools/context_assemblers.py
  
change_history:
  - timestamp: "2025-04-24T23:24:30Z"
    summary: "Created HSTC.md file"
    details: "Initial documentation of coordinator_get_documentation_context.md in HSTC.md"
```

### `coordinator_get_expert_architect_advice.md`
```yaml
source_file_intent: |
  Defines the prompt for generating expert architectural advice in response to design and implementation questions.
  
source_file_design_principles: |
  - Design principle alignment verification
  - Architecture pattern recommendation
  - Trade-off analysis framing
  
source_file_constraints: |
  - Must align advice with project design documentation
  - Must provide rationale for architectural recommendations
  
dependencies:
  - kind: codebase
    dependency: doc/DESIGN.md
  - kind: codebase
    dependency: doc/DESIGN_DECISIONS.md
  
change_history:
  - timestamp: "2025-04-24T23:24:30Z"
    summary: "Created HSTC.md file"
    details: "Initial documentation of coordinator_get_expert_architect_advice.md in HSTC.md"
```

### `metadata_extraction.md`
```yaml
source_file_intent: |
  Defines the prompt for extracting metadata from code and documentation files to generate HSTC entries.
  
source_file_design_principles: |
  - Structured metadata identification
  - Cross-file relationship inference
  - Hierarchical context building
  
source_file_constraints: |
  - Must extract metadata following HSTC schema requirements
  - Must accurately identify dependencies and relationships
  
dependencies:
  - kind: codebase
    dependency: src/dbp/metadata_extraction/component.py
  
change_history:
  - timestamp: "2025-04-24T23:24:30Z"
    summary: "Created HSTC.md file"
    details: "Initial documentation of metadata_extraction.md in HSTC.md"
