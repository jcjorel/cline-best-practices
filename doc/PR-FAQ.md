# PRESS RELEASE

## Introducing Documentation-based Programming MCP Server (DBP-S) for Cline: Near Real-Time Context for Smarter AI Coding Assistance
*Cline's AI Assistant now understands your project structure instantly with automatic code metadata indexing*

PARIS, FRANCE—April 12, 2025—Today, Jean-Charles JOREL (jeancharlesjorel@gmail.com) announced the release of the Documentation-based Programming MCP Server (DBP-S), a powerful new enhancement that enables Cline's AI assistant to instantly access and understand your entire project's structure, documentation, and relationships. By continuously indexing project metadata in near real-time, the Cline AI assistant now delivers more accurate, contextually-aware coding recommendations that truly understand your project's architecture and documentation standards.

Developers using Cline frequently need to remind the AI assistant about their project's structure, conventions, and existing documentation—a repetitive process that interrupts workflow and diminishes productivity. With the new DBP-S, Cline automatically indexes all file metadata, standardized headers, function comments, and documentation relationships within 10 seconds of any file change, ensuring the AI assistant always has the most up-to-date understanding of your project. Crucially, the server retrieves design decisions documented throughout the codebase, helping maintain global consistency between code and documentation—the core goal of this MCP server.

"I built the Documentation-based Programming MCP server because developers were spending too much time helping the AI assistant understand their project context," said Jean-Charles JOREL. "Now, with automatic indexing and a comprehensive metadata retrieval system, Cline's AI assistant delivers significantly more relevant suggestions that respect your project's existing patterns and documentation standards without requiring constant reminders, while ensuring design decisions remain consistent throughout the project."

The DBP-S is available today for all Cline users. Activation requires no additional configuration—the server automatically begins indexing once installed, maintaining a lightweight in-memory index (with no database backend) that updates within seconds of any file change. This makes implementing Documentation-based Programming practical and efficient, as the server handles all the complexity of maintaining consistency between code and documentation.

This release represents another step in Cline's mission to create truly context-aware AI coding assistants that seamlessly integrate with developer workflows, reducing cognitive overhead and enabling developers to focus on solving interesting problems rather than explaining project context or maintaining documentation consistency. As an open-source project focused on terminal-based AI assistance, Cline with DBP-S now offers unprecedented context awareness without disrupting efficient command-line workflows.

# FREQUENTLY ASKED QUESTIONS

## Q: What is Documentation-based Programming?
A: Documentation-based Programming (DBP) is a development approach that treats documentation as the single source of truth in a project. In this paradigm, documentation—including file headers, function comments, and standalone documentation files—takes precedence over code itself. The core benefits of this approach include:

- **Documentation-First Development**: Features begin with documentation updates, which are refined before updating code, ensuring well-thought-out designs
- **Consistent Source of Truth**: Code and documentation remain in sync by design, eliminating drift between stated intent and implementation
- **Reduced LLM Context Requirements**: By maintaining comprehensive documentation, AI assistants like Cline can understand project context without needing to process and parse complex code structures
- **Automatic Synchronization**: When code is modified directly, documentation is automatically updated to maintain consistency
- **Focus on Design Intent**: Developers concentrate on communicating design intent clearly, leading to more maintainable systems

## Q: What specific metadata does the Documentation-based Programming MCP Server index?
A: The server indexes multiple types of project metadata, but specifically focuses on metadata that follows the documentation standards described in the system prompt file:
- Complete file paths and directory structures
- File extensions and sizes
- Standardized file headers and function comments
- Documentation relationships between files
- Design decisions documented in the codebase (at function, file, and module levels)
- Available markdown changelogs

All this information is extracted and made available through a simple, unified GraphQL-like querying interface (a single command), with particular emphasis on maintaining consistency between code and documentation. This single-command approach allows for fast, discretionary data retrieval exactly when needed, significantly speeding up context gathering at the start of or during a conversation. The command can retrieve:

1. **Project Business Context**: Specialized access to PR-FAQ and WORKING_BACKWARDS documents to understand project vision and business rationale (critical for generating business-aligned mock data, data models, and UX designs)
2. **Technical Context**: Retrieve DESIGN documents and technical specifications
3. **Document Relationship Graph**: Navigate through "depends on:" or "impacts:" relationships for any file, organized as a walkable graph regardless of file location in the codebase
4. **Standardized Header Sections**: Retrieve all or selective header sections by individual file or across multiple files (e.g., get all design decisions or constraints across the entire project)
5. **Documentation Inconsistencies**: Identify incomplete or missing file headers and sections that break the documentation continuum, allowing targeted remediation of documentation gaps
6. **Change History Timeline**: Gather all "[GenAI tool change history]" sections and MARKDOWN_CHANGELOG.md files across the codebase sorted from newest to oldest to quickly understand recent project activities

