
## Documentation Intent and Expectations

### Core Documentation Files
- **`<project_root>/coding_assistant/GENAI_HEADER_TEMPLATE.txt`**: Contains the standardized header template for source files. Used to maintain consistency across the codebase and ensure GenAI tools have proper context.

- **`<project_root>/doc/DESIGN.md`**: The architectural blueprint of the project. Defines system components, their interactions, design patterns, and technical decisions. MUST be consulted before implementing any changes to understand the overall architecture.
  - **When DESIGN.md becomes too large**, child markdown files are created in `<project_root>/doc/design/` to document specific aspects in greater detail
  - DESIGN.md contains navigation links to all child documents
  - Child documents contain cross-references to siblings and DATA_MODEL.md to avoid duplication

- **`<project_root>/doc/DATA_MODEL.md`**: Definitive source for database schema, entity relationships, and data structures. Includes table definitions, field types, constraints, indexes, and relationships between entities.
  - **When DATA_MODEL.md becomes too large**, child markdown files are created in `<project_root>/doc/data_model/` to document specific data structures in greater detail
  - DATA_MODEL.md contains navigation links to all child documents
  - Child documents contain cross-references to siblings to avoid duplication
  - **CRITICAL: DATA_MODEL.md and all its child documents MUST be kept in sync at all times**

- **`<project_root>/doc/DOCUMENT_RELATIONSHIPS.md`**: Maintains dependencies between documentation files. Ensures changes to one document trigger appropriate updates in related documents. Format follows a directed graph structure with "Depends on" and "Impacts" relationships.

- **`<project_root>/doc/PR-FAQ.md`**: **Follows Amazon's specific working backwards methodology structure**. Written from the future perspective of a completed feature as an internal press release with frequently asked questions. Contains sections for headline, problem statement, solution, customer quote, and detailed FAQs. The authoritative source for business intent and feature success criteria.

- **`<project_root>/doc/WORKING_BACKWARDS.md`**: **Written in Amazon's working backwards format**. Contains the product vision articulated through customer-focused narratives, tenets, and user experience descriptions. Used to validate that implementation decisions align with product direction and customer outcomes.

### Implementation Documentation (Ephemeral Working Documents)
**IMPORTANT: All files in the scratchpad directory are EPHEMERAL working documents and NOT sources of truth. They facilitate implementation but hold no authoritative status in the project.**

- **`<project_root>/scratchpad/{TASK_NAME}_PLAN.md`**: Temporary implementation plan for complex tasks. Contains discrete, executable steps, assumptions, dependencies, success criteria, and references to all relevant files. Should be treated as a working document that may become outdated.

- **`<project_root>/scratchpad/{TASK_NAME}_PLAN_CHANGELOG.md`**: Temporary tracking document for implementation progress with chronological entries detailing completed, in-progress, and failed tasks. Meant only for short-term implementation tracking, not long-term reference.

- **`<project_root>/scratchpad/{TASK_NAME}_DOC_UPDATE.md`**: Temporary container for proposed documentation updates. Content from this file should be transferred to official documentation and then considered obsolete.

### Permanent Documentation
- **`MARKDOWN_CHANGELOG.md`**: Located in each directory containing markdown files, tracks changes to documentation files in that directory only. Each entry includes timestamp and summary of changes to specific markdown files.

- **`<module_path>/DESIGN_DECISIONS.md`**: Documents module-level design decisions including rationale, alternatives considered, and implications. Serves as the authoritative record for architectural choices within a module.

### References in File Headers
- **`[Reference documentation]`**: Lists in file headers must only reference markdown files in the doc/ directory that provide essential context for understanding and maintaining the file. Never reference ephemeral scratchpad files.

When accessing any of these documents, adhere to these principles:
1. Treat official documentation (not scratchpad files) as the source of truth for intended behavior
2. Verify document content against expected structure described above
3. Report any structural deviations from these expectations
4. Prioritize newer documentation (check timestamps) when conflicts exist
5. Consider documentation completeness when evaluating implementation confidence
6. Never treat scratchpad files as authoritative; they are implementation aids only
