"""Test de l'étape C (Phase 3) — reimbursement_ledger.

Sème 3 événements de remboursement (dates relatives à aujourd'hui), vérifie :
  - reimbursement_add calcule remaining = paid - secu - mutuelle, et le status
  - reimbursement_summary agrège les totaux
  - pending = tous les 'en attente' ; missing = 'en attente' datés de > 30 j
  - aucune sortie de conseil financier (restituer, pas conseiller)

Pré-requis : projet installé (uv pip install -e .).
Lancer :  uv run python test_reimbursement.py
Adapte les imports si tes fonctions portent d'autres noms.
"""
import json
import sys
from datetime import date, timedelta

from mon_parcours_sante.tools import reimbursement_add, reimbursement_summary
from mon_parcours_sante.store import HealthStore

ADVICE = ["contest", "changez de mutuelle", "vous devriez", "conseil", "optimis", "déclarez", "réclamez"]

# (care_event, jours_dans_le_passé, paid, secu, mutuelle, attendu_remaining, attendu_status_contient, attendu_missing)
EVENTS = [
    ("consultation généraliste",  5, 30.0, 24.5, 5.5,  0.0,  "rembours", False),  # soldé
    ("séance kiné",              10, 50.0, 20.0, 0.0, 30.0,  "attente",  False),  # pending récent
    ("soins dentaires",          45, 80.0,  0.0, 0.0, 80.0,  "attente",  True),   # pending ancien -> missing
]


def reset_and_seed():
    s = HealthStore()
    c = getattr(s, "conn", None) or getattr(s, "_conn")
    c.execute("DELETE FROM reimbursements")
    c.commit()
    for ev, days, paid, secu, mut, *_ in EVENTS:
        d = (date.today() - timedelta(days=days)).isoformat()
        reimbursement_add(ev, d, paid, secu_reimbursed=secu, mutuelle_reimbursed=mut)
    return c


def almost(a, b, tol=0.01):
    try:
        return abs(float(a) - float(b)) < tol
    except (TypeError, ValueError):
        return False


def _events(section):
    out = []
    if isinstance(section, list):
        for x in section:
            out.append((x.get("care_event") or x.get("event") or x.get("label") or "").lower()
                       if isinstance(x, dict) else str(x).lower())
    return out


def _total(summary, *keys):
    src = summary.get("totals", summary) if isinstance(summary, dict) else {}
    for k in keys:
        if isinstance(src, dict) and k in src:
            return src[k]
    return None


def main() -> int:
    conn = reset_and_seed()
    ok = True

    # 1) reimbursement_add : remaining + status calculés en base
    print("=== vérif des lignes (calcul de reimbursement_add) ===")
    for ev, days, paid, secu, mut, exp_rem, exp_status, _ in EVENTS:
        row = conn.execute(
            "SELECT remaining, status FROM reimbursements WHERE care_event = ?", (ev,)
        ).fetchone()
        if row is None:
            print(f"[XX] {ev} absent en base"); ok = False; continue
        rem, status = row["remaining"], (row["status"] or "").lower()
        rem_ok = almost(rem, exp_rem)
        st_ok = exp_status in status
        print(f"[{'OK' if rem_ok and st_ok else 'XX'}] {ev:26} remaining={rem} (att.{exp_rem}) status={status!r}")
        ok = ok and rem_ok and st_ok

    # 2) reimbursement_summary
    summary = reimbursement_summary()
    print("\n=== reimbursement_summary() ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))

    checks = {
        "paid (160)":      almost(_total(summary, "paid", "total_paid", "paye"), 160.0),
        "secu (44.5)":     almost(_total(summary, "secu", "secu_reimbursed", "total_secu"), 44.5),
        "mutuelle (5.5)":  almost(_total(summary, "mutuelle", "mutuelle_reimbursed", "total_mutuelle"), 5.5),
        "remaining (110)": almost(_total(summary, "remaining", "reste", "total_remaining"), 110.0),
    }
    for label, good in checks.items():
        print(f"[{'OK' if good else 'XX'}] total {label}")
        ok = ok and good

    pending = _events(summary.get("pending") if isinstance(summary, dict) else [])
    missing = _events(summary.get("missing") if isinstance(summary, dict) else [])

    if any("kiné" in p for p in pending) and any("dentaire" in p for p in pending):
        print("[OK] pending contient les 2 'en attente'")
    else:
        print(f"[XX] pending incomplet : {pending}"); ok = False

    if any("dentaire" in m for m in missing) and not any("kiné" in m for m in missing):
        print("[OK] missing = seulement l'ancien (>30 j)")
    else:
        print(f"[XX] missing incorrect : {missing}"); ok = False

    # 3) aucun conseil financier
    blob = json.dumps(summary, ensure_ascii=False, default=str).lower()
    leaked = [w for w in ADVICE if w in blob]
    if leaked:
        print(f"[XX] conseil financier détecté (interdit) : {leaked}"); ok = False
    else:
        print("[OK] chiffres bruts, aucun conseil financier")

    print("\n" + ("ÉTAPE C OK ✅" if ok else "À CORRIGER ❌"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
