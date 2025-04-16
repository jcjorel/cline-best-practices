# Alembic Database Migrations

This directory contains the Alembic migrations for the Database-Based Programming system.

## Overview

Alembic is used to manage database schema creation and upgrades in a version-controlled manner. Each migration script represents a set of changes to the database schema, allowing for smooth upgrades and downgrades between versions.

## Directory Structure

```
alembic/
  ├── versions/       # Migration script files
  ├── env.py         # Environment configuration
  ├── script.py.mako # Template for migration scripts
  └── README.md      # This file
```

## Usage

### Running Migrations

To bring the database up to the latest version:

```bash
alembic upgrade head
```

### Creating a New Migration

To create a new migration after model changes:

```bash
alembic revision --autogenerate -m "Description of the changes"
```

This will automatically generate a migration script based on differences between the defined models and the current database schema.

### Downgrading

To rollback to a previous version:

```bash
alembic downgrade -1  # Go back one revision
alembic downgrade <revision_id>  # Go back to a specific revision
```

### Getting Migration Information

To see the current revision:

```bash
alembic current
```

To see migration history:

```bash
alembic history
```

## Best Practices

1. Always review auto-generated migrations before applying them
2. Test migrations on development environments before production
3. Include a meaningful description when creating new migrations
4. Make sure each migration is reversible (has a working downgrade function)
5. Keep migrations focused on specific schema changes
6. Version control all migration scripts along with application code

## Documentation

For more information about Alembic, refer to the [official Alembic documentation](https://alembic.sqlalchemy.org/).
