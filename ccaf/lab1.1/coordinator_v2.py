"""
Exercise 3, Step 2 -- coordinator_v2.py

Same four-step pipeline as coordinator.py, refactored to carry state in
a single TicketContext object instead of loose variables. Each
subagent still only receives the specific fields it needs -- never the
whole ctx object -- which keeps the memory-isolation property from
Exercise 2 intact while making the pipeline's state explicit and
self-documenting.

Run with:
    python3 coordinator_v2.py
"""

from context import TicketContext
from subagents import run_classifier, run_crm_enricher, run_drafter, run_validator

TICKET_TEXT = """\
From: sarah.chen@globalcorp.com
Subject: Cannot access SSO login -- entire team locked out

Our team of 40 has been unable to log in via SSO since 09:00 this
morning. We have a client demo in 3 hours. This is completely blocking
us.
"""


def main():
    ctx = TicketContext(
        ticket_id="T-1001",
        raw_ticket=TICKET_TEXT,
        customer_email="sarah.chen@globalcorp.com",
    )

    # --- Step 1: Classify ---------------------------------------------------
    classification = run_classifier(ctx.raw_ticket)
    ctx.product_area = classification["product_area"]
    ctx.severity = classification["severity"]
    ctx.intent = classification["intent"]
    print("[Classifier]", classification)

    # --- Step 2: Enrich ------------------------------------------------------
    # Pass only the fields the enricher needs -- not ctx itself.
    classification_for_crm = {
        "product_area": ctx.product_area,
        "severity": ctx.severity,
        "intent": ctx.intent,
    }
    crm = run_crm_enricher(ctx.customer_email, classification_for_crm)
    ctx.account_tier = crm["account_tier"]
    ctx.sla_tier = crm["sla_tier"]
    ctx.account_manager = crm["account_manager"]
    print("[CRM Enricher]", crm)

    # --- Step 3: Draft -------------------------------------------------------
    classification_for_draft = {
        "product_area": ctx.product_area,
        "severity": ctx.severity,
        "intent": ctx.intent,
    }
    crm_for_draft = {
        "account_tier": ctx.account_tier,
        "sla_tier": ctx.sla_tier,
        "account_manager": ctx.account_manager,
    }
    draft = run_drafter(ctx.raw_ticket, classification_for_draft, crm_for_draft)
    ctx.draft_response = draft
    print("[Drafter]\n", draft)

    # --- Step 4: Validate -----------------------------------------------------
    classification_for_validation = {
        "product_area": ctx.product_area,
        "severity": ctx.severity,
        "intent": ctx.intent,
    }
    crm_for_validation = {
        "account_tier": ctx.account_tier,
        "sla_tier": ctx.sla_tier,
    }
    validation = run_validator(
        ctx.draft_response, classification_for_validation, crm_for_validation
    )
    ctx.validation_result = validation
    print("[Validator]", validation)

    print("\nFinal context (all fields should be populated):")
    print(ctx)


if __name__ == "__main__":
    main()
