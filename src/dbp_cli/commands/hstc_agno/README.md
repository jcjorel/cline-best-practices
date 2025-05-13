# HSTC Agno CLI Commands

This document describes the command-line interface for the HSTC implementation with Agno.

## Command Overview

The `hstc_agno` command group provides tools for managing Hierarchical Semantic Tree Context (HSTC)
documentation using the Agno framework and Amazon Bedrock models.

### Available Commands

- `update`: Update documentation for a single file
- `update-dir`: Update documentation for all files in a directory
- `status`: Check documentation status for a file or directory
- `view`: View the generated documentation
- `clear-cache`: Clear the HSTC cache
- `save-cache`: Save the HSTC cache to a file
- `load-cache`: Load the HSTC cache from a file

## Usage Examples

### Update a single file

```bash
dbp_cli hstc_agno update path/to/file.py
```

### Update all Python files in a directory

```bash
dbp_cli hstc_agno update-dir src/module --pattern "*.py"
```

### Check documentation status

```bash
dbp_cli hstc_agno status path/to/file.py --verbose
```

### View generated documentation

```bash
dbp_cli hstc_agno view path/to/file.py --output-format markdown
```

## Options

### Global Options

- `--verbose/--quiet`: Show detailed output

### Update Options

- `--output, -o`: Output directory for implementation plan
- `--recursive/--no-recursive`: Process dependencies recursively

### Update Directory Options

- `--output, -o`: Output directory for implementation plans
- `--recursive/--no-recursive`: Process dependencies recursively
- `--recursive-dir/--no-recursive-dir`: Process subdirectories recursively
- `--pattern, -p`: File patterns to include (can be specified multiple times)

### View Options

- `--output-format, -f`: Output format (text, json, markdown)

## Cache Management

The HSTC Agno module maintains a cache of analyzed files to speed up processing. You can manage this cache with the following commands:

```bash
# Clear the cache
dbp_cli hstc_agno clear-cache

# Save the cache to a file
dbp_cli hstc_agno save-cache cache_file.json

# Load the cache from a file
dbp_cli hstc_agno load-cache cache_file.json
