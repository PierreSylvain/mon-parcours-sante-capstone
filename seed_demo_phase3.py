"""Seed de démo pour la Phase 3 (étape D) — données réalistes pour `adk web`.

Peuple :
  - des remboursements variés (soldés / en attente récents / anciens = 'missing')
  - quelques médicaments avec des échéances échelonnées (bonus medication-tracking)
Dates RELATIVES à aujourd'hui -> le seuil 'missing' (>30 j) reste valable quel
que soit le jour où tu lances.

Lancer :  uv run python seed_demo_phase3.py
Adapte les imports si tes fonctions portent d'autres noms.
"""
import json
from datetime import date, timedelta

from mon_parcours_sante.tools import reimbursement_add, reimbursement_summary
from mon_parcours_sante.store import HealthStore


def d(days_ago: int) -> str:
    return (date.today() - timedelta(days=days_ago)).isoformat()


# (care_event, jours_passés, payé, secu, mutuelle)
REIMBURSEMENTS = [
    ("Consultation médecin généraliste",      3,  30.0, 21.0,  9.0),   # soldé
    ("Consultation cardiologue",              5,  60.0, 42.0, 18.0),   # soldé
    ("Pharmacie (Lévothyrox)",               12,  10.0,  7.0,  3.0),   # soldé
    ("Séance de kinésithérapie",              8,  50.0, 20.0,  0.0),   # en attente (récent)
    ("Analyses biologiques (laboratoire)",   40,  45.0, 27.0,  0.0),   # en attente ancien -> missing
    ("Soins dentaires (couronne)",           50, 500.0, 84.0, 200.0),  # en attente ancien -> missing
    ("Optique (lunettes)",                   60, 250.0,  0.0, 100.0),  # en attente ancien -> missing
]

# (nom, dose, schéma, jours avant/après renouvellement)
MEDICATIONS = [
    ("Lévothyrox",  "75 µg",  "1/jour le matin",  +10),   # à renouveler bientôt
    ("Vitamine D",  "1 amp",  "1/mois",           +25),   # à renouveler ce mois
    ("Magnésium",   "300 mg", "1/jour",            -5),   # renouvellement dépassé
    ("Doliprane",   "1000 mg","si besoin",       None),   # sans échéance
]


def main() -> None:
    s = HealthStore()
    c = getattr(s, "conn", None) or getattr(s, "_conn")

    # reset des deux tables (données fictives)
    c.execute("DELETE FROM reimbursements")
    c.execute("DELETE FROM medications")
    c.commit()

    # remboursements via le tool (calcul remaining/status par ton implémentation)
    for ev, days, paid, secu, mut in REIMBURSEMENTS:
        reimbursement_add(ev, d(days), paid, secu_reimbursed=secu, mutuelle_reimbursed=mut)

    # médicaments (insertion directe ; pas de tool d'écriture dédié)
    for name, dose, sched, offset in MEDICATIONS:
        renewal = None if offset is None else (date.today() + timedelta(days=offset)).isoformat()
        c.execute(
            "INSERT INTO medications (name, dose, schedule, prescriber, renewal_date) "
            "VALUES (?, ?, ?, ?, ?)",
            (name, dose, sched, "Dr Martin", renewal),
        )
    c.commit()

    # aperçu de ce que l'agent devra restituer
    print("=== Remboursements semés ===")
    for r in c.execute("SELECT care_event, date, paid, remaining, status FROM reimbursements ORDER BY date"):
        print(f"  {r['date']}  {r['care_event']:38} payé={r['paid']:>6}  reste={r['remaining']:>6}  [{r['status']}]")

    print("\n=== reimbursement_summary() (ce que le skill doit présenter) ===")
    print(json.dumps(reimbursement_summary(), ensure_ascii=False, indent=2, default=str))

    print("\n=== Médicaments semés ===")
    for m in c.execute("SELECT name, dose, renewal_date FROM medications ORDER BY renewal_date IS NULL, renewal_date"):
        print(f"  {m['name']:12} {m['dose']:8} renouvellement={m['renewal_date']}")

    print("\nSeed terminé. Lance `uv run adk web` pour tester le skill.")


if __name__ == "__main__":
    main()
