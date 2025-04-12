# Working Backwards: Documentation-based Programming MCP Server (DBP-S)

## Documentation-based Programming: A New Development Paradigm

Documentation-based Programming (DBP) fundamentally shifts how developers approach software creation by establishing documentation as the authoritative source of truth. Unlike traditional development where code is primary and documentation often becomes outdated, DBP inverts this relationship.

In the DBP approach:

1. **Documentation First**: New features begin with documentation changes rather than code implementation
2. **Single Source of Truth**: Documentation is considered the definitive reference for project intent and architecture
3. **Automatic Synchronization**: When code changes are made directly, documentation is updated to maintain consistency
4. **Context Efficiency**: Comprehensive documentation allows AI assistants to understand projects without parsing complex code, saving valuable LLM context window space
5. **Design-Focused Development**: Emphasis shifts to clearly communicating design intent before implementation begins

This paradigm is particularly effective with AI coding assistants like Cline, which benefit from clear, structured documentation to provide accurate assistance. The DBP-S server makes this approach practical by automatically maintaining the relationship between documentation and code.

## 1. Customer Problem

Cline users frequently experience the following frustrations when working with the AI assistant:

- **Repetitive Context Setting**: Developers must repeatedly remind the AI assistant about project structure, coding standards, and documentation practices.

- **Inconsistent Recommendations**: Without persistent knowledge of the project context, the AI assistant may suggest solutions that don't align with established patterns.

- **Design Decision Fragmentation**: Critical design decisions get lost across multiple files and conversations, leading to inconsistent implementation.

- **Documentation-Code Misalignment**: As projects evolve, code and documentation drift apart, causing AI recommendations that don't respect the project's documentation standards.

- **Delayed Productivity**: Significant time is spent explaining project architecture rather than solving actual coding problems.

- **Context Limitations**: LLMs have limited context windows, making it impossible to include all relevant project files and documentation in a single prompt.

A senior developer described their experience: "I spend at least 20% of my interactions with Cline just reminding it about our project structure and coding standards. It's like working with a new team member who keeps forgetting our conventions and doesn't understand the critical design decisions that shaped our architecture."

## 2. Customer Experience with Solution

After installing the Documentation-based Programming MCP Server (DBP-S):

1. Sarah, a full-stack developer, opens her project in the morning. The DBP-S has already indexed her entire codebase overnight after recent changes, specifically focusing on the documentation standards defined in the system prompt.

2. Without providing any additional context, she asks Cline to "update the user authentication flow to support multi-factor authentication."

3. Cline immediately references the correct files in the authentication module, notes the existing design patterns documented in file headers, and proposes changes that perfectly align with the project's established architecture and documentation standards. Most importantly, it references the design decisions documented at function, file, and module level that apply to authentication security standards.

4. When Sarah makes changes to the code, the DBP-S detects and indexes those changes within 10 seconds using its pure in-memory indexing system, ensuring that subsequent interactions with Cline maintain perfect contextual awareness.

5. Sarah completes the feature in half the usual time, without having to repeatedly explain project context or correct misaligned suggestions from the AI assistant. The implementation maintains complete consistency between code and documentation, preserving all design decisions.

6. Before submitting her code, Sarah uses the DBP-S to detect any documentation inconsistencies that may have been introduced during development. The system immediately identifies a missing design decision section in one of the modified files, allowing her to remediate the documentation gap before it affects future development.

## 3. How Will We Know If Successful?

Success metrics for the Documentation-based Programming MCP Server include:

- **Reduction in Context-Setting Prompts**: 70% decrease in prompts where users explain project structure or standards

- **Increased Acceptance Rate**: 40% increase in suggestions accepted without modification

- **Documentation Consistency**: 80% reduction in code changes that contradict documentation

- **Design Decision Preservation**: 95% adherence to documented design decisions in AI-generated code

- **Customer Satisfaction**: User satisfaction ratings for contextual accuracy improve by 60%

- **Time Savings**: 25% reduction in time spent per feature implementation

- **Follow-Up Query Reduction**: 50% decrease in follow-up queries where users correct the AI's understanding of the project

## 4. Implementation Tenets

1. **Near Real-Time Indexing**: All changes to project files must be reflected in the metadata index within 10 seconds.

2. **Zero Configuration**: The system must work out-of-the-box without requiring users to configure indexing parameters.

3. **Resource Efficiency**: Indexing operations must maintain minimal CPU/memory footprint using a pure in-memory approach with no database backend.

4. **Documentation Standards Focused**: Only index metadata that follows the documentation standards described in the system prompt file.

5. **Design Decision Preservation**: Actively track and index all design decisions at function, file, and module levels to ensure implementation consistency.

6. **Complete Coverage**: All relevant project metadata, including file structure, headers, comments, and documentation relationships must be indexed.

7. **Local-Only Processing**: All indexing and metadata storage must occur locally to ensure security and privacy.

## 5. Technical Approach

The Documentation-based Programming MCP Server architecture consists of four primary components:

### File Monitoring System
- Uses efficient filesystem watches to detect changes
- Batches updates during high-activity periods
- Employs intelligent filtering to ignore non-relevant files
- Focuses on files that contain documentation following system prompt standards

