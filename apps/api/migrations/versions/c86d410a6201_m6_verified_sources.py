"""M6 immutable verified source metadata; no M1-M5 table alterations.

Revision ID: c86d410a6201
Revises: 110b14c4b973
"""

import sqlalchemy as sa
from alembic import op

revision = "c86d410a6201"
down_revision = "110b14c4b973"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rag_source_objects",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("institution_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("object_key", sa.String(130), nullable=False),
        sa.Column("byte_length", sa.Integer(), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column(
            "request_id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("source_type", sa.String(24), nullable=False),
        sa.Column("source_reference", sa.String(500), nullable=False),
        sa.Column("verification", sa.String(20), server_default="UNVERIFIED", nullable=False),
        sa.Column("correction_reason", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("institution_id", "id"),
        sa.UniqueConstraint("institution_id", "document_id"),
        sa.UniqueConstraint("object_key"),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["institution_id", "document_id"],
            ["policy_documents.institution_id", "policy_documents.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id", "actor_id"],
            ["users.institution_id", "users.id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("byte_length > 0 AND byte_length <= 10485760", name="source_size"),
        sa.CheckConstraint("source_hash ~ '^[0-9a-f]{64}$'", name="source_hash"),
        sa.CheckConstraint(
            "object_key = replace(institution_id::text, '-', '') || '-' || "
            "replace(document_id::text, '-', '') || '-' || source_hash",
            name="source_key",
        ),
        sa.CheckConstraint(
            "source_type IN ('INSTITUTION','IMPORT','DOCUMENT','STUDENT','SYSTEM')",
            name="source_type_values",
        ),
        sa.CheckConstraint(
            "verification IN ('VERIFIED','SELF_DECLARED','UNVERIFIED')", name="verification_values"
        ),
        sa.CheckConstraint("length(source_reference) > 0", name="source_present"),
    )
    op.create_index(
        "ix_rag_source_objects_institution_id", "rag_source_objects", ["institution_id"]
    )
    op.execute("""
        CREATE FUNCTION rag_guard_source_object() RETURNS trigger AS $$
        DECLARE original_hash text;
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                RAISE EXCEPTION 'Immutable RAG source metadata';
            END IF;
            SELECT content_hash INTO original_hash FROM policy_documents
            WHERE institution_id = NEW.institution_id AND id = NEW.document_id FOR SHARE;
            IF original_hash IS NULL OR original_hash <> NEW.source_hash THEN
                RAISE EXCEPTION 'RAG source must match tenant document hash';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER rag_source_integrity
        BEFORE INSERT OR UPDATE OR DELETE ON rag_source_objects
        FOR EACH ROW EXECUTE FUNCTION rag_guard_source_object();
    """)


def downgrade() -> None:
    op.drop_table("rag_source_objects")
    op.execute("DROP FUNCTION rag_guard_source_object()")
