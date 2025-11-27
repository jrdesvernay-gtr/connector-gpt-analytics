"""add updated_at to ga_connections

Revision ID: cd5b1b244029
Revises: aba5f5d04d4a
Create Date: 2025-01-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'cd5b1b244029'
down_revision: Union[str, None] = 'aba5f5d04d4a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add updated_at column - first add as nullable, then update existing rows, then make it non-nullable
    op.add_column('ga_connections', 
        sa.Column('updated_at', sa.DateTime(), nullable=True))
    
    # Update existing rows to set updated_at = created_at
    op.execute("UPDATE ga_connections SET updated_at = created_at WHERE updated_at IS NULL")
    
    # Now make it non-nullable
    op.alter_column('ga_connections', 'updated_at', nullable=False)


def downgrade() -> None:
    op.drop_column('ga_connections', 'updated_at')