### Metadata Extraction Engine
- Single generic parser for all file types based on keywords and simple parsing directives
- Keywords and parsing directives generated by Anthropic Claude 3.x models on AWS Bedrock
- Directives generated at startup or when documentation template files change
- Analyzes DOCUMENT_BASED_PROGRAMMING_SYSTEM_PROMPT.md or custom templates
- Header and function comment extraction based on identified documentation patterns
- Documentation relationship mapping
- Comprehensive design decision extraction at function, file, and module levels
- Focus on maintaining global consistency between code and documentation

### Metadata Storage
- Pure in-memory index with no database backend
- Compressed metadata representation
- Optimized for fast query access patterns
- Incremental update support
- Memory-efficient data structures

### Query Interface
- Single-command GraphQL-like API for discretionary data retrieval with powerful capabilities:
  * **Project Business Context**: Specialized access to PR-FAQ and WORKING_BACKWARDS documents with enhanced prioritization for business context (critical for generating accurate mock data, data models, and UX designs that align with business requirements)
  * **Technical Context**: Access DESIGN documents and technical specifications
  * **Document Relationship Graph**: Navigate "depends on:" or "impacts:" relationships as a walkable graph
  * **Header Section Extraction**: Query specific header sections across individual or multiple files
  * **Documentation Inconsistency Detection**: Identify incomplete or missing file headers and sections that break the documentation continuum
  * **Change History Timeline**: Compile all "[GenAI tool change history]" sections and MARKDOWN_CHANGELOG.md files sorted chronologically from newest to oldest
- All metadata returned includes precise location information (file name, directory path, start/end line numbers)
- Fast context gathering at the start of or during conversations
- Context-aware filtering capabilities
- Design decision retrieval prioritization
- Documentation consistency verification
- Relevance scoring for large result sets

### Out of Scope
- Code execution or evaluation
- Security vulnerability scanning
- Performance profiling
- External database storage (intentionally in-memory only)
- Version control integration (planned for future release)

## 6. FAQ for Internal Team

**Q: How will this impact performance on user machines?**
A: The service is designed to be extremely lightweight as a pure in-memory solution with no database backend. It targets minimal resource usage (<5% CPU, <100MB RAM) and employs intelligent throttling during periods of high system load.

**Q: What happens if files change very frequently?**
A: The system implements batching and debouncing mechanisms to handle rapid file changes efficiently, ensuring system stability even during high-frequency updates. The in-memory design allows for very quick incremental updates without disk I/O bottlenecks.

**Q: How do we handle very large projects?**
A: For projects exceeding 100,000 files, the system will employ a more selective indexing strategy, prioritizing files that follow the documentation standards in the system prompt, frequently accessed directories, and files mentioned in recent conversations. The memory-efficient design ensures scalability even for large codebases.

**Q: Can one server instance handle multiple projects?**
A: Yes, a single DBP-S server can simultaneously index and serve multiple isolated codebases. The server maintains complete separation between projects based on their directory paths while efficiently sharing computational resources. This is particularly valuable for developers working across multiple repositories or for teams that want to share a server instance across related projects.

**Q: How does this integrate with Cline's existing context management?**
A: The Documentation-based Programming MCP Server provides a new tool that Cline can use to enrich its context understanding, complementing rather than replacing its existing context management capabilities. It specifically focuses on documentation standards compliance and design decision consistency.

**Q: How does the system adapt to different documentation formats?**
A: The DBP-S is flexible in how it handles documentation standards. By default, it uses the format defined in DOCUMENT_BASED_PROGRAMMING_SYSTEM_PROMPT.md, but it will automatically detect and use project-specific formats from `<codebase>/coding_assistant/GENAI_HEADER_TEMPLATE.txt` when available. This flexibility allows each project to maintain its own documentation approach while still benefiting from consistent indexing.

**Q: How does the system handle various programming languages?**
A: The system uses a generic approach that works across programming languages. Rather than implementing specialized parsers for each language, it uses a single parser based on keywords and simple parsing directives. These directives are generated by Anthropic Claude 3.7 Sonnet and 3.5 Haiku models on AWS Bedrock by analyzing the documentation templates. This generation happens at server startup or when template files change, allowing the system to adapt to any programming language without language-specific parsers.

**Q: What about binary files and non-code assets?**
A: The system focuses primarily on text-based source files that follow the documentation standards defined in the system prompt, though it will track binary files in the directory structure. Content indexing is limited to text-based sources to optimize memory usage in the in-memory index.

**Q: Who developed this server?**
A: The Documentation-based Programming MCP Server was developed by Jean-Charles JOREL (jeancharlesjorel@gmail.com) to address the specific challenges of maintaining consistency between code and documentation in projects using Cline's AI assistant.

## About Cline

[Cline](https://github.com/cline/cline) is an open-source, terminal-based AI coding assistant designed to enhance developer productivity through contextually aware code generation, explanation, and modification. The project aims to:

- **Maintain Terminal Workflow**: Operate entirely within the terminal to preserve developer efficiency
- **Enhance Context Awareness**: Deeply understand project structure and coding patterns
- **Support Seamless Collaboration**: Function as an AI pair programmer that adapts to developer preferences
- **Respect Development Practices**: Generate code that aligns with established project standards

As a terminal-first tool, Cline differentiates itself from GUI-based AI assistants by integrating directly into developers' existing command-line workflows, providing powerful AI capabilities without disrupting productivity.
