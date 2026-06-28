"""
Simple Coordinator-Subagent Research Assistant
================================================
3 research subagents (market, technical, risk) run ONE AFTER ANOTHER.
Their results are passed explicitly to a 4th "synthesizer" subagent.
The synthesizer only runs after a hard gate confirms all 3 results exist.

Each agent runs its own loop and checks `stop_reason` to decide whether to:
  - act (call a tool) and continue
  - stop normally (end_turn)
  - stop because it got cut off (max_tokens)

Setup:
    pip install anthropic
    export ANTHROPIC_API_KEY="sk-ant-..."
    python research_coordinator.py "Should we invest in solid-state batteries?"
"""

import json
import os
import sys

from anthropic import Anthropic

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 1000
MAX_ITERATIONS = 8  # safety valve: stop any agent loop after this many turns
TOPICS = ["market", "technical", "risk"]

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


# ---------------------------------------------------------------------
# Tools: one fake "search" tool, and two "submit answer" tools.
# Submit tools force the model to hand back a clean structured shape
# instead of us trying to parse free-form text.
# ---------------------------------------------------------------------

SEARCH_TOOL = {
    "name": "search_sources",
    "description": "Look up information related to a query. Returns fake but plausible sources.",
    "input_schema": {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    },
}

SUBMIT_FINDING_TOOL = {
    "name": "submit_finding",
    "description": "Submit your final research finding. Call this once you are done.",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "key_points": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        },
        "required": ["summary", "key_points", "confidence"],
    },
}

SUBMIT_SYNTHESIS_TOOL = {
    "name": "submit_synthesis",
    "description": "Submit your final combined answer. Call this once you are done.",
    "input_schema": {
        "type": "object",
        "properties": {
            "final_answer": {"type": "string"},
            "open_questions": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["final_answer", "open_questions"],
    },
}

# --- Coordinator's own tools: it doesn't research or synthesize itself,
# it just decides WHEN to dispatch each subagent. ---

DISPATCH_RESEARCH_TOOL = {
    "name": "dispatch_research_agent",
    "description": "Send a research subagent to investigate one topic angle.",
    "input_schema": {
        "type": "object",
        "properties": {
            "topic": {"type": "string", "enum": TOPICS},
        },
        "required": ["topic"],
    },
}

DISPATCH_SYNTHESIS_TOOL = {
    "name": "dispatch_synthesizer",
    "description": (
        "Send the synthesizer subagent to combine all research findings into "
        "a final answer. Only call this after all research topics are done."
    ),
    "input_schema": {"type": "object", "properties": {}},
}

COORDINATOR_DONE_TOOL = {
    "name": "coordinator_done",
    "description": "Call this once the synthesizer has produced the final answer.",
    "input_schema": {"type": "object", "properties": {}},
}


def fake_search(query):
    """Pretend tool: no real network call, just made-up results."""
    return {
        "results": [
            f"Placeholder source 1 about: {query}",
            f"Placeholder source 2 about: {query}",
        ]
    }


# ---------------------------------------------------------------------
# The agentic loop, shared by every agent.
# It keeps calling the model until the model calls its "submit" tool
# (success) or stops for some other reason (handled, not ignored).
# ---------------------------------------------------------------------

def run_agent(system_prompt, first_message, tools, submit_tool_name):
    messages = [{"role": "user", "content": first_message}]

    for iteration in range(MAX_ITERATIONS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            messages=messages,
            tools=tools,
        )
        messages.append({"role": "assistant", "content": response.content})
        print(f"  [STOP_REASON CHECK] iteration {iteration+1}: stop_reason='{response.stop_reason}'")

        # --- This is the key check: what should the agent do next? ---
        if response.stop_reason == "tool_use":
            print("  [STOP_REASON CHECK] -> ACT: tool requested, will execute and CONTINUE loop")
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue

                if block.name == submit_tool_name:
                    # The model handed us its final structured answer.
                    # We stop here -- this is a successful halt.
                    print(f"  [STOP_REASON CHECK] -> HALT: '{submit_tool_name}' called, task truly done")
                    return block.input

                elif block.name == "search_sources":
                    result = fake_search(block.input["query"])
                else:
                    result = {"error": f"unknown tool {block.name}"}

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                })

            # Feed tool results back in and let the loop continue (ACT -> CONTINUE)
            print("  [STOP_REASON CHECK] -> CONTINUE: tool result sent back, looping again")
            messages.append({"role": "user", "content": tool_results})

        elif response.stop_reason == "end_turn":
            # Model stopped talking without ever submitting an answer.
            print("  [STOP_REASON CHECK] -> HALT: 'end_turn' with no submission (incomplete)")
            print("  (agent ended without submitting a result)")
            return None

        elif response.stop_reason == "max_tokens":
            # Got cut off mid-answer -- don't trust it, just halt.
            print("  [STOP_REASON CHECK] -> HALT: 'max_tokens' (truncated, degraded halt)")
            print("  (agent got cut off / ran out of tokens)")
            return None

        else:
            print(f"  [STOP_REASON CHECK] -> HALT: unrecognized stop_reason (defensive halt)")
            print(f"  (unexpected stop_reason: {response.stop_reason})")
            return None

    # Loop ran MAX_ITERATIONS times without the agent submitting anything.
    print(f"  (gave up after {MAX_ITERATIONS} iterations without a submission)")
    return None


