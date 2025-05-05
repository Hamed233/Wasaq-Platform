"""Add contact information fields to Land model

Revision ID: add_contact_info_fields
Revises: a5f37eae079a
Create Date: 2025-05-05 15:11:13.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_contact_info_fields'
down_revision = 'a5f37eae079a'
branch_labels = None
depends_on = None


def upgrade():
    # Add contact information fields to the lands table
    op.add_column('lands', sa.Column('contact_name', sa.String(length=100), nullable=True))
    op.add_column('lands', sa.Column('contact_phone', sa.String(length=20), nullable=True))
    op.add_column('lands', sa.Column('contact_email', sa.String(length=100), nullable=True))
    op.add_column('lands', sa.Column('contact_position', sa.String(length=100), nullable=True))
    op.add_column('lands', sa.Column('contact_notes', sa.Text(), nullable=True))


def downgrade():
    # Remove contact information fields from the lands table
    op.drop_column('lands', 'contact_notes')
    op.drop_column('lands', 'contact_position')
    op.drop_column('lands', 'contact_email')
    op.drop_column('lands', 'contact_phone')
    op.drop_column('lands', 'contact_name')
