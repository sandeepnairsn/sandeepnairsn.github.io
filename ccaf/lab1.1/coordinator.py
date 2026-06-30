"""
Exercise 2, Step 2 -- coordinator.py

Calls the four subagents in order: Classifier -> CRM Enricher -> Drafter
-> Validator, passing each step's output into the next step that needs
it. The coordinator itself is plain Python orchestration -- it makes no
Claude API calls of its own; it only delegates to the subagent
functions and routes data between them.

Run with:
    python3 coordinator.py
"""

from subagents import run_classifier, run_crm_enricher, run_drafter, run_validator

TICKET_TEXT = """\
From: sarah.chen@globalcorp.com
Subject: Cannot access SSO login -- entire team locked out

Our team of 40 has been unable to log in via SSO since 09:00 this
morning. We have a client demo in 3 hours. This is completely blocking
us.
"""

CUSTOMER_EMAIL = "sarah.chen@globalcorp.com"


def main():
    classification = run_classifier(TICKET_TEXT)
    print("[Classifier]", classification)

    crm = run_crm_enricher(CUSTOMER_EMAIL, classification)
    print("[CRM Enricher]", crm)

    # --- Memory Isolation Experiment -----------------------------------
    # The call below passes classification and crm into the drafter, so
    # the draft is grounded in real context. To run the lab's memory
    # isolation experiment: temporarily edit run_drafter() in
    # subagents.py to drop the classification and crm parameters (so it
    # only ever sees `ticket`), then call it here with just TICKET_TEXT.
    # Compare the resulting draft to this version -- does it still
    # mention the right product area and SLA tier, or does it guess
    # (hallucinate) generic-sounding details instead?
    draft = run_drafter(TICKET_TEXT, classification, crm)
    print("[Drafter]\n", draft)

    validation = run_validator(draft, classification, crm)
    print("[Validator]", validation)


if __name__ == "__main__":
    main()
