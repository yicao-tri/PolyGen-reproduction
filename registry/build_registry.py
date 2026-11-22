#!/usr/bin/env python3
"""Rebuild the compact PolyGen evidence index; never run experiments or change sources."""
import csv
import hashlib
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / 'registry'
OUT = REG / 'output'
DB = OUT / 'polygen_evidence.sqlite'

def digest(data):
    return hashlib.sha256(data).hexdigest()

def build():
    OUT.mkdir(exist_ok=True)
    if DB.exists():
        DB.unlink()  # Derived index only. Original inputs remain immutable.
    cx = sqlite3.connect(DB)
    cx.executescript((REG / 'schema.sql').read_text())
    cx.executemany('INSERT INTO schema_meta VALUES (?,?)', [('schema_version','1'),('project','PolyGen reproduction'),('role','evidence_index_not_validated_results_master'),('snapshot_date','2026-11-21')])
    files = sorted(p for p in (ROOT/'evidence/gap-analysis-20261016').rglob('*') if p.is_file() and p.name != 'HANDOFF_COPY_MANIFEST.json')
    rows=[]
    for p in files:
        rel=p.relative_to(ROOT).as_posix(); raw=p.read_bytes(); h=digest(raw); sid='src:'+digest(rel.encode())[:20]
        data=[]
        if p.suffix=='.csv':
            with p.open(newline='') as f: data=list(csv.DictReader(f))
        cx.execute('INSERT INTO source_files VALUES (?,?,?,?,?,?,?,?)',(sid,'gap-analysis-20261016',rel,p.suffix,h,len(raw),len(data) if p.suffix=='.csv' else None,'ingest-v1'))
        tier='synthetic_planning' if 'SYNTHETIC' in p.name else 'dated_source_snapshot'
        cx.execute('INSERT INTO asset_registry VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(sid,'evidence_snapshot',rel,'repository',len(raw),h,'present','hash_verified','retain',sid,tier,'No scientific promotion; source interpretation applies'))
        if p.parent.name=='tables':
            for i,row in enumerate(data,1):
                t='engineering_only' if p.name.startswith(('T12_','T13_','T14_')) else 'planned_not_run' if p.name.startswith(('T4_','T6_')) else 'prediction_or_audit_only'
                cx.execute('INSERT INTO tabular_evidence VALUES (?,?,?,?,?)',(sid,i,p.name,t,json.dumps(row,sort_keys=True)))
        rows.append([rel,h,len(raw)])
    claims=[
      ('prediction','Prediction benchmark and Q80 locked-tail audits','observed_prediction_only','evidence/gap-analysis-20261016/assets/tables/T3_locked_tail_verifier_bins.csv','Supports verifier-limit diagnosis, not physical failure'),
      ('physical','Candidate physical validation','NO_GO_PLANNED_NOT_RUN','evidence/gap-analysis-20261016/evidence/data/pcff_plus_bundle_audit/pcff_plus_bundle_audit.json','No candidate-specific parameter bundle; no new MD'),
      ('pfp','Historical top-1 PFP pilot','NON_CONVERGED_SMOKE_ONLY','evidence/gap-analysis-20261016/FINAL_READINESS_AUDIT.md','Missing trajectories; not physical confirmation'),
      ('molminer','Five-seed 5/20/50 epoch MolMiner','engineering_only','evidence/gap-analysis-20261016/STRICT_MOLMINER_SMOKE.md','Final same-support budget/checkpoint/Wee comparison incomplete'),
      ('f7f8','Representation and decision-value panels','synthetic_planning','evidence/gap-analysis-20261016/CLAIM_MAP.csv','Replace or remove before publication'),
      ('a4','Hisa code-review issues','isolated_patch_pending_canonical_review','evidence/gap-analysis-20261016/HISA_REVIEW_ACTIONS.md','Agent regression is not human sign-off'),
      ('ood','PI1M and structural OOD','incomplete','evidence/gap-analysis-20261016/TODO_AND_ACCEPTANCE.md','Sampled near-overlap and row-disjointness are insufficient')]
    cx.executemany('INSERT INTO claims VALUES (?,?,?,?,?)',claims)
    queries=[('gates','SELECT claim_id,status,evidence_path,interpretation_boundary FROM claims ORDER BY claim_id','Claim statuses from dated source material; not new results'),('sources','SELECT source_path,sha256,size_bytes,row_count FROM source_files ORDER BY source_path','Exact imported source snapshots; absent rows are unknown'),('tables','SELECT table_name,evidence_tier,count(*) AS n FROM tabular_evidence GROUP BY table_name,evidence_tier ORDER BY table_name','CSV rows, not independent scientific replicates')]
    results={}
    for q,sql,boundary in queries:
        cursor=cx.execute(sql); cols=[c[0] for c in cursor.description]; vals=cursor.fetchall()
        cx.execute('INSERT INTO query_catalog VALUES (?,?,?,?,?,?,?)',(q,q,'1',sql,json.dumps(cols),boundary,digest(sql.encode())))
        result={'columns':cols,'rows':vals}; blob=json.dumps(result,sort_keys=True,indent=2)+'\n';(OUT/(q+'.json')).write_text(blob);results[q]={'rows':len(vals),'sha256':digest(blob.encode())}
    for table, in cx.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
        for col in cx.execute('PRAGMA table_info('+table+')').fetchall():
            cx.execute('INSERT INTO data_dictionary VALUES (?,?,?,?,?,?,?)',(table,col[1],col[2],None,'See schema.sql and source interpretation boundary','source metadata or exact CSV text',0 if col[3] else 1))
    manifest_hash=digest(json.dumps(rows,sort_keys=True).encode())
    cx.execute('INSERT INTO ingest_runs VALUES (?,?,?,?,?,?,?)',('ingest-v1','2026-11-21','2026-11-21','1',manifest_hash,None,'complete'))
    cx.commit(); assert cx.execute('PRAGMA integrity_check').fetchone()[0]=='ok';cx.close()
    receipt={'role':'evidence_index_not_scientific_results_master','schema_version':1,'input_manifest_sha256':manifest_hash,'source_files':len(files),'database_sha256':digest(DB.read_bytes()),'query_results':results,'large_assets_manifest':'evidence/gap-analysis-20261016/HANDOFF_COPY_MANIFEST.json','build_command':'python3 registry/build_registry.py'}
    (OUT/'build_receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print(json.dumps(receipt,sort_keys=True))

if __name__=='__main__': build()
