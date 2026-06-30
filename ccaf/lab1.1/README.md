# CCA-F Module 1, Lab 1.1 -- Building the Agentic Loop

## Setup

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your-key-here"
```

## Exercise 1 -- The Agentic Loop

- `tools.py` -- `classify_ticket()`, the simulated classification tool.
- `loop.py` -- the while-loop that drives Claude through tool calls
  until product_area, severity, and intent are all confirmed.

Run:
```bash
python3 tools.py     # quick sanity check of the tool function alone
python3 loop.py       # the full agentic loop
```

Try the reflection exercises from the lab:
- Run `loop.py` a few times -- does the number of tool calls vary?
- Move the `messages.append({"role": "assistant", ...})` line to *after*
  the `if/elif` branching and re-run -- note the error.
- Swap `while True:` for `for i in range(2):` and re-run -- note what
  breaks.

## Exercise 2 -- Coordinator & Subagents

- `subagents.py` -- four isolated single-call functions: `run_classifier`,
  `run_crm_enricher`, `run_drafter`, `run_validator`.
- `coordinator.py` -- plain Python orchestration that calls all four in
  sequence and prints each labelled output.

Run:
```bash
python3 coordinator.py
```

### Memory Isolation Experiment
In `subagents.py`, temporarily change `run_drafter` to drop the
`classification` and `crm` parameters so it only ever sees the raw
ticket text. Re-run `coordinator.py` and compare the new draft to the
original -- does it still reference the correct product area and SLA
tier, or does it guess?

## Exercise 3 -- Explicit Context Passing

- `context.py` -- `TicketContext` dataclass: required intake fields
  with no defaults, plus `Optional[str]` fields for everything
  populated downstream, plus `classification_complete()`,
  `enrichment_complete()`, and `draft_complete()` helper methods.
- `coordinator_v2.py` -- `coordinator.py` refactored to read/write
  state on a single `ctx` object, while still passing only the
  specific fields each subagent needs (not the whole `ctx`).

Run:
```bash
python3 context.py        # standalone check -- no API key needed
python3 coordinator_v2.py
```

## Exercise 4 -- Programmatic Step Enforcement

- `gates.py` -- `PipelineGateError` plus `gate_classification`,
  `gate_enrichment`, `gate_draft`. Each raises with a message naming
  the specific missing field(s); `gate_enrichment` fails if *either*
  `account_tier` or `sla_tier` is missing (partial CRM data is treated
  as incomplete).
- `coordinator_v3.py` -- `coordinator_v2.py` wrapped in
  `try/except PipelineGateError`, with a gate call and a "Gate N
  passed" print between each step.
- `coordinator_v3_sabotage.py` -- copy of `coordinator_v3.py` that
  forces `ctx.severity = None` right after the Classifier runs, to
  prove Gate 1 blocks immediately and names `severity` as the missing
  field, and that steps 2-4 never execute.

Run:
```bash
python3 coordinator_v3.py
python3 coordinator_v3_sabotage.py   # should print [PIPELINE BLOCKED] naming severity
```

### Verified without live API calls
`context.py`'s construction check and all four gate functions in
`gates.py` were tested directly (bypassing the subagent API calls) and
behave as specified:
- Missing required `TicketContext` fields raise `TypeError` at
  construction.
- Gates pass silently when their preconditions are met.
- Gate 1 blocks and names `severity` specifically when it's `None`.
- Gate 2 blocks on partial CRM data (`account_tier` set, `sla_tier`
  `None`) -- it does not pass on a partial result.
- Gate 3 blocks when `draft_response` is `None`.

`coordinator_v2.py`, `coordinator_v3.py`, and
`coordinator_v3_sabotage.py` make real `client.messages.create()`
calls via `subagents.py` and need `ANTHROPIC_API_KEY` set to run
end-to-end.
