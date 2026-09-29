"""semantic_memory_schema

Revision ID: 0003_semantic_memory_schema
Revises: 0002_documents_schema
Create Date: 2026-09-29 03:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0003_semantic_memory_schema'
down_revision: Union[str, Sequence[str], None] = '0002_documents_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add vector and source tracking columns to memories
    with op.batch_alter_table('memories') as batch_op:
        batch_op.add_column(sa.Column('summary', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('source_id', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('importance', sa.Integer(), nullable=False, server_default='1'))
        batch_op.add_column(sa.Column('embedding', sa.LargeBinary(), nullable=True))
        batch_op.add_column(sa.Column('embedding_status', sa.String(length=20), nullable=False, server_default='PENDING'))
        batch_op.add_column(sa.Column('embedding_model', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('embedding_model_version', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('embedding_dimension', sa.Integer(), nullable=True))
        batch_op.create_index('ix_memories_embedding_status', ['embedding_status'], unique=False)
        batch_op.create_index('ix_memories_source_type', ['source_type'], unique=False)

    # 2. Create document_chunks table for searchable source material
    op.create_table(
        'document_chunks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.String(length=64), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('chunk_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('text_content', sa.Text(), nullable=False),
        sa.Column('embedding', sa.LargeBinary(), nullable=True),
        sa.Column('embedding_model', sa.String(length=100), nullable=True),
        sa.Column('embedding_model_version', sa.String(length=50), nullable=True),
        sa.Column('embedding_dimension', sa.Integer(), nullable=True),
        sa.Column('start_char', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('end_char', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.document_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_document_chunks_id'), 'document_chunks', ['id'], unique=False)
    op.create_index(op.f('ix_document_chunks_document_id'), 'document_chunks', ['document_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_document_chunks_document_id'), table_name='document_chunks')
    op.drop_index(op.f('ix_document_chunks_id'), table_name='document_chunks')
    op.drop_table('document_chunks')

    with op.batch_alter_table('memories') as batch_op:
        batch_op.drop_index('ix_memories_source_type')
        batch_op.drop_index('ix_memories_embedding_status')
        batch_op.drop_column('embedding_dimension')
        batch_op.drop_column('embedding_model_version')
        batch_op.drop_column('embedding_model')
        batch_op.drop_column('embedding_status')
        batch_op.drop_column('embedding')
        batch_op.drop_column('importance')
        batch_op.drop_column('source_id')
        batch_op.drop_column('summary')