# ---------------------------------------------------------------------
# Research subagent: one per topic, run sequentially.
# ---------------------------------------------------------------------

def run_research_agent(topic, question):
    print(f"\n--- Researching topic: {topic} ---")
    system_prompt = (
        f"You are a research specialist focused only on the '{topic}' angle. "
        "Use search_sources if helpful, then call submit_finding with your result.\n\n"
        "IMPORTANT: search_sources is a STUB/placeholder tool for testing this "
        "pipeline. It does NOT return real data -- it only returns dummy text "
        "like 'Placeholder source about: <your query>'. Do NOT use your own "
        "background knowledge to fill in real-sounding facts. Your summary and "
        "key_points must honestly reflect that this is placeholder research, "
        "e.g. 'Placeholder research for {topic}: no real data available, stub "
        "search returned dummy results only.'"
    )
    result = run_agent(
        system_prompt=system_prompt,
        first_message=f"Question: {question}\nFocus only on the {topic} angle.",
        tools=[SEARCH_TOOL, SUBMIT_FINDING_TOOL],
        submit_tool_name="submit_finding",
    )
    if result:
        result["topic"] = topic
    return result


# ---------------------------------------------------------------------
# Synthesizer subagent: combines all findings. Has NO search tool --
# it only sees what we explicitly hand it below.
# ---------------------------------------------------------------------

def run_synthesizer_agent(question, findings):
    print("\n--- Synthesizing final answer ---")

    # Explicit structured context: each finding is clearly labeled.
    context_text = ""
    for f in findings:
        context_text += (
            f"\n[{f['topic'].upper()} FINDING] (confidence: {f['confidence']})\n"
            f"Summary: {f['summary']}\n"
            f"Key points: {', '.join(f['key_points'])}\n"
        )

    print("  [EXPLICIT CONTEXT PASSED TO SYNTHESIZER] -----------------------")
    print(context_text)
    print("  --------------------------------------------------------------")

    system_prompt = (
        "You combine research findings from specialists into one final answer. "
        "You do not research anything yourself. Call submit_synthesis when done.\n\n"
        "IMPORTANT: the findings you receive are PLACEHOLDER/dummy data from a "
        "test pipeline, not real research. Your final_answer must say plainly "
        "that this is a placeholder/demo run with no real data, not a real "
        "investment recommendation. Do not invent real-sounding analysis."
    )
    first_message = (
        f"Original question: {question}\n\n"
        f"Here are the research findings to combine:\n{context_text}\n\n"
        "Write the final combined answer now."
    )
    return run_agent(
        system_prompt=system_prompt,
        first_message=first_message,
        tools=[SUBMIT_SYNTHESIS_TOOL],
        submit_tool_name="submit_synthesis",
    )


# ---------------------------------------------------------------------
# Coordinator: now an AGENT itself. The LLM decides which research
# topics to dispatch and when to call the synthesizer -- but the HARD
# GATE is still enforced in code: dispatch_synthesizer() will refuse to
# run the synthesizer if findings are missing, no matter what the
# coordinator LLM tries to do.
# ---------------------------------------------------------------------

COORDINATOR_SYSTEM_PROMPT = f"""You are the coordinator of a research assistant team.

You have research subagents for these topics: {", ".join(TOPICS)}.
You also have a synthesizer subagent that combines all findings into one answer.

Your job:
1. Dispatch a research subagent (dispatch_research_agent) for EACH topic.
2. Once all topics are researched, dispatch the synthesizer (dispatch_synthesizer).
3. Call coordinator_done once you have the final synthesized answer.

You cannot dispatch the synthesizer before all topics are researched -- it will
be refused if you try too early.
"""


