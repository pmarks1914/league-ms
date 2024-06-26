"""migration 004

Revision ID: 19161c7616c3
Revises: c8b51d8ae080
Create Date: 2024-05-16 23:57:10.930932

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '19161c7616c3'
down_revision = 'c8b51d8ae080'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('file', schema=None) as batch_op:
        batch_op.drop_constraint('file_user_id_fkey', type_='foreignkey')
        batch_op.drop_column('user_id')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('file', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.VARCHAR(length=36), autoincrement=False, nullable=True))
        batch_op.create_foreign_key('file_user_id_fkey', 'user', ['user_id'], ['id'])

    # ### end Alembic commands ###
