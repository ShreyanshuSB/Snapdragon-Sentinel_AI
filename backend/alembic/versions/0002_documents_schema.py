"""documents_schema

Revision ID: 0002_documents_schema
Revises: 0001_initial_schema
Create Date: 2026-09-29 03:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002_documents_schema'
down_revision: Union[str, Sequence[str], None] = '0001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.String(length=64), nullable=False),
        sa.Column('file_id', sa.String(length=64), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('mime_type', sa.String(length=100), nullable=False, server_default='application/octet-stream'),
        sa.Column('source_type', sa.String(length=50), nullable=False, server_default='document'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='READY'),
        sa.Column('page_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('ocr_pages_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('extracted_text', sa.Text(), nullable=False, server_default=''),
        sa.Column('extraction_method', sa.String(length=100), nullable=False, server_default='direct'),
        sa.Column('processing_time_ms', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_documents_id'), 'documents', ['id'], unique=False)
    op.create_index(op.f('ix_documents_document_id'), 'documents', ['document_id'], unique=True)
    op.create_index(op.f('ix_documents_file_id'), 'documents', ['file_id'], unique=False)

    op.create_table(
        'document_pages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.String(length=64), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('width', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('height', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('text', sa.Text(), nullable=False, server_default=''),
        sa.Column('has_ocr', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('regions', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('processing_time_ms', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.document_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_document_pages_id'), 'document_pages', ['id'], unique=False)
    op.create_index(op.f('ix_document_pages_document_id'), 'document_pages', ['document_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_document_pages_document_id'), table_name='document_pages')
    op.drop_index(op.f('ix_document_pages_id'), table_name='document_pages')
    op.drop_table('document_pages')

    op.drop_index(op.f('ix_documents_file_id'), table_name='documents')
    op.drop_index(op.f('ix_documents_document_id'), table_name='documents')
    op.drop_index(op.f('ix_documents_id'), table_name='documents')
    op.drop_table('documents')
