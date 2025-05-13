# Legacy CLI Removal Plan

This directory contains a comprehensive plan and implementation scripts for safely removing the former non-Click based CLI implementation from the codebase.

## Overview

The Documentation-Based Programming CLI was previously migrated from an argparse-based implementation to a Click-based implementation. Now that the migration is complete and the new CLI is stable, we need to remove the obsolete non-Click implementation to reduce maintenance burden and prevent confusion.

## Contents

This directory contains the following files:

- **implementation_plan.md**: Comprehensive implementation plan for the removal process
- **file_removal_list.md**: Detailed inventory of files to be removed with their replacements
- **verification_script.py**: Script to verify if it's safe to proceed with removal
- **removal_script.py**: Script to remove the legacy CLI files
- **README.md**: This documentation file

## Removal Process

Follow these steps to safely remove the legacy CLI implementation:

### 1. Review the Implementation Plan

Start by reviewing the implementation plan to understand the removal process:

```bash
cat implementation_plan.md
```

### 2. Run the Verification Script

Run the verification script to determine if it's safe to proceed with removal:

```bash
cd /home/jcjorel/cline-best-practices  # Change to the project root
python3 scratchpad/cli_removal_plan/verification_script.py --output-dir scratchpad/cli_removal_plan
```

This generates a verification report that analyzes:
- References to the legacy CLI in other files
- Whether entry points in setup.py have been updated
- Command comparison between old and new implementations
- Overall safety assessment

### 3. Review the Verification Report

Check the generated verification report to ensure it's safe to proceed:

```bash
# Find the latest report
ls -lt scratchpad/cli_removal_plan/cli_removal_verification_*
# Review the report
cat scratchpad/cli_removal_plan/cli_removal_verification_YYYYMMDD_HHMMSS.md
```

Look for the "✅ Safe to proceed with removal" message in the summary.

### 4. Dry Run Removal

Perform a dry run to see what would be removed without making any changes:

```bash
python3 scratchpad/cli_removal_plan/removal_script.py --dry-run
```

### 5. Perform the Removal

If the verification passed and the dry run looks good, proceed with the removal:

```bash
python3 scratchpad/cli_removal_plan/removal_script.py
```

This will:
- Create a backup branch in Git
- Remove the legacy CLI files in the correct order
- Move any special files to their new locations
- Clean up empty directories

### 6. Test the Application

After removal, test the application to ensure everything works correctly:

```bash
# Run some basic tests with the Click CLI
python -m dbp_cli.cli_click.__main__ --help
python -m dbp_cli.cli_click.__main__ config --help
# Run any other necessary tests
```

## Troubleshooting

### Verification Failed

If the verification script indicates it's not safe to proceed:

1. Review the references found in other files and update them to use the new CLI
2. Check if entry points in setup.py have been updated to point to the new CLI
3. Verify that all commands have been migrated from the old to the new implementation
4. Run the verification script again

### Forcing Removal

If you need to proceed with removal despite verification failures:

```bash
python3 scratchpad/cli_removal_plan/removal_script.py --force
```

⚠️ **Warning**: Only use this if you understand the potential consequences and have a backup.

### Rollback

If issues are encountered after removal, you can restore the removed files from the backup branch:

```bash
# List backup branches
git branch | grep backup/pre-cli-removal

# Restore specific files from the backup branch
git checkout backup/pre-cli-removal-YYYYMMDDHHMMSS -- src/dbp_cli/commands/
git checkout backup/pre-cli-removal-YYYYMMDDHHMMSS -- src/dbp_cli/cli.py
git checkout backup/pre-cli-removal-YYYYMMDDHHMMSS -- src/dbp_cli/__main__.py

# Commit the restoration
git commit -m "Restore legacy CLI due to issues"
```

## Files Removed

The removal process will remove the following files and directories:

1. Core CLI files:
   - `src/dbp_cli/cli.py`
   - `src/dbp_cli/__main__.py` (if not already updated)

2. Command structure files:
   - `src/dbp_cli/commands/base.py`
   - `src/dbp_cli/commands/click_adapter.py`
   - `src/dbp_cli/commands/__init__.py`

3. Command implementation files:
   - `src/dbp_cli/commands/commit.py`
   - `src/dbp_cli/commands/config.py`
   - `src/dbp_cli/commands/query.py`
   - `src/dbp_cli/commands/server.py`
   - `src/dbp_cli/commands/status.py`
   - `src/dbp_cli/commands/hstc.py`
   - `src/dbp_cli/commands/modeldiscovery.py`

4. Test files:
   - `src/dbp_cli/commands/test/` directory

Special files will be handled as follows:
- `src/dbp_cli/commands/HSTC.md` will be moved to `src/dbp_cli/cli_click/commands/HSTC.md`
