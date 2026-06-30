"""
Exercise 3, Step 1 -- context.py

TicketContext is a typed dataclass that carries all pipeline state
between subagents, replacing the raw dict/variable passing used in
coordinator.py. Constructing it with a missing required field raises a
TypeError immediately, at the Python level -- not silently inside a
Claude response.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class TicketContext:
    # --- Required at intake: no default, must be provided at construction ---
    ticket_id: str
    raw_ticket: str
    customer_email: str

    # --- Populated by Classifier ---
    product_area: Optional[str] = None
    severity: Optional[str] = None
    intent: Optional[str] = None

    # --- Populated by CRM Enricher ---
    account_tier: Optional[str] = None
    sla_tier: Optional[str] = None
    account_manager: Optional[str] = None

    # --- Populated by Drafter and Validator ---
    draft_response: Optional[str] = None
    validation_result: Optional[str] = None

    def classification_complete(self) -> bool:
        """True only if product_area, severity, and intent are all non-None."""
        return (
            self.product_area is not None
            and self.severity is not None
            and self.intent is not None
        )

    def enrichment_complete(self) -> bool:
        """True only if account_tier and sla_tier are both non-None."""
        return self.account_tier is not None and self.sla_tier is not None

    def draft_complete(self) -> bool:
        """True only if draft_response has been written."""
        return self.draft_response is not None


if __name__ == "__main__":
    # Quick check -- this should fail loudly with a TypeError, not silently.
    try:
        TicketContext()
    except TypeError as exc:
        print(f"Construction without required fields failed as expected:\n  {exc}")

    # This should succeed.
    ctx = TicketContext(
        ticket_id="T-1001",
        raw_ticket="Cannot access SSO login -- entire team locked out",
        customer_email="greennathan@example.com",
    )
    print("\nConstructed OK:")
    print(ctx)
    print("classification_complete:", ctx.classification_complete())
    print("enrichment_complete:", ctx.enrichment_complete())
    print("draft_complete:", ctx.draft_complete())
