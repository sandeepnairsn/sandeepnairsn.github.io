"""
Exercise 1, Step 2 -- loop.py

The agentic loop that drives classify_ticket() via the Anthropic
Messages API until Claude has confirmed all three fields:
product_area, severity, and intent.

Setup:
    export ANTHROPIC_API_KEY="your-key-here"
    pip install anthropic

Run with:
    python3 loop.py
"""

import json

from anthropic import Anthropic

from tools import classify_ticket

# ------------------------------------------------------------------------
# Client
# ------------------------------------------------------------------------
client = Anthropic()  # reads ANTHROPIC_API_KEY from the environment

# Any tool-capable model works here. Using a balanced default for this
# single-agent exercise (see Exercise 2 for model selection across a
# multi-agent pipeline).
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024

# ------------------------------------------------------------------------
# Test ticket (same one used across all exercises in this lab)
# ------------------------------------------------------------------------
TICKET_TEXT = """\
From: sarah.chen@globalcorp.com
Subject: Cannot access SSO login -- entire team locked out

Our team of 40 has been unable to log in via SSO since 09:00 this
morning. We have a client demo in 3 hours. This is completely blocking
us.
"""

# ------------------------------------------------------------------------
# Tool registration
# ------------------------------------------------------------------------
tools = [
    {
        "name": "classify_ticket",
        "description": (
            "Classify a support ticket into one or more fields. Call this "
            "as many times as needed, requesting only the fields you still "
            "need, until product_area, severity, and intent are all known."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticket_text": {
                    "type": "string",
                    "description": "The full text of the support ticket to classify.",
                },
                "fields_needed": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Which fields to classify right now. Each item must be "
                        "one of: 'product_area', 'severity', 'intent'."
                    ),
                },
            },
            "required": ["ticket_text", "fields_needed"],
        },
    }
]

# Maps tool name -> python callable, so dispatch is a one-line lookup.
AVAILABLE_FUNCTIONS = {"classify_ticket": classify_ticket}

# ------------------------------------------------------------------------
# Initial conversation
# ------------------------------------------------------------------------
messages = [
    {
        "role": "user",
        "content": (
            "Classify the following support ticket completely. You must "
            "determine all three fields -- product_area, severity, and "
            "intent -- using the classify_ticket tool. Call the tool as "
            "many times as you need to (one field at a time or several at "
            "once) until all three fields are confirmed. Do not stop until "
            "you have all three, and do not guess fields yourself -- only "
            "report values that came from the tool.\n\n"
            f"Ticket:\n{TICKET_TEXT}"
        ),
    }
]

# ------------------------------------------------------------------------
# Agentic loop
# ------------------------------------------------------------------------
iteration = 0

while True:
    iteration += 1

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        tools=tools,
        messages=messages,
    )

    print(f"--- Iteration {iteration} | stop_reason: {response.stop_reason} ---")

    # Mandatory: append the assistant turn before any branching logic.
    # (Try moving this after the branching to see the error mentioned in
    # the reflection questions.)
    messages.append({"role": "assistant", "content": response.content})

    if response.stop_reason == "end_turn":
        final_text = "".join(
            block.text for block in response.content if block.type == "text"
        )
        print("\nFinal classification result:\n")
        print(final_text)
        break

    elif response.stop_reason == "tool_use":
        tool_results = []

        for block in response.content:
            if block.type != "tool_use":
                continue

            print(f"  Tool call: {block.name}({block.input})")

            function_to_call = AVAILABLE_FUNCTIONS[block.name]
            result = function_to_call(**block.input)

            print(f"  Tool result: {result}")

            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                }
            )

        messages.append({"role": "user", "content": tool_results})
        continue

    else:
        # "max_tokens" or "stop_sequence" -- not expected for this small
        # ticket, but handled so the loop never hangs silently.
        print(f"Unhandled stop_reason: {response.stop_reason}")
        break
