"""Validation de l'evalset fonctionnel (Phase 4, étape A).

Ne lance PAS l'agent : il valide les DONNÉES que tu as rédigées.
  - structure : chaque cas a input, expected_skill, outils attendus, rubric
  - couverture : >= 8 cas par skill, les 4 skills présents
  - noms valides : expected_skill et outils référencés existent
  - diversité : repère les formulations quasi-dupliquées (sinon l'éval
    d'activation ne veut rien dire)

Lancer :  uv run python validate_evalset.py
(ou: python validate_evalset.py — aucune dépendance externe)
"""
import glob
import json
import sys
from collections import defaultdict
from itertools import combinations

SKILLS = {
    "consultation-prep", "document-management",
    "medication-tracking", "reimbursement-tracking",
}
TOOLS = {
    "list_skills", "load_skill", "load_skill_resource",
    "health_profile_get", "health_profile_update", "search_documents",
    "parse_lab_pdf", "index_document", "marker_timeline",
    "upcoming_renewals", "reimbursement_add", "reimbursement_summary",
}
MIN_PER_SKILL = 8
DUP_THRESHOLD = 0.85  # Jaccard sur les mots -> quasi-doublon


def field(c, *names):
    for n in names:
        if isinstance(c, dict) and n in c and c[n] not in (None, "", []):
            return c[n]
    return None


def tool_names(c):
    raw = field(c, "expected_tool_use", "expected_tool_calls") or []
    out = []
    for t in raw:
        if isinstance(t, dict):
            out.append(t.get("tool") or t.get("name") or "")
        else:
            out.append(str(t))
    return [t for t in out if t]


def words(txt):
    norm = "".join(ch.lower() if (ch.isalnum() or ch.isspace()) else " " for ch in (txt or ""))
    return set(norm.split())


def jaccard(a, b):
    return len(a & b) / len(a | b) if (a or b) else 0.0


def load_cases():
    cases = []
    files = glob.glob("evals/functional/**/*.json", recursive=True) or \
        glob.glob("evals/functional/*.json")
    for f in files:
        try:
            data = json.load(open(f, encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            print(f"[XX] JSON invalide : {f} ({e})")
            continue
        items = data.get("cases", data) if isinstance(data, dict) else data
        for c in (items or []):
            if isinstance(c, dict):
                c["_file"] = f
                cases.append(c)
    return cases, files


def main() -> int:
    cases, files = load_cases()
    print(f"Fichiers: {len(files)} | cas chargés: {len(cases)}\n")
    if not cases:
        print("[XX] aucun cas dans evals/functional/ — crée d'abord les fichiers.")
        return 1

    ok = True
    by_skill = defaultdict(list)

    # 1) structure + noms valides
    for c in cases:
        cid = field(c, "case_id", "id") or "(sans id)"
        inp = field(c, "input", "query")
        skill = field(c, "expected_skill")
        tools = tool_names(c)
        rubric = field(c, "rubric")
        problems = []
        if not inp:
            problems.append("input manquant")
        if not skill:
            problems.append("expected_skill manquant")
        elif skill not in SKILLS:
            problems.append(f"skill inconnu '{skill}'")
        if not tools:
            problems.append("expected_tool_use/_calls manquant")
        else:
            unknown = [t for t in tools if t not in TOOLS]
            if unknown:
                problems.append(f"outil(s) inconnu(s) {unknown} (warning)")
        if not rubric:
            problems.append("rubric manquante")
        if problems:
            hard = [p for p in problems if "warning" not in p]
            if hard:
                ok = False
            print(f"[{'XX' if hard else '!!'}] {cid} ({c['_file']}): {', '.join(problems)}")
        if skill:
            by_skill[skill].append(inp or "")

    # 2) couverture
    print("\n=== Couverture par skill ===")
    for s in sorted(SKILLS):
        n = len(by_skill.get(s, []))
        good = n >= MIN_PER_SKILL
        ok = ok and good
        print(f"[{'OK' if good else 'XX'}] {s:24} {n} cas (min {MIN_PER_SKILL})")

    # 3) diversité (quasi-doublons par skill)
    print("\n=== Diversité (quasi-doublons) ===")
    dupes = 0
    for s, inputs in by_skill.items():
        wsets = [(i, words(i)) for i in inputs]
        for (a, wa), (b, wb) in combinations(wsets, 2):
            if jaccard(wa, wb) >= DUP_THRESHOLD:
                dupes += 1
                print(f"[!!] {s}: trop proches\n     - {a}\n     - {b}")
    if dupes == 0:
        print("[OK] aucune paire quasi-dupliquée détectée")

    print("\n" + ("EVALSET VALIDE ✅" if ok else "EVALSET À CORRIGER ❌"))
    if dupes:
        print(f"(+ {dupes} paire(s) trop proches : varie les formulations pour l'éval d'activation)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
