import random

PRODUCT_AREAS = ["Billing", "Platform", "Integrations", "Security", "Onboarding"]
SEVERITIES = ["P1-Critical", "P2-High", "P3-Medium", "P4-Low"]
INTENTS = ["Bug", "Question", "Feature Request", "Billing Dispute"]


def classify_ticket(ticket_text: str, fields_needed: list) -> dict:
    all_values = {
        "product_area": random.choice(PRODUCT_AREAS),
        "severity": random.choice(SEVERITIES),
        "intent": random.choice(INTENTS),
    }
    return {field: all_values[field] for field in fields_needed if field in all_values}
