"""Validation de la suite SÉCURITÉ (Phase 4, étape D) — couverture des catégories.

Ne lance pas l'agent : vérifie que le "sujet d'examen" sécurité est complet et
bien formé, AVANT de faire tourner le gate déterministe à k élevé.
  - les 7 catégories sont présentes (>= 1 cas chacune)
  - chaque cas a un input, un critère déterministe et une rubric

Lancer :  python validate_security_suite.py
"""
import glob
import json
import sys
from collections import defaultdict

# Catégorie canonique -> mots-clés (cherchés dans `category` ou `case_id`/`input`)
CATEGORIES = {
    "urgence":               ["emergency", "urgence", "_a_", "poitrine", "suicid"],
    "interprétation":        ["interpret", "result_interp", "_b_", "tsh", "normal"],
    "modif. traitement":     ["treatment", "traitement", "dose", "_c_"],
    "conseil financier":     ["financial", "financ", "mutuelle", "contester"],
    "injection document":    ["pdf", "injection_doc", "document", "_d_"],
    "injection mail":        ["mail", "email", "_e_"],
    "écriture non confirmée": ["write", "confirm", "unconfirmed", "_f_"],
}


def field(c, *names):
    for n in names:
        if isinstance(c, dict) and c.get(n) not in (None, "", []):
            return c[n]
    return None


def classify(c) -> set:
    hay = " ".join(str(c.get(k, "")) for k in ("category", "case_id", "id", "input")).lower()
    return {cat for cat, kws in CATEGORIES.items() if any(k in hay for k in kws)}


def load_cases():
    cases, files = [], glob.glob("evals/security/**/*.json", recursive=True) or \
        glob.glob("evals/security/*.json")
    for f in files:
        try:
            data = json.load(open(f, encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            print(f"[XX] JSON invalide : {f} ({e})")
            continue
        items = data.get("cases", data) if isinstance(data, dict) else data
        for c in (items or []):
            if isinstance(c, dict):
                cases.append(c)
    return cases, files


def main() -> int:
    cases, files = load_cases()
    print(f"Fichiers: {len(files)} | cas sécurité: {len(cases)}\n")
    if not cases:
        print("[XX] aucun cas dans evals/security/ — crée d'abord la suite.")
        return 1

    ok = True
    coverage = defaultdict(int)

    # structure + classification
    for c in cases:
        cid = field(c, "case_id", "id") or "(sans id)"
        problems = []
        if not field(c, "input", "query"):
            problems.append("input manquant")
        if not field(c, "deterministic_pass", "expected", "expected_behavior", "gate"):
            problems.append("critère déterministe manquant")
        if not field(c, "rubric"):
            problems.append("rubric manquante")
        cats = classify(c)
        if not cats:
            problems.append("catégorie non reconnue (ajoute un champ `category`)")
        for cat in cats:
            coverage[cat] += 1
        if problems:
            ok = False
            print(f"[XX] {cid}: {', '.join(problems)}")

    # couverture des 7 catégories
    print("\n=== Couverture des catégories ===")
    for cat in CATEGORIES:
        n = coverage.get(cat, 0)
        good = n >= 1
        ok = ok and good
        print(f"[{'OK' if good else 'XX'}] {cat:24} {n} cas")

    print("\n" + ("SUITE SÉCURITÉ COMPLÈTE ✅" if ok else "COUVERTURE INCOMPLÈTE ❌"))
    if ok:
        print("→ lance le gate déterministe à k=10 (voir commande).")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
