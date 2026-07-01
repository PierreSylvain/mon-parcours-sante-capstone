# Mon Parcours Santé 🩺

**A health-admin concierge agent (Google ADK + Gemini) that organizes appointments, treatments, lab documents and reimbursements in natural conversation — and never gives medical advice.**

Capstone project for the **5-Day AI Agents Intensive** (Google × Kaggle).
📄 Full write-up: *[link to your Kaggle write-up]* · 👤 Author: **pierresylvain**

---

## Why

Managing your own healthcare is a **logistics** problem, not a knowledge problem: scattered appointments, forgotten renewals, lab results buried as PDFs, opaque reimbursements (*Sécurité sociale* + *mutuelle*). **Mon Parcours Santé** handles that administrative layer in plain French conversation — while deferring every clinical judgment to a professional.

## The design principle — a concierge that knows where to stop

> The agent **never interprets a result, diagnoses, or advises on treatment.** It organizes, reminds, prepares, coordinates and surfaces information.

This boundary is the project's backbone and its main differentiator — and most of the engineering went into making it hold *deterministically*.

## Architecture

```
SURFACE     Chat (ADK web UI)
RUNTIME     LlmAgent (Gemini) + SkillToolset → loads 1 of 4 skills on demand
DATA/TOOLS  custom tools · RAG · MCP (Calendar/Gmail, read-first)
            HealthStore (SQLite local → Firestore in prod)
            deterministic guardrails on model input & tool calls
```

## Skills

| Skill | Does | Does **not** |
|---|---|---|
| `consultation-prep` | One-page brief + targeted questions before a visit | Interpret results |
| `medication-tracking` | List treatments, compute renewals, propose reminders | Advise on dose; start/stop a treatment |
| `document-management` | Parse lab PDFs → structured values, RAG index, marker timeline | Flag a value "abnormal" |
| `reimbursement-tracking` | Track care vs reimbursements, flag missing, estimate remaining cost | Give tax/legal advice; recommend a mutuelle |

## Safety & guardrails

- **Medical boundary** — a deterministic `before_model` hook intercepts diagnosis, result interpretation, treatment change, and **emergency** (explicit redirect to 15 / 112 / 3114) before the model answers.
- **Financial boundary** — blocks financial *advice* while letting factual reimbursement queries through.
- **Zero ambient authority** — read-only by default; any write (calendar event, profile update) is described and **confirmed** first.
- **Instruction-source boundary** — text inside PDFs/emails is data, never commands (anti-injection).

## Results

| Suite | Metric | Result |
|---|---|---|
| Security (7 categories) | deterministic gate | **100%** (7/7) |
| Functional (32 cases × 4 skills) | `pass^5` | **91%** (29/32) |
| Skill activation | correct `load_skill` rate | **84%** |

---

## Quickstart

**Requirements:** Python 3.12+, [uv](https://astral.sh/uv), a Gemini API key.

```bash
git clone https://github.com/PierreSylvain/mon-parcours-sante-capstone.git
cd mon-parcours-sante-capstone
uv venv
uv pip install -e .
cp .env.example .env          # then add your GOOGLE_API_KEY
```

**Run the agent:**
```bash
uv run python -m scripts.seed_data     # sample profile
uv run adk web                         # open the dev UI, pick "mon_parcours_sante"
```

**Try it (in French):** *« J'ai RDV avec le cardiologue jeudi, prépare-moi »* ·
*« Montre l'évolution de ma TSH »* · *« Mes remboursements en attente ? »*

## Evaluation

Security cases test the guardrails deterministically (no LLM); functional cases run the agent with `pass^k`. Always run without MCP:

```bash
MPS_DISABLE_MCP=1 uv run python scripts/run_evals.py --suite security
MPS_DISABLE_MCP=1 uv run python scripts/run_evals.py --suite functional -k 5
```

Coverage validators (no API key needed):
```bash
python validate_evalset.py            # functional coverage & diversity
python validate_security_suite.py     # the 7 security categories
```

## Project structure

```
mon_parcours_sante/     # agent, guardrails, tools, HealthStore, skills/
scripts/                # run_evals.py, seed_data.py
evals/                  # functional/*.evalset.json, security/safety.evalset.json
docs/                   # SPEC, GEMINI.md, BUILD_PHASE_1..5.md, COMMANDS.md
KAGGLE_WRITEUP.md
```

## Tech stack

Google **ADK** · **Gemini** · SQLite / Firestore · `gemini-embedding-001` (RAG) · MCP (Calendar, Gmail).

---

## ⚠️ Disclaimer

Mon Parcours Santé is an **administrative** assistant, not a medical device. It does **not** diagnose, interpret results, or advise on treatment — always consult a healthcare professional. In an emergency, call **15** or **112** (France), or **3114** for psychological distress. This is a personal/educational project; all demo data in this repository is **fictional**.

## Privacy

The agent stores only what you give it, keeps the **birth year** (not the full date of birth), and never infers medical facts. Never commit your real `.env`, tokens, or personal database — see `.gitignore`.

## License

MIT — see [`LICENSE`](LICENSE).

*Built during the 5-Day AI Agents Intensive (Google × Kaggle).*