All metadata returned by the command includes precise location information (file name, directory, start/end line numbers), enabling direct navigation to the source of any metadata item.

## Q: How does this improve Cline's capabilities compared to before?
A: Previously, Cline's AI assistant would have limited visibility into your project structure, requiring you to repeatedly provide context about file organization, coding standards, and documentation relationships. The DBP-S eliminates this friction by making all this information instantly available to the AI assistant through a single command interface, resulting in:
- More accurate and contextually relevant suggestions
- Better adherence to your project's established patterns and practices
- Reduced need to correct the AI when it misunderstands project structure
- Global consistency between code implementations and documentation
- Identification of documentation inconsistencies that need remediation
- Preservation of design decisions throughout the development lifecycle
- Business-aware recommendations through prioritization of Amazon-style PR-FAQ and WORKING_BACKWARDS documents
- Significantly faster responses that incorporate knowledge of your entire codebase

## Q: How is the metadata kept up-to-date?
A: The DBP-S implements an efficient file system monitoring system that detects any changes to project files within 10 seconds of modification. When changes are detected, only the affected files are re-indexed, ensuring minimal system resource usage while maintaining near real-time accuracy of the metadata index. Being a pure in-memory indexer with no database backend, it provides exceptional performance with minimal overhead.

## Q: Will this affect my system's performance?
A: The DBP-S is designed to be extremely lightweight. As a pure in-memory indexer without any database, the indexing process runs as a background task with minimal CPU and memory usage. The server intelligently batches updates during periods of high file change activity and employs incremental indexing to minimize resource consumption. For most projects, the performance impact is negligible.

## Q: How does the DBP-S handle large codebases?
A: The server employs several optimization strategies for large codebases:
1. Incremental indexing that processes only changed files
2. Intelligent file filtering to exclude binary files, build artifacts, and dependency directories
3. Throttled processing during periods of high activity
4. Compressed storage of metadata in memory
5. Selective indexing based on documentation standards in the system prompt
These optimizations allow the server to efficiently handle codebases with thousands of files while maintaining responsiveness, all without requiring a database backend.

## Q: Can a single DBP-S instance serve multiple projects?
A: Yes, a single DBP-S server can index and serve multiple isolated codebases simultaneously. As long as different MCP clients use different codebase directories, the server maintains complete separation between projects while efficiently sharing computational resources. This capability is particularly useful for developers working on multiple projects or for teams sharing a server instance across related codebases.

## Q: How does the system know which documentation standards to follow?
A: The DBP-S is flexible in its approach to documentation standards. By default, it uses the format defined in the DOCUMENT_BASED_PROGRAMMING_SYSTEM_PROMPT.md file. However, if a project has its own custom header template at `<codebase>/coding_assistant/GENAI_HEADER_TEMPLATE.txt`, the server will detect and use that format instead. This allows each project to maintain its own documentation standards while still benefiting from the DBP-S's metadata indexing capabilities.

## Q: Does the DBP-S use AI models for parsing?
A: Yes, but with a generic approach. The DBP-S uses a single generic parser that relies on keywords (section names) and simple parsing directives generated by Anthropic Claude 3.7 Sonnet and 3.5 Haiku models on AWS Bedrock. These directives are generated at server startup or when a change is detected in the documentation template file. The system analyzes either the DOCUMENT_BASED_PROGRAMMING_SYSTEM_PROMPT.md file or the `<codebase>/coding_assistant/GENAI_HEADER_TEMPLATE.txt` file (if it exists) to understand the documentation structure. This approach maintains maximum flexibility across different programming languages and file types without requiring specialized parsers for each language.

## Q: Is my code secure with this indexing service running?
A: Yes. The DBP-S runs entirely locally on your machine. No code or metadata is ever transmitted to external servers. The indexed metadata remains within your local memory environment and is only accessed by the Cline AI assistant running on your machine. Since it operates as a pure in-memory solution with no database, there are no data persistence concerns once the service is stopped.

## Q: What's on the roadmap for future enhancements?
A: Future enhancements being considered include:
- Code complexity metrics and quality indicators
- Function and class dependency graphs
- Semantic understanding of code relationships
- Design decision impact analysis
- Documentation consistency verification
- Integration with version control history
- Support for custom documentation standard plugins

## About Cline

[Cline](https://github.com/cline/cline) is an open-source, terminal-based AI coding assistant designed to enhance developer productivity through contextually aware code generation, explanation, and modification. Built with a focus on developer experience, Cline integrates directly into terminal workflows and aims to be the most effective AI pair programmer by deeply understanding project context and developer intent. Unlike many AI assistants, Cline operates entirely in the terminal, maintaining the efficiency of command-line workflows while providing powerful AI assistance.
