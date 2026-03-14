"""Initial schema for the enterprise RAG chatbot MVP."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = "20260314_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "sessions",
        sa.Column("session_id", sa.String(length=64), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "documents",
        sa.Column("doc_id", sa.String(length=128), primary_key=True),
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.Column("doc_type", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "request_logs",
        sa.Column("request_id", sa.String(length=64), primary_key=True),
        sa.Column("session_id", sa.String(length=64), sa.ForeignKey("sessions.session_id"), nullable=False),
        sa.Column("route", sa.String(length=32), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("input_risk_level", sa.String(length=16), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "chunks",
        sa.Column("chunk_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("doc_id", sa.String(length=128), sa.ForeignKey("documents.doc_id", ondelete="CASCADE"), nullable=False),
        sa.Column("section", sa.String(length=255), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("session_id", sa.String(length=64), sa.ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("route", sa.String(length=32), nullable=True),
        sa.Column("citations", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "retrieval_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("request_id", sa.String(length=64), sa.ForeignKey("request_logs.request_id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", sa.String(length=64), sa.ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("retrieved_chunk_ids", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("scores", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("route", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "feedback",
        sa.Column("request_id", sa.String(length=64), sa.ForeignKey("request_logs.request_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("rating", sa.String(length=16), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_index("ix_messages_session_timestamp", "messages", ["session_id", "timestamp"])
    op.create_index("ix_request_logs_session_id", "request_logs", ["session_id"])
    op.create_index("ix_retrieval_logs_session_id", "retrieval_logs", ["session_id"])
    op.create_index("ix_chunks_doc_id_chunk_index", "chunks", ["doc_id", "chunk_index"])


def downgrade() -> None:
    op.drop_index("ix_chunks_doc_id_chunk_index", table_name="chunks")
    op.drop_index("ix_retrieval_logs_session_id", table_name="retrieval_logs")
    op.drop_index("ix_request_logs_session_id", table_name="request_logs")
    op.drop_index("ix_messages_session_timestamp", table_name="messages")
    op.drop_table("feedback")
    op.drop_table("retrieval_logs")
    op.drop_table("messages")
    op.drop_table("chunks")
    op.drop_table("request_logs")
    op.drop_table("documents")
    op.drop_table("sessions")

