import json
import anthropic
from tools import classify_ticket

client = anthropic.Anthropic()

TICKET = (
    "From: sarah.chen@globalcorp.com "
    "Subject: Cannot access SSO login — entire team locked out "
    "Our team of 40 has been unable to log in via SSO since 09:00 this morning. "
    "We have a client demo in 3 hours. This is completely blocking us."
)

tools = [
    {
        "name": "classify_ticket",
        "description": (
            "Classifies a support ticket into structured fields. "
            "Call this tool with the ticket text and a list of fields you need. "
            "Returns a dict with the requested field values."
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
                        "List of classification fields to return. "
                        "Valid values: product_area, severity, intent."
                    ),
                },
            },
            "required": ["ticket_text", "fields_needed"],
        },
    }
]

messages = [
    {
        "role": "user",
        "content": (
            f"Classify the following support ticket. You must determine all three fields: "
            f"product_area, severity, and intent. Use the classify_ticket tool as many times "
            f"as needed until all three fields are confirmed. Do not stop until you have all three.\n\n"
            f"Ticket:\n{TICKET}"
        ),
    }
]

iteration = 0
while True:
    iteration += 1
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        tools=tools,
        messages=messages,
    )
    print(f"\n--- Iteration {iteration} | stop_reason: {response.stop_reason} ---")

    messages.append({"role": "assistant", "content": response.content})

    if response.stop_reason == "end_turn":
        for block in response.content:
            if hasattr(block, "text"):
                print("\nFinal classification result:")
                print(block.text)
        break

    if response.stop_reason == "tool_use":
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"  Tool call: {block.name}({block.input})")
                if block.name == "classify_ticket":
                    result = classify_ticket(**block.input)
                else:
                    result = {"error": f"Unknown tool: {block.name}"}
                print(f"  Tool result: {result}")
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    }
                )
        messages.append({"role": "user", "content": tool_results})

    elif response.stop_reason == "max_tokens":
        print("WARNING: Response cut off at max_tokens limit.")
        break

    elif response.stop_reason == "stop_sequence":
        print("Stop sequence matched — treating as end_turn.")
        for block in response.content:
            if hasattr(block, "text"):
                print(block.text)
        break
