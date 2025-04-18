# Design Decision: Allow Direct Alembic CLI Invocation

## Summary
The database migration system should support direct Alembic CLI invocation (`alembic -c alembic.ini upgrade head`) in addition to integrated application-driven migrations. This requires modifications to the migration environment configuration to properly handle different invocation contexts.

## Problem
When running Alembic directly via the CLI command (`alembic -c alembic.ini upgrade head`), migrations weren't being applied because:

1. The `env.py` script was prioritizing the ComponentSystem for configuration
2. When invoked directly, the ComponentSystem isn't initialized, causing the database URL resolution to fail or fall back to unintended defaults
3. The script wasn't checking for and using the database URL from alembic.ini during direct CLI invocation
4. Error reporting was insufficient to diagnose migration failures

## Solution
Modify the Alembic environment script (`env.py`) to:

1. Prioritize using the database URL from `alembic.ini` if running via direct CLI invocation
2. Fall back to ComponentSystem configuration only if running from within the application
3. Add improved diagnostics to report database URL, current migration versions, and migration progress
4. Explicitly check and report on the alembic_version table state to aid debugging

## Implementation
The `get_url()` function in `env.py` has been modified to:
- First check if running directly via alembic command and use config from .ini file
- Only fall back to ComponentSystem if direct config isn't available
- Add informative logging for each configuration source used

The `run_migrations_online()` function has been enhanced to:
- Log the database URL being used for migrations
- Check and report the current alembic_version table state before running migrations
- Add progress reporting during migration execution

## Rationale
This change maintains the convenience of integrated migrations within the application while supporting direct Alembic CLI usage, which is valuable for:
- Manual database maintenance operations
- Database administration by users unfamiliar with the application internals
- Troubleshooting migration issues
- Deployment automation scripts that might run migrations separately

## Alternatives Considered
1. **Require application initialization for all migrations**: Rejected because it reduces flexibility for database administration and maintenance.
2. **Create a separate alembic.ini for direct CLI use**: Rejected because maintaining two configurations would likely lead to inconsistencies.
3. **Create a custom CLI wrapper**: Considered but deferred as the direct approach is simpler and preserves standard Alembic workflows.

## Migration Path
This change is backward compatible with existing deployments. Application-driven migrations continue to work as before, while direct CLI invocation is now properly supported.
