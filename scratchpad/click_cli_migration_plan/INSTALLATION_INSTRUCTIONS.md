# Installation Instructions

These instructions guide you through installing and using the dbp-cli tool with its new Click-based interface.

## Installation Methods

### Method 1: Using pip (Recommended)

```bash
# Install the latest version
pip install dbp-cli

# Or specify a version
pip install dbp-cli==0.1.0
```

### Method 2: From Source

```bash
# Clone the repository
git clone https://github.com/example/dbp-cli.git
cd dbp-cli

# Install in development mode
pip install -e .
```

### Method 3: Using a requirements file

```bash
# Create a requirements.txt file containing:
# dbp-cli>=0.1.0

pip install -r requirements.txt
```

## Verifying Installation

After installation, verify that both CLI versions are available:

```bash
# Check legacy CLI version
dbp --version

# Check new Click-based CLI version
dbp-click --version
```

Both commands should display the same version number, confirming successful installation of both interfaces.

## Using the New CLI

The new Click-based CLI is available as `dbp-click`:

```bash
# Show help
dbp-click --help

# Run a command
dbp-click query "Your query here"
```

See the [Migration Guide](MIGRATION_GUIDE.md) for detailed information on transitioning from the legacy `dbp` command to the new `dbp-click` command.

## Configuration

Both the legacy CLI and the new Click-based CLI use the same configuration file and environment variables:

```bash
# Set configuration file location
dbp-click --config /path/to/config.yaml

# Or using environment variables
export DBP_CLI_CONFIG=/path/to/config.yaml
dbp-click status
```

## Dependencies

The dbp-cli package requires:

- Python 3.8 or higher
- click >= 8.0.0
- colorama >= 0.4.4
- requests >= 2.25.0
- boto3 >= 1.38.0
- agno >= 1.0.0

## Virtual Environment (Recommended)

For the best experience, we recommend using a virtual environment:

```bash
# Create a virtual environment
python -m venv dbp-env

# Activate the virtual environment
# On Windows:
dbp-env\Scripts\activate
# On macOS/Linux:
source dbp-env/bin/activate

# Install dbp-cli
pip install dbp-cli

# Now you can use the CLI
dbp-click --help
```

## Troubleshooting

If you encounter issues:

1. Ensure you have the correct Python version (3.8+)
2. Check if all dependencies are installed correctly
3. Verify your configuration file is valid
4. Try running with `--debug` flag for more detailed error information
5. If using the new CLI command, consult the [Migration Guide](MIGRATION_GUIDE.md) for common issues

For additional assistance, please refer to the project documentation or open an issue on the project repository.
