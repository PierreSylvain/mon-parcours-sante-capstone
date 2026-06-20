---
name: consultation-prep
description: preparation of medical consultations. Triggers on phrases like "RDV", "prépare-moi", or when a provider and a future date are mentioned.
---

# Consultation Prep Skill

## When to use
Use this skill when the user asks to prepare for an upcoming medical consultation, mentions an upcoming appointment (RDV), or says "prépare-moi". 

## Steps
1. Call `health_profile_get` to retrieve the user's base medical profile, current conditions, allergies, and medications.
2. Call `search_documents` with relevant keywords to find recent lab results or reports matching the reason for the visit or the provider's specialty.
3. Select the most relevant history for *this specific reason*.
4. Render a one-page brief using `assets/brief_template.md`.
5. Propose a targeted list of questions using `references/what-to-ask.md` as inspiration.

## HARD Boundaries (NON-NEGOTIABLE)
- **No Interpretation**: You must never clinically interpret a result or offer a diagnosis.
- **Reference Ranges**: Copying a reference range already printed on a document is OK. Judging a value as "too high", "anormal", or "bad" is FORBIDDEN.
- **Action limits**: Do NOT create or modify the appointment (this skill is for preparation only). Do NOT formulate anxiety-inducing questions.
