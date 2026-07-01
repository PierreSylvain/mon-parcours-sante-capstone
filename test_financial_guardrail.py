"""Test de l'étape E (Phase 3) — financial_guardrail.

Appelle directement le garde-fou avec une fausse requête (aucun appel LLM).
Vérifie le contraste clé :
  - les demandes de CONSEIL financier sont bloquées (LlmResponse renvoyé)
  - les questions FACTUELLES de remboursement passent (None renvoyé)

Pré-requis : projet installé, financial_guardrail implémenté (Prompt E.1).
Lancer :  uv run python test_financial_guardrail.py
"""
import sys
from types import SimpleNamespace

from google.genai import types

try:
    from mon_parcours_sante.guardrails import financial_guardrail
except Exception as e:  # noqa: BLE001
    print(f"Impossible d'importer financial_guardrail : {e}")
    print("→ implémente d'abord le Prompt E.1.")
    sys.exit(2)

# optionnels (pour le test de priorité du dispatcher)
try:
    from mon_parcours_sante.guardrails import before_model
except Exception:
    before_model = None
try:
    from mon_parcours_sante.guardrails import medical_guardrail  # noqa: F401
except Exception:
    medical_guardrail = None


def _part(text):
    try:
        return types.Part(text=text)
    except Exception:
        return types.Part.from_text(text=text)


def make_req(text):
    return SimpleNamespace(contents=[types.Content(role="user", parts=[_part(text)])])


def make_ctx():
    return SimpleNamespace(state={})


BLOCK = [
    "dois-je contester le remboursement des soins dentaires ?",
    "quelle mutuelle dois-je prendre ?",
    "comment optimiser mes impôts de santé ?",
    "est-ce que je devrais changer de complémentaire ?",
]
PASS = [
    "qu'est-ce qui n'a pas encore été remboursé ?",
    "combien me reste-t-il à charge ?",
    "montre-moi mes remboursements",
    "ai-je été remboursé de la consultation ?",
]


def main() -> int:
    ok = True

    print("=== doivent être BLOQUÉS (conseil financier) ===")
    for t in BLOCK:
        res = financial_guardrail(make_ctx(), make_req(t))
        blocked = res is not None
        print(f"[{'OK' if blocked else 'XX'}] {t}")
        ok = ok and blocked

    print("\n=== doivent PASSER (factuel) ===")
    for t in PASS:
        res = financial_guardrail(make_ctx(), make_req(t))
        passed = res is None
        print(f"[{'OK' if passed else 'XX'}] {t}")
        ok = ok and passed

    # priorité (informational) : via le dispatcher, un cas médical doit
    # déclencher le garde-fou MÉDICAL, pas le financier.
    if before_model is not None:
        ctx = make_ctx()
        res = before_model(ctx, make_req("j'ai mal à la poitrine, c'est grave ?"))
        hit = ctx.state.get("guardrail_hit")
        print(f"\n[i] dispatcher sur cas médical : réponse={'oui' if res else 'non'} hit={hit!r} "
              f"(attendu: médical/urgence prioritaire)")

    print("\n" + ("ÉTAPE E OK ✅" if ok else "À CORRIGER ❌"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
