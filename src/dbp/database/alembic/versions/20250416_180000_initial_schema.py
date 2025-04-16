"""Initial schema

Revision ID: 20250416_180000
Revises: 
Create Date: 2025-04-16 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250416_180000'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    [Function intent]
    Creates the initial database schema based on all models defined in models.py.
    
    [Implementation details]
    Uses Alembic operations to create tables in the correct order,
    ensuring foreign key references are valid.
    
    [Design principles]
    Creates a complete baseline schema as the starting point for all future migrations.
    """
    # Create projects table
    op.create_table('projects',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('root_path', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('root_path')
    )
    
    # Create documents table
    op.create_table('documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('path', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('last_modified', sa.DateTime(), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('md5_digest', sa.String(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('intent', sa.Text(), nullable=True),
        sa.Column('design_principles', sa.Text(), nullable=True),
        sa.Column('constraints', sa.Text(), nullable=True),
        sa.Column('reference_documentation', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('path')
    )
    
    # Create document_relationships table
    op.create_table('document_relationships',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('target_id', sa.Integer(), nullable=False),
        sa.Column('relationship_type', sa.String(), nullable=False),
        sa.Column('topic', sa.String(), nullable=False),
        sa.Column('scope', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['source_id'], ['documents.id'], ),
        sa.ForeignKeyConstraint(['target_id'], ['documents.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create functions table
    op.create_table('functions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('intent', sa.Text(), nullable=True),
        sa.Column('design_principles', sa.Text(), nullable=True),
        sa.Column('implementation_details', sa.Text(), nullable=True),
        sa.Column('design_decisions', sa.Text(), nullable=True),
        sa.Column('parameters', sa.Text(), nullable=True),
        sa.Column('start_line', sa.Integer(), nullable=True),
        sa.Column('end_line', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create classes table
    op.create_table('classes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('intent', sa.Text(), nullable=True),
        sa.Column('design_principles', sa.Text(), nullable=True),
        sa.Column('implementation_details', sa.Text(), nullable=True),
        sa.Column('design_decisions', sa.Text(), nullable=True),
        sa.Column('start_line', sa.Integer(), nullable=True),
        sa.Column('end_line', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create design_decisions table
    op.create_table('design_decisions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('rationale', sa.Text(), nullable=True),
        sa.Column('alternatives', sa.Text(), nullable=True),
        sa.Column('decision_date', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create change_records table
    op.create_table('change_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('summary', sa.String(), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create inconsistencies table
    op.create_table('inconsistencies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('severity', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('suggested_resolution', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create recommendations table
    op.create_table('recommendations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('creation_timestamp', sa.DateTime(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('developer_feedback', sa.Text(), nullable=True),
        sa.Column('last_codebase_change_timestamp', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create suggested_changes table
    op.create_table('suggested_changes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('recommendation_id', sa.Integer(), nullable=True),
        sa.Column('document_id', sa.Integer(), nullable=True),
        sa.Column('change_type', sa.String(), nullable=False),
        sa.Column('location', sa.String(), nullable=False),
        sa.Column('before_text', sa.Text(), nullable=True),
        sa.Column('after_text', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
        sa.ForeignKeyConstraint(['recommendation_id'], ['recommendations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create developer_decisions table
    op.create_table('developer_decisions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('recommendation_id', sa.Integer(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('decision', sa.String(), nullable=False),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.Column('implementation_timestamp', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['recommendation_id'], ['recommendations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create schema_version table
    op.create_table('schema_version',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('version', sa.String(), nullable=False),
        sa.Column('applied_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create doc_relationships table
    op.create_table('doc_relationships',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_document', sa.String(), nullable=False),
        sa.Column('target_document', sa.String(), nullable=False),
        sa.Column('relationship_type', sa.String(), nullable=False),
        sa.Column('topic', sa.String(), nullable=True),
        sa.Column('scope', sa.String(), nullable=True),
        sa.Column('meta_data', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_doc_relationships_relationship_type'), 'doc_relationships', ['relationship_type'], unique=False)
    op.create_index(op.f('ix_doc_relationships_source_document'), 'doc_relationships', ['source_document'], unique=False)
    op.create_index(op.f('ix_doc_relationships_target_document'), 'doc_relationships', ['target_document'], unique=False)
    
    # Create inconsistency_records table
    op.create_table('inconsistency_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_file', sa.String(), nullable=False),
        sa.Column('target_file', sa.String(), nullable=True),
        sa.Column('inconsistency_type', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('severity', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('detected_at', sa.DateTime(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('meta_data', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_inconsistency_records_inconsistency_type'), 'inconsistency_records', ['inconsistency_type'], unique=False)
    op.create_index(op.f('ix_inconsistency_records_severity'), 'inconsistency_records', ['severity'], unique=False)
    op.create_index(op.f('ix_inconsistency_records_source_file'), 'inconsistency_records', ['source_file'], unique=False)
    op.create_index(op.f('ix_inconsistency_records_status'), 'inconsistency_records', ['status'], unique=False)
    op.create_index(op.f('ix_inconsistency_records_target_file'), 'inconsistency_records', ['target_file'], unique=False)
    
    # Create recommendation_records table
    op.create_table('recommendation_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('strategy_name', sa.String(), nullable=False),
        sa.Column('fix_type', sa.String(), nullable=False),
        sa.Column('severity', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('inconsistency_ids', sa.Text(), nullable=False),
        sa.Column('source_file', sa.String(), nullable=True),
        sa.Column('target_file', sa.String(), nullable=True),
        sa.Column('code_snippet', sa.Text(), nullable=True),
        sa.Column('doc_snippet', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('applied_at', sa.DateTime(), nullable=True),
        sa.Column('meta_data', sa.Text(), nullable=True),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_recommendation_records_severity'), 'recommendation_records', ['severity'], unique=False)
    op.create_index(op.f('ix_recommendation_records_source_file'), 'recommendation_records', ['source_file'], unique=False)
    op.create_index(op.f('ix_recommendation_records_status'), 'recommendation_records', ['status'], unique=False)
    op.create_index(op.f('ix_recommendation_records_strategy_name'), 'recommendation_records', ['strategy_name'], unique=False)
    op.create_index(op.f('ix_recommendation_records_target_file'), 'recommendation_records', ['target_file'], unique=False)
    
    # Create association tables
    op.create_table('inconsistency_documents',
        sa.Column('inconsistency_id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
        sa.ForeignKeyConstraint(['inconsistency_id'], ['inconsistencies.id'], ),
        sa.PrimaryKeyConstraint('inconsistency_id', 'document_id')
    )
    
    op.create_table('recommendation_inconsistencies',
        sa.Column('recommendation_id', sa.Integer(), nullable=False),
        sa.Column('inconsistency_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['inconsistency_id'], ['inconsistencies.id'], ),
        sa.ForeignKeyConstraint(['recommendation_id'], ['recommendations.id'], ),
        sa.PrimaryKeyConstraint('recommendation_id', 'inconsistency_id')
    )


def downgrade() -> None:
    """
    [Function intent]
    Removes the entire database schema created in the upgrade function.
    
    [Implementation details]
    Drops all tables in the reverse order of their creation to avoid
    foreign key constraint violations.
    
    [Design principles]
    Completely removes all tables and returns the database to an empty state.
    """
    # Drop association tables first to avoid foreign key constraints
    op.drop_table('recommendation_inconsistencies')
    op.drop_table('inconsistency_documents')
    
    # Drop tables with foreign keys to other tables
    op.drop_index(op.f('ix_recommendation_records_target_file'), table_name='recommendation_records')
    op.drop_index(op.f('ix_recommendation_records_strategy_name'), table_name='recommendation_records')
    op.drop_index(op.f('ix_recommendation_records_status'), table_name='recommendation_records')
    op.drop_index(op.f('ix_recommendation_records_source_file'), table_name='recommendation_records')
    op.drop_index(op.f('ix_recommendation_records_severity'), table_name='recommendation_records')
    op.drop_table('recommendation_records')
    
    op.drop_index(op.f('ix_inconsistency_records_target_file'), table_name='inconsistency_records')
    op.drop_index(op.f('ix_inconsistency_records_status'), table_name='inconsistency_records')
    op.drop_index(op.f('ix_inconsistency_records_source_file'), table_name='inconsistency_records')
    op.drop_index(op.f('ix_inconsistency_records_severity'), table_name='inconsistency_records')
    op.drop_index(op.f('ix_inconsistency_records_inconsistency_type'), table_name='inconsistency_records')
    op.drop_table('inconsistency_records')
    
    op.drop_index(op.f('ix_doc_relationships_target_document'), table_name='doc_relationships')
    op.drop_index(op.f('ix_doc_relationships_source_document'), table_name='doc_relationships')
    op.drop_index(op.f('ix_doc_relationships_relationship_type'), table_name='doc_relationships')
    op.drop_table('doc_relationships')
    
    op.drop_table('schema_version')
    op.drop_table('developer_decisions')
    op.drop_table('suggested_changes')
    op.drop_table('recommendations')
    op.drop_table('inconsistencies')
    op.drop_table('change_records')
    op.drop_table('design_decisions')
    op.drop_table('classes')
    op.drop_table('functions')
    op.drop_table('document_relationships')
    op.drop_table('documents')
    op.drop_table('projects')
