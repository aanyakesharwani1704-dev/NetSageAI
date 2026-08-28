# NetsageAi

NetsageAi is an AI-assisted network troubleshooting prototype that combines deterministic rule-based checks with LLM-powered diagnosis and human review.

## Features

- Rule-based network fault detection
- LLM-assisted diagnosis
- Structured diagnosis output
- Confidence scoring
- Human review workflow
- Review/audit logging
- Sample troubleshooting cases

## Architecture

```text
Network Case
     |
     v
Rule-Based Checker
     |
     +------> Deterministic Findings
     |
     v
LLM Diagnosis Engine
     |
     v
Structured Diagnosis
     |
     v
Human Review
     |
     v
Review / Audit Log
```

## Project Structure

```text
NetsageAi/
├── src/
│   ├── app.py
│   ├── checker.py
│   └── engine.py
├── data/
│   ├── cases.csv
│   └── review_log.csv
├── docs/
│   ├── architecture.md
│   ├── setup.md
│   ├── features.md
│   ├── audit_logs.md
│   └── usage.md
├── prompts/
│   └── diagnose_prompt.md
├── requirements.txt
└── README.md
```

## Installation

```bash
git clone https://github.com/YOUR-USERNAME/NetsageAi.git
cd NetsageAi
pip install -r requirements.txt
```

Configure the required API credentials locally before running the AI functionality.

## Run

```bash
streamlit run src/app.py
```

## Documentation

See the `docs/` directory for architecture, setup, features, usage, and audit-log documentation.

## Important

Never commit API keys, passwords, or other secrets to GitHub.

## Future Scope

- FastAPI backend
- React frontend
- Database persistence
- Authentication
- Automated evaluation
- Docker deployment
