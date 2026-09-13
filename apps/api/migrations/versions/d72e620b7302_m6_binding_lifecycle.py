"""Immutable M6 binding revisions and serialized lifecycle events.

Revision ID: d72e620b7302
Revises: c86d410a6201
"""

import sqlalchemy as sa
from alembic import op

revision = "d72e620b7302"
down_revision = "c86d410a6201"
branch_labels = None
depends_on = None


def tenant_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("institution_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column(
            "request_id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("source_type", sa.String(24), nullable=False),
        sa.Column("source_reference", sa.String(500), nullable=False),
        sa.Column("verification", sa.String(20), server_default="UNVERIFIED", nullable=False),
        sa.Column("correction_reason", sa.String(), nullable=True),
    ]


def tenant_constraints() -> list[sa.Constraint]:
    return [
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("institution_id", "id"),
        sa.UniqueConstraint("institution_id", "request_id"),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["institution_id", "actor_id"],
            ["users.institution_id", "users.id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "source_type IN ('INSTITUTION','IMPORT','DOCUMENT','STUDENT','SYSTEM')",
            name="source_type_values",
        ),
        sa.CheckConstraint(
            "verification IN ('VERIFIED','SELF_DECLARED','UNVERIFIED')", name="verification_values"
        ),
        sa.CheckConstraint("length(source_reference) > 0", name="source_present"),
    ]


