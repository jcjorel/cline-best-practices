# Hierarchical Semantic Tree (HST) Approach

HST provides structured context data through a hierarchy of HSTC.md files located in each project directory. This approach enables efficient semantic navigation of large codebases by maintaining summaries at each level of the directory hierarchy.

## Purpose and Benefits
- Creates a navigable semantic tree providing efficient context about project structure and documentation
- Allows LLMs to gain hierarchical understanding without processing the entire codebase
- Preserves critical file metadata even when original files are outside the context window
- Enables intelligent "drill-down" into relevant code areas based on semantic understanding

## HST Traversal Algorithm
When using HSTC to enrich LLM context, you MUST follow this exact hierarchical traversal pattern:

1. ALWAYS start from the top-level HSTC.md in the project root
2. Process this root HSTC.md file COMPLETELY before proceeding further
3. Based on the user request, identify which child directory is most relevant
4. Move ONLY to that child directory's HSTC.md file (never skip levels)
5. Process this child HSTC.md completely before proceeding further
6. Repeat steps 3-5 recursively, following a strict path down the directory tree
7. Continue until reaching the most specific relevant directory for the user's request
8. Process the final HSTC.md to understand local file context

**CRITICAL: You MUST NEVER read an HSTC.md file without first having read and processed ALL of its ancestor HSTC.md files in the correct hierarchical sequence, starting from the project root**

**CRITICAL: When gathering project context to answer a user request, traversal must always proceed from root toward leaves in strict parent-to-child order, never starting mid-tree or skipping levels**

**CRITICAL: When considering any codebase changes, you MUST gather high-quality context by FOLLOWING STRICTLY the HST Traversal Algorithm to make the best design decisions**

## HSTC.md Standardized Structure
Each HSTC.md file must strictly follow this template format:

```markdown
# Hierarchical Semantic Tree Context: [Directory Name]

## Directory Purpose
[Brief description of this directory's purpose and role in the project architecture - 5-10 sentences. It is effectively a **TECHNICAL ONLY** summary of the rest of the file highlighting architectural information. Add technical significant details if still enough spare sentences.]

## Child Directories
<!-- For each child directory with HSTC.md -->

### [Child Directory Name 1]
["Directory Purpose" section from child's HSTC.md. Rephrase it if contains reference to "parent directory" or other relative positional indication not applicable once merged in the current HSTC.md]

### [Child Directory Name 2]
["Directory Purpose" section from child's HSTC.md. Rephrase it if contains reference to "parent directory" or other relative positional indication not applicable once merged in the current HSTC.md]

<!-- Repeat for all child directories -->

## Local Files

### `filename1.py`
```yaml
source_file_intent: |
  [Content of source file intent section from file header]
  
source_file_design_principles: |
  [Content of design principles section from file header]
  
source_file_constraints: |
  [Content of constraints section from file header]
  
dependencies:
  - kind: <unknown(default)|codebase|system|other>
    dependency: <dependency>
  
change_history:
  - timestamp: "YYYY-MM-DDThh:mm:ssZ"
    summary: "[change summary]"
    details: "[change details]"
  - timestamp: "YYYY-MM-DDThh:mm:ssZ"
    summary: "[change summary]"
    details: "[change details]"
```

<!-- Repeat for all files in directory -->
<!-- End of the file with "End of HSTC.md file" to easily detect potential truncation -->

## HSTC.md Lifecycle Management
When user requests "Update HSTC", execute this precise update sequence:

1. **Update Process**:
   ```
   UPDATE_HSTC(directory_path):
     a. IF directory_path UNSPECIFIED:
        - SET directory_path = <project_root>
     b. Execute the script in coding_assistant/ that will help you identify files to update
     c. IF AT LEAST one HSTC_REQUIRES_UPDATE.md file exists
        - FOR EACH identified_directory
           1. Read modified filenames from <identified_directory>/HSTC_REQUIRES_UPDATE.md
           2. For each filename, extract header and update corresponding entry in HSTC.md
           3. Garbage collect file and directory references in HSTC.md file that do not exist in filesystem
           4. Delete HSTC_REQUIRES_UPDATE.md
     d. ELSE IF AT LEAST one directory_without_HSTC.md:
        - FOR EACH directory_without_HSTC.md
           1. Scan all files in directory
           2. Extract all headers and create new HSTC.md
     e. ELSE:
        - Loop to b. until no more directory to update
     f. UPDATE_HSTC COMPLETED (task completed)
   ```

2. **Critical HST Update Rules**:
   - **ALWAYS update HSTC.md files yourself. Use a script only to gather directories to update.**
   - **During update operation, the critical traversal rule IS MODIFIED and you MUST always process files in the order returned by the identification script**
   - If the script used by UPDATE_HSCT() is identifying a file, always open it and write it even with the same content as we need to update last modification time. 
   - During create/update of a HSTC.md file,
        1. Maintain strict adherence to the standard HSTC.md template format
        2. Ensure all local files (and no more) are listed in each HSTC.md

4. **Change Tracking**:
   - After modifying any file header, log ONLY the filename in `<same_dir>/HSTC_REQUIRES_UPDATE.md`
   - Each file should be listed on a separate line without additional formatting

This standardized approach ensures consistent, navigable semantic trees that provide efficient context for code comprehension and modification.
