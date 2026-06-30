"""
Exercise 4, Step 2 -- coordinator_v3.py

Same pipeline as coordinator_v2.py, with a programmatic gate enforced
before each step that depends on the previous one's output. If a gate
fails, PipelineGateError stops the pipeline immediately with a named,
informative error -- instead of letting a later step run on incomplete
data.

Run with:
    python3 coordinator_v3.py
"""

from context import TicketContext
from gates import PipelineGateError, gate_classification, gate_enrichment, gate_draft
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

    try:
        # --- Step 1: Classify -------------------------------------------------
        classification = run_classifier(ctx.raw_ticket)
        ctx.product_area = classification["product_area"]
        ctx.severity = classification["severity"]
        ctx.intent = classification["intent"]
        print("[Classifier]", classification)

        gate_classification(ctx)
        print("Gate 1 passed: classification complete.")

        # --- Step 2: Enrich ----------------------------------------------------
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

        gate_enrichment(ctx)
        print("Gate 2 passed: enrichment complete.")

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

        gate_draft(ctx)
        print("Gate 3 passed: draft complete.")

        # --- Step 4: Validate ------------------------------------------------------
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

    except PipelineGateError as exc:
        print(f"[PIPELINE BLOCKED] {exc}")


if __name__ == "__main__":
    main()
