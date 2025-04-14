# Design Decisions

This document serves as a temporary log of project-wide design decisions that have not yet been incorporated into the appropriate documentation files. Decisions are recorded with newest entries at the top and should be periodically synced to appropriate documentation files (DESIGN.md, SECURITY.md, DATA_MODEL.md, CONFIGURATION.md).

## Simplified Recommendation System (2025-04-14)

**Decision**: Replace the FIFO queue-based recommendation system with a simplified single-recommendation approach.

**Rationale**: The original FIFO queue design adds unnecessary complexity to both the implementation and the user experience. A single-recommendation approach creates a clearer mental model for users and reduces system overhead.

**Key Changes**:
- Generate only one recommendation at a time instead of maintaining a queue
- Keep the existing recommendation format and PENDING_RECOMMENDATION.md
- Automatically invalidate and remove recommendations when any codebase change occurs
- Eliminate the recommendations/ directory structure
  
**Key Implications**:
- Simpler user interaction model (single decision point)
- More responsive feedback loop for users
- Reduced complexity in the recommendation tracking system
- Potential for faster recommendation regeneration after code changes
- Elimination of queue management code and related database structures

**Impacts**:
- DESIGN.md: Recommendation Workflow section
- DATA_MODEL.md: Recommendation data model
- File Structure section in multiple documents

There were previously no pending design decisions to be merged. All previously recorded decisions have been successfully incorporated into the appropriate documentation files:

- Database Architecture → DATA_MODEL.md
- Configuration Strategy → CONFIGURATION.md
- Recommendation Lifecycle Management → DATA_MODEL.md 
- Code Structure Governance → DESIGN.md
- LLM Processing Approach → DESIGN.md
- Prompt Template Management → design/INTERNAL_LLM_TOOLS.md
- Enhanced Metadata Extraction → DATA_MODEL.md
- MCP Client Security → SECURITY.md
- Implementation Principles → DESIGN.md

The last integration was completed on 2025-04-14T19:25:00Z.
