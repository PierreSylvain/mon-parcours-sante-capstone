"""Test de l'étape A (Phase 3) — upcoming_renewals.

Sème 4 médicaments avec des dates RELATIVES à aujourd'hui (donc déterministe),
puis vérifie le classement :
  - renouvellement passé      -> overdue
  - renouvellement dans 15 j  -> due (seuil 30 j)
  - renouvellement dans 90 j  -> ni l'un ni l'autre à 30 j (mais due à 120 j)
  - sans date                 -> ignoré, pas de crash
Vérifie aussi qu'aucun conseil n'est émis.

Pré-requis : projet installé (uv pip install -e .).
Lancer :  uv run python test_upcoming_renewals.py
Adapte l'import si ta fonction porte un autre nom.
"""
import json
import sys
from datetime import date, timedelta

from mon_parcours_sante.tools import upcoming_renewals
from mon_parcours_sante.store import HealthStore

ADVICE = ["arrêt", "n'arrête", "conseil", "augment", "diminu", "posologie", "dose recommand", "vous devriez"]

MEDS = [
    ("Lévothyrox",  (date.today() - timedelta(days=10)).isoformat()),   # overdue
    ("Vitamine D",  (date.today() + timedelta(days=15)).isoformat()),   # due (<=30)
    ("Magnésium",   (date.today() + timedelta(days=90)).isoformat()),   # far (>30)
    ("Doliprane",   None),                                              # sans date
]


def seed():
    s = HealthStore()
    c = getattr(s, "conn", None) or getattr(s, "_conn")
    c.execute("DELETE FROM medications")
    for name, renewal in MEDS:
        c.execute(
            "INSERT INTO medications (name, dose, schedule, renewal_date) VALUES (?, ?, ?, ?)",
            (name, "1cp", "1/jour", renewal),
        )
    c.commit()


def _names(section):
    out = []
    if isinstance(section, list):
        for x in section:
            out.append((x.get("name") or x.get("medication") or "").lower()
                       if isinstance(x, dict) else str(x).lower())
    return out


def classify(result, med_name):
    """-> 'overdue' | 'due' | 'absent', tolérant à la forme du retour."""
    med = med_name.lower()
    if isinstance(result, dict):
        overdue = result.get("overdue") or result.get("late") or []
        due = result.get("due") or result.get("upcoming") or []
        if med in _names(overdue):
            return "overdue"
        if med in _names(due):
            return "due"
        for key in ("renewals", "medications", "results", "items"):
            lst = result.get(key)
            if isinstance(lst, list):
                for x in lst:
                    if isinstance(x, dict) and (x.get("name", "").lower() == med):
                        st = str(x.get("status", "")).lower()
                        days = x.get("days_until", x.get("days"))
                        if "overdue" in st or "retard" in st or (isinstance(days, (int, float)) and days < 0):
                            return "overdue"
                        return "due"
    return "absent"


def main() -> int:
    seed()
    res = upcoming_renewals(within_days=30)
    print("upcoming_renewals(30) =")
    print(json.dumps(res, ensure_ascii=False, indent=2, default=str))

    ok = True
    expected = {"Lévothyrox": "overdue", "Vitamine D": "due", "Magnésium": "absent", "Doliprane": "absent"}
    for med, exp in expected.items():
        got = classify(res, med)
        flag = "OK" if got == exp else "XX"
        if got != exp:
            ok = False
        print(f"[{flag}] {med:12} attendu={exp:8} obtenu={got}")

    # seuil within_days : à 120 j, Magnésium (J+90) doit passer en 'due'
    res2 = upcoming_renewals(within_days=120)
    if classify(res2, "Magnésium") == "due":
        print("[OK] seuil within_days respecté (Magnésium due à 120 j)")
    else:
        print("[XX] within_days ne décale pas le seuil"); ok = False

    # aucun conseil
    blob = json.dumps(res, ensure_ascii=False, default=str).lower()
    leaked = [w for w in ADVICE if w in blob]
    if leaked:
        print(f"[XX] conseil détecté (interdit) : {leaked}"); ok = False
    else:
        print("[OK] données brutes, aucun conseil de traitement")

    print("\n" + ("ÉTAPE A OK ✅" if ok else "À CORRIGER ❌"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
