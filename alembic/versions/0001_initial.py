"""Initial operation tables.

Revision ID: 0001_initial
Revises:
Create Date: 2026-01-15
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "boats",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("owner", sa.String(length=128), nullable=False),
        sa.Column("licence_no", sa.String(length=64), nullable=False),
        sa.Column("district", sa.String(length=64), nullable=False),
        sa.Column("home_port", sa.String(length=64), nullable=False),
        sa.Column("crew_json", sa.Text(), nullable=False),
        sa.Column("gear", sa.String(length=64), nullable=False),
    )
    op.create_table(
        "operations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("boat_id", sa.String(length=64), sa.ForeignKey("boats.id"), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("opened_by", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "status in ('open', 'searching', 'found', 'closed')",
            name="ck_operations_status",
        ),
    )
    op.create_index("ix_operations_boat_id", "operations", ["boat_id"])
    op.create_table(
        "positions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("boat_id", sa.String(length=64), sa.ForeignKey("boats.id"), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lon", sa.Float(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_positions_boat_id", "positions", ["boat_id"])
    op.create_table(
        "sectors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("op_id", sa.Integer(), sa.ForeignKey("operations.id"), nullable=False),
        sa.Column("name", sa.String(length=32), nullable=False),
        sa.Column("polygon_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("assigned_boat", sa.String(length=128), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status in ('unassigned', 'assigned', 'searching', 'clear', 'found')",
            name="ck_sectors_status",
        ),
    )
    op.create_index("ix_sectors_op_id", "sectors", ["op_id"])
    op.create_table(
        "approvals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("op_id", sa.Integer(), sa.ForeignKey("operations.id"), nullable=False),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("requested_by_agent", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("approver", sa.String(length=64), nullable=True),
        sa.Column("approver_role", sa.String(length=64), nullable=True),
        sa.Column("message_id", sa.String(length=64), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status in ('pending', 'approved', 'rejected')",
            name="ck_approvals_status",
        ),
    )
    op.create_index("ix_approvals_op_id", "approvals", ["op_id"])
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("op_id", sa.Integer(), sa.ForeignKey("operations.id"), nullable=False),
        sa.Column("actor", sa.String(length=64), nullable=False),
        sa.Column("actor_type", sa.String(length=16), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("message_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_events_op_id", "events", ["op_id"])
    op.create_table(
        "evidence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("op_id", sa.Integer(), sa.ForeignKey("operations.id"), nullable=False),
        sa.Column("sector_id", sa.Integer(), sa.ForeignKey("sectors.id"), nullable=True),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("uri", sa.Text(), nullable=False),
        sa.Column("submitted_by", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("kind in ('photo', 'gps', 'note')", name="ck_evidence_kind"),
    )
    op.create_index("ix_evidence_op_id", "evidence", ["op_id"])


def downgrade() -> None:
    op.drop_table("evidence")
    op.drop_table("events")
    op.drop_table("approvals")
    op.drop_table("sectors")
    op.drop_table("positions")
    op.drop_table("operations")
    op.drop_table("boats")
