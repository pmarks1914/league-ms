"""migration 001

Revision ID: eb4e488f8f6a
Revises: 0b26cc8efc7e
Create Date: 2024-08-04 16:20:18.258108

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'eb4e488f8f6a'
down_revision = '0b26cc8efc7e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('file', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_official', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('issued_date', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('slug', sa.String(length=80), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('file', schema=None) as batch_op:
        batch_op.drop_column('slug')
        batch_op.drop_column('issued_date')
        batch_op.drop_column('is_official')

    # ### end Alembic commands ###
