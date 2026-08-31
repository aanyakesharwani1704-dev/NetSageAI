# NetSageAI

NetSageAI is an AI-assisted network troubleshooting assistant for Cisco-style lab environments. It combines deterministic rule-based checks with a Gemini-powered diagnosis pass. Every suggested fix is placed behind a mandatory human review step before it is accepted.

## Features

* Troubleshooting cases covering:

  * Spanning Tree Protocol (STP)
  * Port Security
  * FHRP / HSRP
  * GRE Tunnels
  * IPv6 SLAAC
  * DHCP Snooping
  * QoS
  * BGP
  * EtherChannel / LACP
  * Duplicate IP Addressing
* Deterministic regex-based checks for common network configuration and output signatures
* Google Gemini-powered diagnostic suggestions
* Structured diagnosis output:

  * Root cause
  * OSI layer
  * Confidence
  * Evidence
  * Next diagnostic command
  * Suggested fix steps
* Hybrid diagnosis combining deterministic checks and LLM reasoning
* Mandatory Human-in-the-Loop review workflow:

  * Accepted
  * Edited
  * Rejected
* CSV and Markdown audit logging
* Dashboard showing:

  * Issue types
  * Severity
  * Review statistics
  * AI-human agreement rate
  * Recent human overrides
* Safe troubleshooting workflow with no automatic configuration deployment

## Architecture

NetSageAI follows a hybrid troubleshooting architecture:

```text
User selects network case
          |
          v
   Deterministic Checker
          |
          +----------------+
          |                |
          v                v
    Rule Findings      Case Evidence
          |                |
          +-------+--------+
                  |
                  v
             Gemini LLM
                  |
                  v
        Structured JSON Diagnosis
                  |
                  v
        Diagnosis Merge Engine
                  |
                  v
        Final Troubleshooting
             Recommendation
                  |
                  v
        Human Review Gate
        /        |        \
   Accepted    Edited    Rejected
        \        |        /
         +-------+-------+
                 |
                 v
        Audit / Review Logs
```

The deterministic checker provides reliable rule-based findings, while Gemini provides additional reasoning for cases that require broader inference.

## Prerequisites

* Python 3.9 or later
* Git
* pip
* A Google Gemini API key

## Installation

Clone the repository:

```bash
git clone <your-repo-url>
cd NetSageAI
```

Create a Python virtual environment.

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

## Configure Gemini

Create the Streamlit secrets directory:

```text
.streamlit/
```

Create a file named:

```text
.streamlit/secrets.toml
```

Add:

```toml
GEMINI_API_KEY = "your-gemini-api-key"
GEMINI_MODEL = "gemini-2.5-flash"
```

Replace `your-gemini-api-key` with your actual Gemini API key.

### Security

Never commit your Gemini API key to GitHub.

The `.streamlit/secrets.toml` file should remain excluded from Git.

If you are using Streamlit Cloud, the same values can be configured through the application's Secrets settings instead of committing the file to the repository.

## Run the Application

From the repository root, start the Streamlit dashboard:

```bash
streamlit run src/app.py
```

Streamlit will display a local URL similar to:

```text
http://localhost:8501
```

Open the URL in a browser.

## How It Works

1. Select a troubleshooting case from the **Case Explorer**.
2. Review the symptom, topology information, and captured show-command output.
3. Select **Run Hybrid Diagnosis**.
4. NetSageAI runs deterministic checks using `src/checker.py`.
5. The application prepares the case evidence and checker findings.
6. The evidence is sent to Google Gemini using the structured prompt in `prompts/diagnose_prompt.md`.
7. Gemini returns a structured JSON diagnosis.
8. The diagnosis is validated and combined with the deterministic checker result.
9. The final diagnosis displays:

   * Root cause
   * OSI layer
   * Confidence
   * Evidence
   * Next diagnostic command
   * Suggested fix steps