def run_coordinator_agent(question):
    findings = []          # filled in as research agents report back
    final_synthesis = {}   # filled in once the synthesizer reports back

    messages = [{"role": "user", "content": f"Research question: {question}"}]
    tools = [DISPATCH_RESEARCH_TOOL, DISPATCH_SYNTHESIS_TOOL, COORDINATOR_DONE_TOOL]

    for iteration in range(MAX_ITERATIONS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=COORDINATOR_SYSTEM_PROMPT,
            messages=messages,
            tools=tools,
        )
        messages.append({"role": "assistant", "content": response.content})
        print(f"  [STOP_REASON CHECK] (coordinator) iteration {iteration+1}: stop_reason='{response.stop_reason}'")

        if response.stop_reason == "tool_use":
            print("  [STOP_REASON CHECK] (coordinator) -> ACT: tool requested, will execute and CONTINUE loop")
            tool_results = []

            for block in response.content:
                if block.type != "tool_use":
                    continue

                if block.name == "dispatch_research_agent":
                    topic = block.input["topic"]
                    print(f"  [COORDINATOR -> SUBAGENT] Hub delegating to RESEARCH specialist: '{topic}'")
                    finding = run_research_agent(topic, question)
                    if finding:
                        findings.append(finding)
                        tool_result_text = f"Research on '{topic}' complete."
                    else:
                        tool_result_text = f"Research on '{topic}' FAILED."

                elif block.name == "dispatch_synthesizer":
                    # --- HARD GATE (in code, not left to the LLM) ---
                    if len(findings) != len(TOPICS):
                        print(f"  [HARD GATE CHECK] BLOCKED: {len(findings)}/{len(TOPICS)} "
                              f"research topics done -- synthesizer will NOT run")
                        tool_result_text = (
                            f"Refused: only {len(findings)}/{len(TOPICS)} topics "
                            "researched so far. Dispatch the missing topics first."
                        )
                    else:
                        print(f"  [HARD GATE CHECK] ALLOWED: {len(findings)}/{len(TOPICS)} "
                              f"research topics done -- proceeding to synthesis")
                        print("  [COORDINATOR -> SUBAGENT] Hub delegating to SYNTHESIS specialist")
                        synthesis = run_synthesizer_agent(question, findings)
                        if synthesis:
                            final_synthesis.update(synthesis)
                            tool_result_text = "Synthesis complete."
                        else:
                            tool_result_text = "Synthesis FAILED."

                elif block.name == "coordinator_done":
                    tool_result_text = "Acknowledged."
                else:
                    tool_result_text = f"Unknown tool {block.name}"

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": tool_result_text,
                })

                # coordinator_done ends the whole coordinator loop
                if block.name == "coordinator_done":
                    print("  [STOP_REASON CHECK] (coordinator) -> HALT: 'coordinator_done' called, task truly done")
                    return final_synthesis

            messages.append({"role": "user", "content": tool_results})

        elif response.stop_reason == "end_turn":
            print("  [STOP_REASON CHECK] (coordinator) -> HALT: 'end_turn' with no coordinator_done call")
            print("  (coordinator ended its turn without calling coordinator_done)")
            return final_synthesis

        elif response.stop_reason == "max_tokens":
            print("  [STOP_REASON CHECK] (coordinator) -> HALT: 'max_tokens' (truncated, degraded halt)")
            print("  (coordinator got cut off / ran out of tokens)")
            return final_synthesis

        else:
            print("  [STOP_REASON CHECK] (coordinator) -> HALT: unrecognized stop_reason (defensive halt)")
            print(f"  (unexpected stop_reason: {response.stop_reason})")
            return final_synthesis

    # Coordinator ran MAX_ITERATIONS times without calling coordinator_done.
    print(f"  (coordinator gave up after {MAX_ITERATIONS} iterations)")
    return final_synthesis


def main():
    if len(sys.argv) < 2:
        print('Usage: python research_coordinator.py "<your question>"')
        return

    question = sys.argv[1]
    synthesis = run_coordinator_agent(question)

    if not synthesis or "final_answer" not in synthesis:
        print("\nNo final answer was produced.")
        return

    print("\n" + "=" * 60)
    print("FINAL ANSWER")
    print("=" * 60)
    print(synthesis["final_answer"])
    print("\nOpen questions:")
    for q in synthesis.get("open_questions", []):
        print(f"  - {q}")


if __name__ == "__main__":
    main()
