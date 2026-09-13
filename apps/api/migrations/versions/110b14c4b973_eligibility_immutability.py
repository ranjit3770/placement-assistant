"""eligibility immutability

Revision ID: 110b14c4b973
Revises: 7647b3ca528a
"""
from alembic import op
import sqlalchemy as sa


revision = '110b14c4b973'
down_revision = '7647b3ca528a'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_decision_update_delete()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'Eligibility decisions are immutable historical records';
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER ensure_decision_immutability
        BEFORE UPDATE OR DELETE ON eligibility_decisions
        FOR EACH ROW EXECUTE FUNCTION prevent_decision_update_delete();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS ensure_decision_immutability ON eligibility_decisions;")
    op.execute("DROP FUNCTION IF EXISTS prevent_decision_update_delete();")
