# Code Generation Rules

## KISS (Keep It Simple & Stupid) Systematic Approach
When you design a solution and/or generate code, you will systematically apply a KISS (Keep It Simple & Stupid) approach as generating non-requested features is confusing the user and contradicts your core role of caring assistant:
- Implement exactly what the user requested - no more, no less
- Avoid adding "nice-to-have" features or optimizations unless explicitly requested
- Choose straightforward implementations over clever or complex ones
- Break down complex solutions into simple, understandable components
- Prioritize readability and maintainability over brevity or elegance
- When multiple implementation options exist, default to the simplest one that meets requirements
- Proactively highlight when a requested feature might be unnecessary or overly complex

## Error Handling Strategy
You know that safe coding is to not bury issues with workarounds and fallbacks. You will prefer to find issue root cause immediatly by crashing
the software (defensive programming) instead of fallbacking to a degraded mode difficult to debug.
- Implement "throw on error" behavior for ALL error conditions without exception
- Do not silently catch errors - always include both error logging and error re-throwing
- Never return null, undefined, or empty objects as a response to error conditions
- Construct descriptive error messages that specify: 1) the exact component that failed and 2) the precise reason for the failure
- **NEVER implement any fallback mechanisms or graceful degradation behavior without explicitly user approval**

## Code and Documentation Standards

### DRY Principle Implementation
Strictly adhere to the DRY (Don't Repeat Yourself) principle in all implementations:
- Identify and eliminate any duplicate logic in code
- Extract common functionality into dedicated reusable components
- Apply inheritance, composition, and abstraction patterns appropriately
- Refactor existing code sections when introducing similar functionality
- Prevent information duplication across documentation files
- Use cross-references between documents instead of copying content
- Establish single sources of truth for any information that appears in multiple places
- Proactively identify repeated patterns before committing any changes

### File Modification Rules
- Add or maintain header comments in every file using the applicable template
- When modifying files exceeding 500 lines, process them in logical sequences of maximum 5 operations
- Document all changes in the GenAI history section using precise timestamp format: YYYY-MM-DDThh:mm:ssZ
- **After updating any codebase file, ALWAYS ensure that function/class method/class comments are consistent with the changes made**
- **ALWAYS update the file header history section with details of the modifications**
- **ALWAYS update the file header intent and design principles to align them with performed modifications**
- For markdown file modifications:
  - Always update the corresponding `MARKDOWN_CHANGELOG.md` located in the SAME directory
  - Format changelog entries exactly as: `YYYY-MM-DDThh:mm:ssZ : [filename.md] change summary`
  - Enforce a strict 20-entry limit in all MARKDOWN_CHANGELOG.md files, removing the oldest entries when this limit is reached
- After any file modification, verify file existence and validate syntax correctness
