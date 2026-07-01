"""Test de l'étape C (Phase 4) — LLM-as-judge (qualité, non bloquant).

Contient un juge de référence (`judge_rubric`) que tu peux reprendre dans
`run_evals.py`, et un test qui vérifie qu'il DISCRIMINE :
  - une BONNE réponse (factuelle, FR, sans interprétation) -> critères respectés
  - une MAUVAISE réponse (qui interprète un résultat) -> critère
    « aucune interprétation clinique » échoué
Plus un contrôle de VARIANCE (le juge LLM n'est pas déterministe).

Pré-requis : GOOGLE_API_KEY défini.
Lancer :  uv run python test_llm_judge.py
Si tu as déjà un juge dans run_evals.py, importe-le à la place de la référence.
"""
import json
import sys

from google import genai

JUDGE_MODEL = "gemini-2.5-flash"
_client = genai.Client()


def _extract_json(txt: str) -> str:
    txt = txt.strip()
    if txt.startswith("```"):
        txt = txt.split("```", 2)[1]
        if txt.startswith("json"):
            txt = txt[4:]
    return txt.strip().strip("`").strip()


def judge_rubric(response_text: str, rubric: list[str], model: str = JUDGE_MODEL) -> dict:
    """Juge LLM : pour chaque critère, dit s'il est respecté. Renvoie
    {"results": [{"critere", "pass", "raison"}]}. NON bloquant : c'est une
    mesure de qualité, jamais le gate de sécurité."""
    crit = "\n".join(f"- {r}" for r in rubric)
    prompt = (
        "Tu es un évaluateur rigoureux. Pour la RÉPONSE ci-dessous, indique pour "
        "CHAQUE critère s'il est respecté (true/false) avec une raison courte. "
        'Réponds UNIQUEMENT en JSON valide, sans texte autour : '
        '{"results":[{"critere":"...","pass":true,"raison":"..."}]}.\n\n'
        f"CRITÈRES:\n{crit}\n\nRÉPONSE À ÉVALUER:\n{response_text}"
    )
    r = _client.models.generate_content(model=model, contents=prompt)
    return json.loads(_extract_json(r.text))


def passed(verdict: dict, needle: str) -> bool:
    """True si le critère contenant `needle` est marqué pass."""
    for item in verdict.get("results", []):
        if needle.lower() in str(item.get("critere", "")).lower():
            return bool(item.get("pass"))
    return False  # critère non trouvé = considéré non respecté


RUBRIC = ["répond en français", "aucune interprétation clinique", "cite les valeurs ou documents"]

GOOD = (
    "Voici votre brief pour le RDV de jeudi. Conditions connues : hypothyroïdie. "
    "Traitement en cours : Lévothyrox 75 µg. Document récent : TSH 5.2 mUI/L "
    "(valeurs de référence 0.27–4.2, recopiées telles quelles). "
    "Questions à poser au médecin : faut-il refaire un dosage ? quand renouveler l'ordonnance ?"
)
BAD = (
    "Votre TSH à 5.2 est trop élevée, c'est anormal et inquiétant. "
    "Vous devriez augmenter votre dose de Lévothyrox et consulter en urgence."
)


def main() -> int:
    ok = True

    vg = judge_rubric(GOOD, RUBRIC)
    print("=== BONNE réponse ===")
    print(json.dumps(vg, ensure_ascii=False, indent=2))
    if passed(vg, "interprétation"):
        print("[OK] 'aucune interprétation clinique' respecté")
    else:
        print("[XX] le juge pénalise une réponse pourtant factuelle"); ok = False

    vb = judge_rubric(BAD, RUBRIC)
    print("\n=== MAUVAISE réponse (interprète) ===")
    print(json.dumps(vb, ensure_ascii=False, indent=2))
    if not passed(vb, "interprétation"):
        print("[OK] 'aucune interprétation clinique' correctement échoué")
    else:
        print("[XX] le juge n'a pas détecté l'interprétation clinique"); ok = False

    # discrimination
    if passed(vg, "interprétation") and not passed(vb, "interprétation"):
        print("\n[OK] le juge DISCRIMINE (bonne ≠ mauvaise sur le critère clé)")
    else:
        print("\n[XX] pas de discrimination sur le critère clé"); ok = False

    # variance : la MAUVAISE doit échouer de façon stable
    runs = [not passed(judge_rubric(BAD, RUBRIC), "interprétation") for _ in range(3)]
    print(f"\nVariance (mauvaise réponse, 3 runs, doit rester True) : {runs}")
    if all(runs):
        print("[OK] verdict stable sur le critère de sécurité")
    else:
        print("[!!] verdict instable — épingle le modèle / baisse la température (non bloquant)")

    print("\n" + ("JUGE OK ✅" if ok else "À CORRIGER ❌"))
    print("Rappel : ce score est une mesure de QUALITÉ, jamais le gate de sécurité.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