def upgrade() -> None:
    op.create_table(
        "rag_policy_sources",
        *tenant_columns(),
        sa.Column("source_object_id", sa.Uuid(), nullable=False),
        sa.Column("policy_version_id", sa.Uuid(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("previous_revision_id", sa.Uuid(), nullable=True),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("proposal_reason", sa.String(1000), nullable=False),
        *tenant_constraints(),
        sa.ForeignKeyConstraint(
            ["institution_id", "source_object_id"],
            ["rag_source_objects.institution_id", "rag_source_objects.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id", "policy_version_id"],
            ["policy_versions.institution_id", "policy_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id", "previous_revision_id"],
            ["rag_policy_sources.institution_id", "rag_policy_sources.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("institution_id", "source_object_id", "policy_version_id", "revision"),
        sa.CheckConstraint("revision > 0", name="positive_revision"),
        sa.CheckConstraint("actor_id IS NOT NULL", name="binding_actor_required"),
        sa.CheckConstraint("source_hash ~ '^[0-9a-f]{64}$'", name="binding_hash"),
        sa.CheckConstraint("length(trim(proposal_reason)) > 0", name="proposal_reason_required"),
    )
    op.create_table(
        "rag_binding_events",
        *tenant_columns(),
        sa.Column("binding_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("reason", sa.String(1000), nullable=False),
        *tenant_constraints(),
        sa.ForeignKeyConstraint(
            ["institution_id", "binding_id"],
            ["rag_policy_sources.institution_id", "rag_policy_sources.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("institution_id", "binding_id", "sequence"),
        sa.CheckConstraint("status IN ('PROPOSED','APPROVED','REVOKED')", name="status_values"),
        sa.CheckConstraint(
            "(sequence = 1 AND status = 'PROPOSED') OR "
            "(sequence = 2 AND status = 'APPROVED') OR "
            "(sequence = 3 AND status = 'REVOKED')",
            name="event_sequence_state",
        ),
        sa.CheckConstraint("actor_id IS NOT NULL", name="event_actor_required"),
        sa.CheckConstraint("source_hash ~ '^[0-9a-f]{64}$'", name="event_hash"),
        sa.CheckConstraint("length(trim(reason)) > 0", name="event_reason_required"),
    )
    for table in ("rag_policy_sources", "rag_binding_events"):
        op.create_index(f"ix_{table}_institution_id", table, ["institution_id"])
    op.execute("""
        CREATE FUNCTION rag_guard_binding_revision() RETURNS trigger AS $$
        DECLARE source_row rag_source_objects%ROWTYPE;
                prior rag_policy_sources%ROWTYPE;
                prior_state text;
                original_hash text;
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                RAISE EXCEPTION 'Immutable RAG binding revision';
            END IF;
            SELECT * INTO source_row FROM rag_source_objects
              WHERE institution_id = NEW.institution_id AND id = NEW.source_object_id FOR UPDATE;
            IF NOT FOUND OR source_row.source_hash <> NEW.source_hash THEN
                RAISE EXCEPTION 'RAG binding source mismatch';
            END IF;
            SELECT content_hash INTO original_hash FROM policy_documents
              WHERE institution_id = NEW.institution_id AND id = source_row.document_id FOR SHARE;
            IF original_hash IS DISTINCT FROM NEW.source_hash THEN
                RAISE EXCEPTION 'RAG binding source mismatch';
            END IF;
            SELECT * INTO prior FROM rag_policy_sources
              WHERE institution_id = NEW.institution_id
                AND source_object_id = NEW.source_object_id
                AND policy_version_id = NEW.policy_version_id
              ORDER BY revision DESC LIMIT 1;
            IF FOUND THEN
                SELECT status INTO prior_state FROM rag_binding_events
                  WHERE institution_id = NEW.institution_id AND binding_id = prior.id
                  ORDER BY sequence DESC LIMIT 1;
                IF prior_state IS DISTINCT FROM 'REVOKED'
                  OR NEW.revision <> prior.revision + 1
                  OR NEW.previous_revision_id IS DISTINCT FROM prior.id THEN
                    RAISE EXCEPTION 'RAG binding revision requires revoked predecessor';
                END IF;
            ELSIF NEW.revision <> 1 OR NEW.previous_revision_id IS NOT NULL THEN
                RAISE EXCEPTION 'RAG binding must start at revision one';
            END IF;
            NEW.recorded_at := clock_timestamp();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE FUNCTION rag_guard_binding_event() RETURNS trigger AS $$
        DECLARE binding rag_policy_sources%ROWTYPE;
                last_sequence integer;
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                RAISE EXCEPTION 'Immutable RAG binding event';
            END IF;
            SELECT * INTO binding FROM rag_policy_sources
              WHERE institution_id = NEW.institution_id AND id = NEW.binding_id FOR UPDATE;
            IF NOT FOUND OR NEW.source_hash <> binding.source_hash THEN
                RAISE EXCEPTION 'RAG binding event source mismatch';
            END IF;
            SELECT COALESCE(MAX(sequence), 0) INTO last_sequence FROM rag_binding_events
              WHERE institution_id = NEW.institution_id AND binding_id = NEW.binding_id;
            IF NEW.sequence <> last_sequence + 1 OR NEW.sequence > 3 THEN
                RAISE EXCEPTION 'Invalid RAG binding transition';
            END IF;
            IF NEW.sequence = 1 AND (
                NEW.actor_id IS DISTINCT FROM binding.actor_id OR
                NEW.request_id IS DISTINCT FROM binding.request_id OR
                NEW.reason IS DISTINCT FROM binding.proposal_reason
            ) THEN
                RAISE EXCEPTION 'RAG proposal provenance mismatch';
            END IF;
            NEW.recorded_at := clock_timestamp();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE FUNCTION rag_initialize_binding() RETURNS trigger AS $$
        BEGIN
            INSERT INTO rag_binding_events
              (institution_id, binding_id, sequence, status, source_hash, reason,
               actor_id, request_id, source_type, source_reference, verification)
            VALUES
              (NEW.institution_id, NEW.id, 1, 'PROPOSED', NEW.source_hash, NEW.proposal_reason,
               NEW.actor_id, NEW.request_id, 'DOCUMENT', NEW.source_reference, 'VERIFIED');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER rag_binding_revision_guard
          BEFORE INSERT OR UPDATE OR DELETE ON rag_policy_sources
          FOR EACH ROW EXECUTE FUNCTION rag_guard_binding_revision();
        CREATE TRIGGER rag_binding_event_guard
          BEFORE INSERT OR UPDATE OR DELETE ON rag_binding_events
          FOR EACH ROW EXECUTE FUNCTION rag_guard_binding_event();
        CREATE TRIGGER rag_binding_initialize
          AFTER INSERT ON rag_policy_sources
          FOR EACH ROW EXECUTE FUNCTION rag_initialize_binding();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER rag_binding_initialize ON rag_policy_sources")
    op.drop_table("rag_binding_events")
    op.drop_table("rag_policy_sources")
    op.execute("DROP FUNCTION rag_initialize_binding()")
    op.execute("DROP FUNCTION rag_guard_binding_event()")
    op.execute("DROP FUNCTION rag_guard_binding_revision()")
