"""
Exercise 2, Step 1 -- subagents.py

Four single-purpose subagents used by coordinator.py:
    run_classifier()    -> dict
    run_crm_enricher()  -> dict
    run_drafter()       -> str
    run_validator()     -> str

Each function makes exactly one client.messages.create() call. None of
them share memory with each other -- every subagent knows only what is
explicitly passed into it as arguments. That isolation is the point of
this exercise; see the "Memory Isolation Experiment" note in
coordinator.py.

Model choice for this lab: each subagent uses claude-haiku-4-5-20251001
-- fast and cost-efficient for a focused, single-responsibility task.
(A coordinator that made its own routing decisions via the API would
use claude-opus-4-6 instead; in this lab the coordinator is plain
Python orchestration, so that model isn't called here.)
"""

import json

from anthropic import Anthropic

client = Anthropic()

SUBAGENT_MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 1024


def _strip_code_fences(text: str) -> str:
    """Defensively remove ``` or ```json fences before json.loads()."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[len("json"):]
        if cleaned.endswith("```"):
            cleaned = cleaned[: -len("```")]
    return cleaned.strip()


def _text_of(response) -> str:
    """Concatenate all text blocks from a Messages API response."""
    return "".join(block.text for block in response.content if block.type == "text")


def run_classifier(ticket: str) -> dict:
    """Classify a ticket into product_area, severity, intent. Returns a dict."""
    response = client.messages.create(
        model=SUBAGENT_MODEL,
        max_tokens=MAX_TOKENS,
        system=(
            "Classify the support ticket into product_area, severity, and "
            "intent. product_area is one of: Billing, Platform, Integrations, "
            "Security, Onboarding. severity is one of: P1-Critical, P2-High, "
            "P3-Medium, P4-Low. intent is one of: Bug, Question, Feature "
            "Request, Billing Dispute. Respond only in JSON with exactly "
            "those three keys -- no prose, no markdown fences."
        ),
        messages=[{"role": "user", "content": ticket}],
    )

    cleaned = _strip_code_fences(_text_of(response))
    return json.loads(cleaned)


def run_crm_enricher(customer_email: str, classification: dict) -> dict:
    """
    Simulate a CRM lookup for this customer/ticket.
    In production this would call a real CRM API via an MCP tool.
    """
    response = client.messages.create(
        model=SUBAGENT_MODEL,
        max_tokens=MAX_TOKENS,
        system=(
            "Simulate a CRM lookup for the given customer email and ticket "
            "classification. Return account_tier, sla_tier, account_manager, "
            "and contract_value. Respond only in JSON with exactly those four "
            "keys -- no prose, no markdown fences."
        ),
        messages=[
            {
                "role": "user",
                "content": (
                    f"Customer email: {customer_email}\n"
                    f"Ticket classification: {json.dumps(classification)}"
                ),
            }
        ],
    )

    cleaned = _strip_code_fences(_text_of(response))
    return json.loads(cleaned)


def run_drafter(ticket: str, classification: dict, crm: dict) -> str:
    """Draft a professional first-response email referencing the SLA tier."""
    context = (
        f"Ticket:\n{ticket}\n\n"
        f"Classification: {json.dumps(classification)}\n\n"
        f"CRM info: {json.dumps(crm)}"
    )

    response = client.messages.create(
        model=SUBAGENT_MODEL,
        max_tokens=MAX_TOKENS,
        system=(
            "Draft a professional first-response email to the customer. "
            "Reference their SLA tier from the CRM info to set expectations "
            "on response time. Keep it concise and reassuring."
        ),
        messages=[{"role": "user", "content": context}],
    )

    return _text_of(response)


def run_validator(draft: str, classification: dict, crm: dict) -> str:
    """Check the draft against product area, SLA tier, and tone."""
    context = (
        f"Draft email:\n{draft}\n\n"
        f"Expected product area: {classification.get('product_area')}\n"
        f"Expected SLA tier: {crm.get('sla_tier')}\n"
        f"Account tier: {crm.get('account_tier')}"
    )

    response = client.messages.create(
        model=SUBAGENT_MODEL,
        max_tokens=MAX_TOKENS,
        system=(
            "Check the draft email against the expected product area, SLA "
            "tier, and a professional tone. If everything matches and reads "
            "well, reply with exactly: APPROVED. Otherwise, list the "
            "specific issues found."
        ),
        messages=[{"role": "user", "content": context}],
    )

    return _text_of(response)
