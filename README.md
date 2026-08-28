# RouteWise AI

RouteWise AI is an AI-assisted troubleshooting helper for Cisco-style lab networks. It pairs deterministic rule checks with an LLM-powered diagnosis pass, and every suggested fix is gated behind mandatory human review before it counts as accepted.

## Features

- Troubleshooting cases covering spanning tree, port security, FHRP (HSRP), GRE tunnels, IPv6 SLAAC, DHCP snooping, QoS, BGP, EtherChannel/LACP, and duplicate addressing
- Deterministic regex-based checks for common configuration signatures
- LLM-powered diagnostic suggestions (OpenAI-compatible chat completions API)
- Structured diagnosis output:
	- Root cause
	- OSI layer
	- Confidence
	- Evidence
	- Next diagnostic command
	- Suggested fix steps
- Mandatory human review workflow with Accepted, Edited, and Rejected decisions
- CSV and Markdown audit logging
- Dashboard showing issue types, severity, and AI-human agreement

## Prerequisites

- Python 3.9 or later
- Git
- pip
- An OpenAI (or OpenAI-compatible) API key

## Installation

Clone the repository:

```bash
git clone <your-repo-url>
cd RouteWiseAI
```

Create a Python virtual environment:

### Windows PowerShell

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Windows Command Prompt

```cmd
python -m venv venv
venv\Scripts\activate
```

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Configure the LLM

Create the Streamlit secrets directory:

```text
.streamlit/
```

Create a file named `.streamlit/secrets.toml` with the following contents:

```toml
OPENAI_API_KEY = "your-openai-api-key"
OPENAI_MODEL = "gpt-4o-mini"
```

Replace `your-openai-api-key` with your actual API key.

> The application reads `OPENAI_MODEL` in `src/engine.py`. Use the singular variable name `OPENAI_MODEL`, not `OPENAI_MODELS`.

The `.streamlit/secrets.toml` file is excluded from Git to prevent accidentally committing credentials.

## Run the Application

From the repository root, start the Streamlit dashboard:

```bash
streamlit run src/app.py
```

Streamlit will display a local URL:

```text
http://localhost:8501
```

Open the URL in a browser.

## How It Works

1. Select a troubleshooting case from the Case Explorer.
2. Review the symptom, topology note, and captured show-command output.
3. Select **Run Hybrid Diagnosis**.
4. RouteWise AI runs deterministic checks using `src/checker.py`.
5. The application sends the case evidence to the LLM using the structured prompt in `prompts/diagnose_prompt.md`.
6. The deterministic result and LLM response are merged into a final diagnosis.
7. Review the diagnosis and proposed CLI steps.
8. Select one of the required human review decisions:
	 - **Accepted**
	 - **Edited**
	 - **Rejected**
9. Save the review decision to record the result in the audit files.

The application does not automatically deploy configuration changes to a network device.

## LLM Fallback Behavior

If `OPENAI_API_KEY` is not configured or the LLM request fails, the application falls back to the deterministic rule checker.
The dashboard displays a warning when this fallback is used. The LLM pass is recommended for cases that do not match a deterministic rule.

## Project Structure

```text
RouteWiseAI/
├── data/
│   ├── cases.csv              # Troubleshooting case dataset
│   └── review_log.csv         # Structured human review records
├── docs/
│   └── audit_logs.md          # Human review audit log
├── prompts/
│   └── diagnose_prompt.md     # LLM diagnosis prompt and output schema
├── src/
│   ├── app.py                 # Streamlit dashboard
│   ├── checker.py             # Deterministic troubleshooting rules
│   └── engine.py              # LLM integration and diagnosis orchestration
├── requirements.txt           # Python dependencies
└── README.md
```

## Deterministic Rule Checks

The rule checker identifies common issues such as:

- Spanning-tree ports stuck in blocking state
- Port security violations (err-disabled interfaces)
- HSRP/FHRP failover failures
- GRE tunnel keepalive/MTU mismatches
- IPv6 SLAAC failures from suppressed router advertisements
- DHCP snooping blocking legitimate server replies
- QoS policies misclassifying and dropping voice traffic
- BGP neighbors stuck in Idle/Active due to AS mismatch
- EtherChannel/LACP mode mismatches
- Duplicate IP addresses

## Review and Audit Data

Review decisions are stored in:

```text
data/review_log.csv
docs/audit_logs.md
```

The dashboard calculates:

- Total reviews
- Accepted diagnoses
- Edited diagnoses
- Rejected diagnoses
- AI-human agreement rate
- Severity distribution
- Issue type distribution
- Recent human overrides

To add five demonstration correction records for the Responsible AI workflow, click **Seed 5 demo correction logs** in the dashboard sidebar.
