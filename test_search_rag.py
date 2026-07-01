"""Test de l'étape B — RAG (index_document + search_documents sémantique).

Idée : la recherche doit retrouver un document PAR LE SENS, sans mot en commun,
et DISCRIMINER entre deux documents distincts. On ingère donc deux bilans
(thyroïdien + lipidique), on les indexe, puis on interroge avec des requêtes
sans recouvrement lexical.

Pré-requis :
  - GOOGLE_API_KEY défini (index_document ET search_documents appellent les embeddings)
  - projet installé (uv pip install -e .)
  - sample_bilan.pdf et sample_bilan_lipidique.pdf à la racine du projet

Lancer :  uv run python test_search_rag.py
Adapte les imports si tes fonctions/modules ont d'autres noms.
"""
import json
import sys

from mon_parcours_sante.tools import parse_lab_pdf, index_document, search_documents
from mon_parcours_sante.store import HealthStore


def _as_list(res):
    """Normalise le retour de search_documents en liste de records, quelle que
    soit sa forme (liste nue, dict {results:[...]}, dict de records, etc.)."""
    if res is None:
        return []
    if isinstance(res, list):
        return res
    if isinstance(res, dict):
        for k in ("results", "documents", "matches", "items", "data", "hits"):
            v = res.get(k)
            if isinstance(v, list):
                return v
        vals = list(res.values())
        if vals and all(isinstance(x, dict) for x in vals):
            return vals          # dict de records keyés (par id par ex.)
        return [res]             # un seul record renvoyé tel quel
    return []


def _markers(record) -> list:
    """Extrait les noms de marqueurs d'un record, quelle que soit la forme de
    extracted_values (str JSON, dict {values:[...]}, dict {TSH:{...}}, liste)."""
    ev = record.get("extracted_values") if isinstance(record, dict) else None
    if isinstance(ev, str):
        try:
            ev = json.loads(ev)
        except Exception:
            return []
    if isinstance(ev, dict):
        if isinstance(ev.get("values"), list):
            ev = ev["values"]
        else:
            return [str(k).lower() for k in ev.keys()]
    out = []
    if isinstance(ev, list):
        for x in ev:
            out.append(str(x.get("marker", "")).lower() if isinstance(x, dict) else str(x).lower())
    return [m for m in out if m]


def _domain(record) -> str:
    """Domaine réel d'un document, déduit de ses marqueurs (source de vérité)."""
    ms = " ".join(_markers(record))
    if any(t in ms for t in ("tsh", "t4", "t3")):
        return "thyro"
    if any(l in ms for l in ("cholest", "ldl", "hdl", "triglyc")):
        return "lipid"
    return (record.get("type") or "").lower() if isinstance(record, dict) else ""


def top_type(query: str):
    """Renvoie le domaine du 1er résultat + affiche le détail du classement."""
    items = _as_list(search_documents(query))
    print(f"\nQ: {query}")
    if not items:
        print("   (aucun résultat)")
        return None, []
    for r in items:
        if isinstance(r, dict):
            print(f"   id={r.get('id')} score={r.get('score')} "
                  f"domain={_domain(r)} markers={_markers(r)} type={r.get('type')!r}")
    return _domain(items[0]), items


def main() -> int:
    store = HealthStore()
    conn = getattr(store, "conn", None) or getattr(store, "_conn", None)

    # 1) S'assurer d'avoir les 2 documents (check par CONTENU, pas par type)
    allev = " ".join(
        (r["extracted_values"] or "").lower()
        for r in conn.execute("SELECT extracted_values FROM documents")
    )
    if "tsh" not in allev:
        parse_lab_pdf("sample_bilan.pdf")
    if "cholest" not in allev and "ldl" not in allev:
        parse_lab_pdf("sample_bilan_lipidique.pdf")

    # 2) Indexer les documents sans vecteur
    for r in conn.execute("SELECT id, vector_ref FROM documents").fetchall():
        if not r["vector_ref"]:
            index_document(r["id"])
    indexed = conn.execute(
        "SELECT COUNT(*) c FROM documents WHERE vector_ref IS NOT NULL AND vector_ref != ''"
    ).fetchone()["c"]
    print(f"[i] documents indexés : {indexed}")
    if indexed < 2:
        print("[XX] moins de 2 documents indexés — index_document n'écrit pas vector_ref ?")
        return 1

    ok = True

    # 3) Sémantique SANS recouvrement lexical avec le document
    q1 = "hormones qui règlent le métabolisme"      # -> thyroïde (aucun mot partagé)
    t1, items1 = top_type(q1)
    if t1 and "thyro" in t1:
        print("[OK] requête 'hormones/métabolisme' -> bilan thyroïdien")
    else:
        print("[XX] n'a pas remonté le bilan thyroïdien en tête"); ok = False

    q2 = "graisses dans le sang et risque cardiovasculaire"   # -> lipidique
    t2, items2 = top_type(q2)
    if t2 and ("lipid" in t2 or "cholest" in t2):
        print("[OK] requête 'graisses/cardio' -> bilan lipidique")
    else:
        print("[XX] n'a pas remonté le bilan lipidique en tête"); ok = False

    # 4) Discrimination : deux requêtes opposées => deux tops différents
    if t1 and t2 and t1 != t2:
        print("\n[OK] la recherche DISCRIMINE (top différent selon le sens)")
    else:
        print("\n[XX] même top pour deux requêtes opposées -> pas de discrimination"); ok = False

    # 5) Contrat 'restituer != interpréter' : aucun jugement dans la sortie
    blob = json.dumps([items1, items2], ensure_ascii=False, default=str).lower()
    if any(w in blob for w in ["anormal", "trop élevé", "abnormal", "high"]):
        print("[XX] jugement clinique présent dans les résultats (interdit)"); ok = False
    else:
        print("[OK] résultats restitués sans interprétation")

    print("\n" + ("RAG OK ✅" if ok else "RAG À CORRIGER ❌"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())