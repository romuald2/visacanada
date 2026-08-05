"""add complaints table for PIPEDA compliance

Revision ID: 018_complaints
Revises: 017_create_deadlines
Create Date: 2026-08-05

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '018_complaints'
down_revision = '017_create_deadlines'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'complaints',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='nouveau'),
        sa.Column('admin_response', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=False), nullable=False, server_default=sa.text('now()')),
        sa.Column('resolved_at', sa.DateTime(timezone=False), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_complaints_id'), 'complaints', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_complaints_id'), table_name='complaints')
    op.drop_table('complaints')
