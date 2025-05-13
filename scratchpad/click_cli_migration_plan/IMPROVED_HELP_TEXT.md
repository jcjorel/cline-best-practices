# Improved Help Text Documentation

This document shows examples of the improved help text in the new Click-based CLI compared to the original legacy CLI.

## Main CLI Help Comparison

### Legacy CLI Help (`dbp --help`)

```
usage: dbp [-h] [--version] [--config FILE] [--server URL] [--api-key KEY] [--verbose] [--quiet]
           [--output {text,json,markdown,html}] [--no-color] [--no-progress] [--debug]
           {query,commit,config,status,server,test,modeldiscovery,hstc,hstc_agno} ...

Documentation-Based Programming CLI

optional arguments:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  --config FILE         Path to configuration file
  --server URL          MCP server URL
  --api-key KEY         API key for authentication
  --verbose, -v         Increase verbosity level
  --quiet, -q           Suppress all non-error output
  --output {text,json,markdown,html}, -o {text,json,markdown,html}
                        Output format
  --no-color            Disable colored output
  --no-progress         Disable progress indicators
  --debug               Enable debug mode with stack traces on errors

Commands:
  {query,commit,config,status,server,test,modeldiscovery,hstc,hstc_agno}
                        Command to execute
```

### New CLI Help (`dbp-click --help`)

```
Usage: dbp-click [OPTIONS] COMMAND [ARGS]...

  Documentation-Based Programming CLI

Options:
  -c, --config FILE  Path to configuration file  [env var: DBP_CLI_CONFIG]
  --server URL       MCP server URL  [env var: DBP_CLI_SERVER]
  --api-key KEY      API key for authentication  [env var: DBP_CLI_API_KEY]
  -v, --verbose      Increase verbosity level
  -q, --quiet        Suppress non-error output
  -o, --output TEXT  Output format (text, json, markdown, html)
                     [default: text]
  --no-color         Disable colored output
  --no-progress      Disable progress indicators
  --debug            Enable debug mode
  --version          Show the version and exit.
  -h, --help         Show this message and exit.

Commands:
  commit     Generate commit messages from git changes
  config     Manage configuration settings
  hstc_agno  HSTC implementation with Agno framework
  query      Execute queries against Bedrock models
  status     Check system status and connection
  version    Display version information
```

### Key Improvements

1. **Cleaner Layout**: Better organization with clear separation of options and commands
2. **Default Values**: Showing default values for options like `--output`
3. **Environment Variables**: Indicating which environment variables can be used instead of options
4. **Short Options**: Clearly showing short options like `-v` alongside long options
5. **Command Descriptions**: Descriptive text for each command showing its purpose
6. **Color Highlighting**: Better color-coding of different sections (not visible in this document)

## Command-Specific Help Comparison

### Legacy Query Command Help (`dbp query --help`)

```
usage: dbp query [-h] [--budget BUDGET] [--timeout TIMEOUT] [--stream] [--format {text,json,markdown,html}] query

positional arguments:
  query                 Query to send to the model

optional arguments:
  -h, --help            show this help message and exit
  --budget BUDGET       Maximum budget for the query in dollars
  --timeout TIMEOUT     Maximum time to wait for response in seconds
  --stream              Stream the response as it's generated
  --format {text,json,markdown,html}, -f {text,json,markdown,html}
                        Output format
```

### New Query Command Help (`dbp-click query --help`)

```
Usage: dbp-click query [OPTIONS] QUERY_TEXT

  Execute queries against Bedrock models

  Send natural language queries to Bedrock models and get AI-generated
  responses. Supports various output formats and streaming options.

  Examples:
    dbp-click query "How do I optimize S3 bucket performance?"
    dbp-click query "Generate TypeScript interface for User model" --format json
    dbp-click query "Help me debug this code" --stream --budget 0.5

Arguments:
  QUERY_TEXT  Query text to send to the model  [required]

Options:
  --budget FLOAT         Maximum budget in dollars  [default: 0.1]
  --timeout INTEGER      Maximum wait time in seconds  [default: 60]
  --stream / --no-stream  Stream the response as it's generated
                         [default: no-stream]
  -f, --format [text|json|markdown|html]
                         Output format  [default: text]
  -h, --help             Show this message and exit.
```

### Key Improvements in Command Help

1. **Command Description**: Detailed description of what the command does
2. **Examples**: Concrete usage examples showing common scenarios
3. **Required Arguments**: Clear indication of required vs. optional arguments
4. **Default Values**: Default values shown for all options
5. **Argument Descriptions**: More descriptive text for each argument
6. **Toggle Options**: Clear indication of toggle options like `--stream/--no-stream`
7. **Hierarchical Display**: Better visual hierarchy for improved readability

## Config Command Help Comparison

### Legacy Config Command Help (`dbp config --help`)

```
usage: dbp config [-h] {get,set,unset,list} ...

optional arguments:
  -h, --help            show this help message and exit

Commands:
  {get,set,unset,list}
```

### New Config Command Help (`dbp-click config --help`)

```
Usage: dbp-click config [OPTIONS] COMMAND [ARGS]...

  Manage configuration settings

  View and modify configuration settings for the CLI and its components.
  Changes are saved to the configuration file and persist between sessions.

Commands:
  get    Get a configuration value
  list   List all configuration values
  set    Set a configuration value
  unset  Remove a configuration value

Options:
  -h, --help  Show this message and exit.
```

These improved help texts make the CLI more user-friendly and easier to understand, especially for new users.
