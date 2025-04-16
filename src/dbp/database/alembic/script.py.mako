"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    """
    [Function intent]
    Implements the schema changes for upgrading to this version.
    
    [Implementation details]
    Uses Alembic operations to create, alter, or drop database objects
    in a specific sequence to ensure data integrity during the upgrade.
    
    [Design principles]
    Changes are idempotent and reversible where possible.
    """
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """
    [Function intent]
    Implements the schema changes for downgrading from this version.
    
    [Implementation details]
    Uses Alembic operations to reverse the changes made in the upgrade
    function, restoring the previous database schema.
    
    [Design principles]
    Changes are applied in reverse order of the upgrade to ensure
    proper schema state is maintained during rollback.
    """
    ${downgrades if downgrades else "pass"}
