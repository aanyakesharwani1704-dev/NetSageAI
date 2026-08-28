# Architecture

```text
User
 |
 v
Streamlit Application
 |
 v
Diagnosis Engine
 |
 +----------------------+
 |                      |
 v                      v
Rule Checker          LLM API
 |                      |
 +----------+-----------+
            |
            v
     Structured Diagnosis
            |
            v
       Human Review
            |
            v
        Audit Log
```

## Components

### Application
`src/app.py` provides the user-facing Streamlit interface.

### Rule Checker
`src/checker.py` performs deterministic pattern-based network diagnosis.

### Diagnosis Engine
`src/engine.py` coordinates evidence, rule findings, LLM reasoning, validation, and fallback behavior.

### Data
The `data/` directory contains sample cases and review records.

### Prompts
The `prompts/` directory contains the diagnosis prompt used by the AI layer.
