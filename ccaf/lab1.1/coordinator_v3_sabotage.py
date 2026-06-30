"""
Exercise 4, Step 3 -- coordinator_v3_sabotage.py

A deliberately broken copy of coordinator_v3.py. Immediately after the
Classifier writes its results into ctx -- and before Gate 1 runs -- we
null out ctx.severity. This proves that:
    1. PipelineGateError fires immediately at Gate 1, not later.
    2. The error message names "severity" as the missing field.
    3. Steps 2, 3, and 4 never execute.

Run with:
    python3 coordinator_v3_sabotage.py
"""

from context import TicketContext
from gates import PipelineGateError, gate_classification, gate_enrichment, gate_draft
from subagents import run_classifier, run_crm_enricher, run_drafter, run_validator

TICKET_TEXT = """\
From: greennathan@example.com
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

        # --- SABOTAGE: deliberately null out a required field ------------------
        ctx.severity = None
        print("[SABOTAGE] ctx.severity forcibly set to None before Gate 1.")

        gate_classification(ctx)
        print("Gate 1 passed: classification complete.")  # should never print

        # --- Step 2: Enrich (should never run) ----------------------------------
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

        # --- Step 3: Draft (should never run) -------------------------------------
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

        # --- Step 4: Validate (should never run) ------------------------------------
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

        print("\nFinal context:")
        print(ctx)

    except PipelineGateError as exc:
        print(f"[PIPELINE BLOCKED] {exc}")


if __name__ == "__main__":
    main()
