# PRESS RELEASE

## Introducing Documentation-based Programming MCP Server (DBP-S) for Cline
*Stop repeating yourself to AI assistants - save 20% of your time with instant project context*

PARIS, FRANCE—April 12, 2025—Today, Jean-Charles JOREL (jeancharlesjorel@gmail.com) announced the release of the Documentation-based Programming MCP Server (DBP-S) for Cline. 

Developers waste valuable time repeatedly explaining their project structure and coding standards to AI assistants. A senior developer noted: "I spend at least 20% of my interactions with Cline just reminding it about our project structure and coding standards." This repetitive context-setting interrupts workflow, diminishes productivity, and leads to inconsistent code suggestions that don't align with established project patterns.

The new Documentation-based Programming MCP Server eliminates this frustration by automatically indexing project metadata within 10 seconds of any file change. It captures file structure, standardized headers, function comments, and documentation relationships, ensuring Cline always has the most up-to-date understanding of your project. The server specifically indexes design decisions documented throughout your codebase, maintaining perfect consistency between code and documentation.

"I built the Documentation-based Programming MCP server because developers were spending too much time helping the AI assistant understand their project context," said Jean-Charles JOREL. "Now, with automatic indexing and a comprehensive metadata retrieval system, Cline delivers significantly more relevant suggestions that respect your project's existing patterns without requiring constant reminders."

The DBP-S is available today for all Cline users. It requires no configuration—the server automatically begins indexing once installed, maintaining a lightweight in-memory index that updates within seconds of any file change.

This release advances Cline's mission to create truly context-aware AI coding assistants that seamlessly integrate with developer workflows. Developers can now focus on solving interesting problems rather than explaining project context or maintaining documentation consistency.

# FREQUENTLY ASKED QUESTIONS

## Q: What is Documentation-based Programming?
A: Documentation-based Programming (DBP) treats documentation as the single source of truth in a project. Documentation—including file headers, function comments, and standalone files—takes precedence over code itself. The benefits include:

- **Documentation-First Development**: Features begin with documentation updates, ensuring well-thought-out designs
- **Consistent Source of Truth**: Code and documentation remain in sync, eliminating drift between intent and implementation
- **Reduced LLM Context Requirements**: AI assistants understand project context without parsing complex code
- **Automatic Synchronization**: When code changes, documentation updates automatically
- **Focus on Design Intent**: Developers communicate design intent clearly, leading to more maintainable systems

## Q: How will DBP-S save me time in my daily work?
A: DBP-S eliminates repetitive context-setting that typically consumes 20% of AI assistant interactions. You'll no longer need to:
- Repeatedly explain your project structure
- Remind the AI about coding standards and patterns
- Correct misaligned code suggestions
- Manually maintain documentation consistency

Instead, you ask questions directly and receive accurate, contextually-aware responses that respect your project's established patterns.

## Q: What specific metadata does the Documentation-based Programming MCP Server index?
A: The server indexes project metadata that follows your documentation standards:
- Complete file paths and directory structures
- File extensions and sizes
- Standardized file headers and function comments
- Documentation relationships between files
- Design decisions at function, file, and module levels
- Markdown changelogs

The server makes this information available through a simple querying interface that provides:

1. **Project Business Context**: Direct access to PR-FAQ and WORKING_BACKWARDS documents
2. **Technical Context**: Access to DESIGN documents and specifications
3. **Document Relationship Graph**: Navigation through document relationships
4. **Standardized Header Sections**: Retrieval of specific header sections across files
5. **Documentation Inconsistencies**: Identification of incomplete documentation
6. **Change History Timeline**: Chronological view of project changes

All metadata includes precise location information for direct navigation.

## Q: How does this improve Cline's capabilities compared to before?
A: Previously, Cline had limited visibility into your project structure, requiring you to repeatedly explain context. The DBP-S eliminates this friction by making all project information instantly available, resulting in:
- More accurate and contextually relevant suggestions
- Better adherence to established patterns and practices
- Reduced need to correct misunderstandings about project structure
- Global consistency between code and documentation
- Automatic identification of documentation gaps
- Preservation of design decisions throughout development
- Business-aware recommendations through PR-FAQ and WORKING_BACKWARDS documents
- Faster responses incorporating knowledge of your entire codebase

## Q: How exactly does the system keep metadata up-to-date?
A: The system detects file changes within 10 seconds using an efficient file system monitor. When changes occur, it only re-indexes affected files, ensuring minimal resource usage while maintaining accurate metadata. As a pure in-memory indexer with no database, it provides exceptional performance with minimal overhead.

## Q: Will this slow down my computer?
A: No. The DBP-S runs as a lightweight background task using less than 5% CPU and under 100MB RAM. It intelligently batches updates during high activity periods and uses incremental indexing to minimize resource impact. For most projects, you won't notice any performance difference.

## Q: I work on a large codebase with thousands of files. Will DBP-S handle this?
A: Yes. The server implements five specific optimizations for large codebases:
1. Incremental indexing of only changed files
2. Intelligent filtering that excludes binary files and build artifacts
3. Throttled processing during high activity
4. Compressed storage of metadata in memory
5. Selective indexing based on documentation standards
These optimizations efficiently handle codebases with thousands of files without requiring a database.

## Q: Can I use DBP-S across multiple projects?
A: Yes. A single DBP-S instance simultaneously indexes and serves multiple isolated codebases. It maintains complete separation between projects while efficiently sharing resources. This works perfectly for developers managing multiple repositories or teams sharing server instances.

## Q: How do I integrate DBP-S with my existing documentation practices?
A: DBP-S adapts to your documentation standards. By default, it uses the format in DOCUMENT_BASED_PROGRAMMING_SYSTEM_PROMPT.md. If your project has a custom template at `<codebase>/coding_assistant/GENAI_HEADER_TEMPLATE.txt`, the server automatically detects and uses that format. This flexibility allows you to maintain your existing documentation approach.

## Q: Does DBP-S work with all programming languages?
A: Yes. Rather than using language-specific parsers, DBP-S uses a single generic parser based on keywords and parsing directives generated by Anthropic Claude models. This approach works effectively across all programming languages and file types.

## Q: Is my code secure with this indexing service?
A: Absolutely. DBP-S runs entirely on your local machine. No code or metadata leaves your system or gets transmitted to external servers. All indexed metadata stays in your local memory and is only accessed by Cline running on your machine. Since it's a pure in-memory solution with no database, no data persists after the service stops.

## Q: What's on the roadmap for future versions?
A: We're actively developing:
- Code complexity metrics and quality indicators
- Function and class dependency graphs
- Semantic understanding of code relationships
- Design decision impact analysis
- Documentation consistency verification
- Version control history integration
- Custom documentation standard plugins

## Q: Are there any version control integration features available now?
A: Yes. The DBP-S MCP server includes a dedicated command to build Git commit messages that gather and summarize changes since your last commit. This intelligent feature not only lists what changed but also analyzes the potential impacts of these changes across your codebase. The feature leverages Anthropic Claude on AWS BedRock to provide comprehensive, contextually aware commit messages that save developers time and improve repository documentation quality.

## About Cline

[Cline](https://github.com/cline/cline) is an open-source, terminal-based AI coding assistant that enhances developer productivity through contextually aware code generation, explanation, and modification. Unlike GUI-based AI assistants, Cline integrates directly into terminal workflows, maintaining command-line efficiency while providing powerful AI capabilities.
