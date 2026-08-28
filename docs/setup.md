# Setup Guide

## 1. Clone

```bash
git clone https://github.com/YOUR-USERNAME/NetsageAi.git
cd NetsageAi
```

## 2. Install dependencies

```bash
pip install -r requirements.txt
```

## 3. Configure secrets

Keep API credentials outside the repository. Do not commit secret files.

## 4. Run

```bash
streamlit run src/app.py
```

## Troubleshooting

If the AI service is unavailable, verify the API configuration and network connection. The deterministic rule layer can still provide rule-based findings where supported.