10. The user reviews the diagnosis through the mandatory Human Review Gate.
11. The reviewer selects:

    * **Accepted**
    * **Edited**
    * **Rejected**
12. The review decision is saved to the audit files.

The application does **not** automatically deploy configuration changes to a network device.

## Gemini Fallback Behavior

NetSageAI is designed to remain usable if the Gemini request cannot be completed.

If:

* `GEMINI_API_KEY` is missing,
* the Gemini request fails,
* the configured Gemini model cannot be reached,
* or the Gemini response cannot be parsed,

the application falls back to the deterministic rule checker.

The dashboard displays a warning when the LLM fallback is activated.

This provides a basic troubleshooting result even when the AI service is unavailable.

## Diagnosis Output

The Gemini diagnosis follows a structured JSON format:

```json
{
  "root_cause": "string",
  "osi_layer": "string",
  "confidence": 0.0,
  "evidence": [
    "string"
  ],
  "next_command": "string",
  "fix_steps": [
    "string"
  ]
}
```

The diagnosis prompt is stored in:

```text
prompts/diagnose_prompt.md
```

The prompt instructs Gemini to:

* Use only available case evidence
* Provide a confidence score between 0.0 and 1.0
* Provide concrete evidence
* Recommend a single diagnostic command
* Provide ordered CLI-oriented fix steps
* Reduce confidence when the available evidence is insufficient

## Project Structure

```text
NetSageAI/
├── data/
│   ├── cases.csv              # Troubleshooting case dataset
│   └── review_log.csv         # Structured human review records
│
├── docs/
│   └── audit_logs.md          # Human review audit log
│
├── prompts/
│   └── diagnose_prompt.md     # Gemini diagnosis prompt and JSON schema
│
├── src/
│   ├── app.py                 # Streamlit dashboard
│   ├── checker.py             # Deterministic troubleshooting rules
│   └── engine.py              # Gemini integration and diagnosis orchestration
│
├── .streamlit/
│   └── secrets.toml           # Local Gemini configuration (do not commit)
│
├── requirements.txt           # Python dependencies
└── README.md
```

## Deterministic Rule Checks

The rule checker identifies common network troubleshooting issues such as:

* Spanning-tree ports stuck in blocking state
* Port-security violations and err-disabled interfaces
* HSRP/FHRP failover problems
* GRE tunnel keepalive and MTU mismatches
* IPv6 SLAAC failures caused by suppressed router advertisements
* DHCP snooping blocking legitimate server replies
* QoS policies misclassifying or dropping voice traffic
* BGP neighbors stuck in Idle/Active because of AS mismatch
* EtherChannel/LACP mode mismatches
* Duplicate IP addresses

## Human-in-the-Loop Review

Human review is a mandatory part of the NetSageAI workflow.

Each diagnosis can be:

### Accepted

The reviewer agrees with the diagnosis and proposed troubleshooting steps.

### Edited

The reviewer identifies an issue and provides corrected fix steps.

### Rejected

The reviewer determines that the diagnosis should not be accepted.

This workflow helps keep AI-generated troubleshooting recommendations subject to human validation.

## Review and Audit Data

Review decisions are stored in:

```text
data/review_log.csv
docs/audit_logs.md
```

The dashboard calculates:

* Total reviews
* Accepted diagnoses
* Edited diagnoses
* Rejected diagnoses
* AI-human agreement rate
* Severity distribution
* Issue type distribution
* Recent human overrides

To add five demonstration correction records for the Responsible AI workflow, click:

**Seed 5 demo correction logs**

in the dashboard sidebar.

## Safety and Deployment

NetSageAI is designed as a troubleshooting assistant for Cisco-style lab environments.

The application:

* Does not automatically deploy configuration changes
* Provides diagnostic commands for verification
* Places proposed fixes behind human review
* Uses deterministic checks alongside AI reasoning
* Records human review decisions for auditability

Any configuration change should be verified by an authorized network operator before being applied to a real device.

