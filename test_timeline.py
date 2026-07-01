"""Test de l'étape C — timeline d'un marqueur (skill document-management).

Vérifie la SOURCE DE DONNÉES de la timeline (le tool marker_timeline s'il existe,
sinon directement lab_values) : 3 points, ordre chronologique, plages recopiées
telles quelles, AUCUNE interprétation (ni jugement, ni 'tendance').

Pré-requis : avoir ingéré les 3 bilans TSH (voir commandes plus bas).
Lancer :  uv run python test_timeline.py
"""
import json
import sys

from mon_parcours_sante.store import HealthStore

# Mots interdits : jugement clinique ET interprétation d'évolution.
FORBIDDEN = ["anormal", "trop élevé", "élevé", "trop bas", "abnormal", "high", "low",
             "inquiétant", "en hausse", "en baisse", "tendance", "amélior", "aggrav"]


def get_timeline(marker: str = "TSH"):
    # 1) tool déterministe si présent
    try:
        from mon_parcours_sante import tools as T
        if hasattr(T, "marker_timeline"):
            res = T.marker_timeline(marker)
            items = res.get("timeline", res) if isinstance(res, dict) else res
            return [dict(x) for x in items], "tool marker_timeline"
    except Exception as e:
        print(f"[i] marker_timeline indisponible ({e}), fallback SQL")
    # 2) fallback : lab_values
    s = HealthStore()
    c = getattr(s, "conn", None) or getattr(s, "_conn")
    rows = c.execute(
        "SELECT value, unit, reference_range, date FROM lab_values "
        "WHERE upper(marker) LIKE 'TSH%' ORDER BY date"
    ).fetchall()
    return [dict(r) for r in rows], "SQL lab_values"


def main() -> int:
    tl, via = get_timeline("TSH")
    print(f"timeline TSH (via {via}) :")
    for p in tl:
        print("   ", p)

    ok = True
    dates = [str(p.get("date")) for p in tl]

    # points distincts
    if len(set(dates)) >= 3:
        print(f"[OK] {len(set(dates))} dates distinctes")
    else:
        print(f"[XX] seulement {len(set(dates))} date(s) — ingère bien les 3 bilans"); ok = False

    # ordre chronologique (sur l'ordre RENVOYÉ)
    if dates == sorted(dates):
        print("[OK] renvoyé en ordre chronologique")
    else:
        print("[XX] pas dans l'ordre chronologique"); ok = False

    # plage de référence recopiée verbatim sur chaque point
    if tl and all("0.27" in str(p.get("reference_range", "")) and "4.2" in str(p.get("reference_range", "")) for p in tl):
        print("[OK] plage de référence 0.27-4.2 recopiée sur chaque point")
    else:
        print("[XX] plage de référence absente/altérée sur au moins un point"); ok = False

    # aucune interprétation
    blob = json.dumps(tl, ensure_ascii=False, default=str).lower()
    leaked = [w for w in FORBIDDEN if w in blob]
    if leaked:
        print(f"[XX] interprétation/jugement détecté (interdit) : {leaked}"); ok = False
    else:
        print("[OK] données brutes, aucune interprétation ni 'tendance'")

    print("\n" + ("TIMELINE OK ✅" if ok else "À CORRIGER ❌"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
