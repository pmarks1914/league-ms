"""migration 005

Revision ID: 9e7fb23d6d3a
Revises: 98ba80ba0343
Create Date: 2024-05-17 00:12:13.699621

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '9e7fb23d6d3a'
down_revision = '98ba80ba0343'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('file', schema=None) as batch_op:
        batch_op.drop_column('created_on')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('file', schema=None) as batch_op:
        batch_op.add_column(sa.Column('created_on', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))

    # ### end Alembic commands ###