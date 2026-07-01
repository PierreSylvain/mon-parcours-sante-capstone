#!/bin/bash
uv run python -c "from mon_parcours_sante.store import HealthStore; s=HealthStore(); c=getattr(s,'conn',None) or getattr(s,'_conn'); c.execute('DELETE FROM documents'); c.execute('DELETE FROM lab_values'); c.commit(); print('base vidée')"
