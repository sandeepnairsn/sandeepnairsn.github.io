"""
Exercise 4, Step 1 -- gates.py

Programmatic gates that check a TicketContext's preconditions before
the coordinator is allowed to call the next subagent. A gate is a hard
stop enforced by the runtime -- unlike a prompt rule, the model can't
talk its way past it.
"""


class PipelineGateError(Exception):
    """Raised when a pipeline precondition is not met."""
    pass


def gate_classification(ctx) -> None:
    """Raise PipelineGateError unless classification is fully populated."""
    if ctx.classification_complete():
        return

    missing = [
        name
        for name, value in (
            ("product_area", ctx.product_area),
            ("severity", ctx.severity),
            ("intent", ctx.intent),
        )
        if value is None
    ]
    raise PipelineGateError(
        f"Gate 1 (classification) failed: missing field(s) {missing}. "
        "Rerun the Classifier before proceeding to CRM Enrichment."
    )


def gate_enrichment(ctx) -> None:
    """Raise PipelineGateError unless account_tier and sla_tier are populated."""
    if ctx.enrichment_complete():
        return

    missing = [
        name
        for name, value in (
            ("account_tier", ctx.account_tier),
            ("sla_tier", ctx.sla_tier),
        )
        if value is None
    ]
    raise PipelineGateError(
        f"Gate 2 (enrichment) failed: {missing} is None. "
        "Rerun the CRM Enricher before proceeding to Drafting."
    )


def gate_draft(ctx) -> None:
    """Raise PipelineGateError unless draft_response has been written."""
    if ctx.draft_complete():
        return

    raise PipelineGateError(
        "Gate 3 (draft) failed: draft_response is None. "
        "Rerun the Drafter before proceeding to Validation."
    )
