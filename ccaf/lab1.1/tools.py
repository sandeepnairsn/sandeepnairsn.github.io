"""
Exercise 1, Step 1 -- tools.py

Defines classify_ticket(), the function Claude will call as a tool
during the agentic loop in loop.py.

For this lab the classification values are simulated (randomly chosen
from the field vocabulary below). In production this function would
call a real classification model or rules engine instead of
random.choice() -- the point of this exercise is the function
signature and return shape, not the classification logic itself.
"""

import random

# Field vocabulary ------------------------------------------------------
PRODUCT_AREAS = ["Billing", "Platform", "Integrations", "Security", "Onboarding"]
SEVERITIES = ["P1-Critical", "P2-High", "P3-Medium", "P4-Low"]
INTENTS = ["Bug", "Question", "Feature Request", "Billing Dispute"]

_FIELD_VALUES = {
    "product_area": PRODUCT_AREAS,
    "severity": SEVERITIES,
    "intent": INTENTS,
}


def classify_ticket(ticket_text: str, fields_needed: list) -> dict:
    """
    Simulate classification of a support ticket.

    Args:
        ticket_text: The full text of the support ticket. Unused in this
            simulated version, but kept in the signature because a real
            classifier would need it.
        fields_needed: Which fields to classify right now. Each item
            must be one of: "product_area", "severity", "intent".

    Returns:
        A dict containing only the requested fields, each mapped to a
        value drawn from that field's vocabulary.
    """
    result = {}
    for field in fields_needed:
        if field not in _FIELD_VALUES:
            raise ValueError(
                f"Unknown field '{field}'. Expected one of {list(_FIELD_VALUES)}."
            )
        result[field] = random.choice(_FIELD_VALUES[field])
    return result


if __name__ == "__main__":
    # Quick manual check -- run `python3 tools.py` to sanity-check the
    # function in isolation before wiring it into loop.py.
    sample = classify_ticket(
        ticket_text="Cannot access SSO login -- entire team locked out",
        fields_needed=["product_area", "severity", "intent"],
    )
    print(sample)
