# Documentation Management and Standards

## Consistency Protection
When proposed code changes would contradict existing documentation:
1. STOP implementation immediately without proceeding further
2. Quote the contradicting documentation exactly: "Documentation states: [exact quote]"
3. Present exactly two options to the user:
   - "OPTION 1 - ALIGN WITH DOCS: [specific code implementation that follows documentation]"
   - "OPTION 2 - UPDATE DOCS: [exact text changes required to align documentation with code]"
4. For conflicts between documentation files, request explicit clarification on which document takes precedence

## Documentation Standards

**All texts you generate within function/class comments, file headers, or documentation MUST NEVER refer to past implementations.**

### Markdown File Standards
- Markdown files will heavily use mermaid diagrams to ease understanding by user
- All markdown files MUST use UPPERCASE_SNAKE_CASE naming format (examples: DESIGN.md, DATA_MODEL.md)
- Every directory that contains markdown files must include a corresponding MARKDOWN_CHANGELOG.md file
- Documentation files must avoid duplicating information that already exists in other documentation files
- Implement cross-references with direct links between related documentation files rather than duplicating content

## Design Decision Documentation
Document design decisions at the appropriate scope level ONLY when the user explicitly requests it:

- **Module-level decisions**: 
  * Add the decision to `<module_path>/DESIGN_DECISIONS.md`
  * Also replicate the exact same decision in `<project_root>/doc/DESIGN_DECISIONS.md`

- **Project-level decisions**: 
  * Add the decision to `<project_root>/doc/DESIGN_DECISIONS.md`
  * This content must be periodically integrated into the appropriate core documentation files (DESIGN.md, SECURITY.md, DATA_MODEL.md, CONFIGURATION.md, API.md) when the user specifically requests this integration

Note: All DESIGN_DECISIONS.md files must follow the pattern of adding newest entries at the top of the file. If any design decision directly contradicts or creates inconsistency with any core documentation file (DESIGN.md, SECURITY.md, DATA_MODEL.md, CONFIGURATION.md, API.md), update that core file immediately and directly instead of adding to DESIGN_DECISIONS.md.

## Design Decision Merging Process
When the user explicitly requests to merge `<project_root>/doc/DESIGN_DECISIONS.md` into appropriate files:
1. Process entries from oldest to newest (bottom-up in the file order)
2. Perform deep integration rather than simple copying by:
   * Analyzing the impact on all referenced documentation
   * Seamlessly integrating each concept into the existing documentation structure
3. During the merge process, discard these specific sections:
   * "Alternatives considered" 
   * "Implications"
   * "Relationship to Other Components" 
4. Update the appropriate core documentation files based on content relevance (DESIGN.md, SECURITY.md, DATA_MODEL.md, CONFIGURATION.md, API.md)
5. After successful integration, remove the merged entries from DESIGN_DECISIONS.md

After each decision is documented, provide this exact confirmation format:
```
[DESIGN DECISION DOCUMENTED]
Scope: [Function/Class method/Class/File/Module]-level
Decision: [brief description]
Location: [file path and section]
```

## Documentation Relationships Management
When updating any documentation file:
1. First check `doc/DOCUMENT_RELATIONSHIPS.md` to identify all related documents
2. Verify complete consistency across all related documents
3. When conflicts are found, present specific resolution options to the user
4. For any new document relationships, update `doc/DOCUMENT_RELATIONSHIPS.md` using this exact format:
   ```
   ## [Primary Document]
   - Depends on: [Related Document 1] - Topic: [subject matter] - Scope: [narrow/broad/specific area]
   - Impacts: [Related Document 2] - Topic: [subject matter] - Scope: [narrow/broad/specific area]
   ```
5. Update the "Relationship Graph" Mermaid diagram in DOCUMENT_RELATIONSHIPS.md to reflect all new or modified "Depends on:" relationships
6. Explicitly document all relationship updates in your response to the user

When significant changes are identified that are not reflected in documentation:
1. Create specific documentation updates with precise file location and exact content changes
2. For complex documentation changes, create a dedicated file: `<project_root>/scratchpad/<implementation_plan_name_in_lower_snake_case>/doc_update.md`

DESIGN_DECISIONS.md files must **NEVER** be part of identified relationships.

*Place a relationship mermaid diagram at top of DOCUMENT_RELATIONSHIPS.md file*
