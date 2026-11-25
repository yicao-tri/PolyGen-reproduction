#!/usr/bin/env python3
"""Append immutable paper records; rebuild a queryable derived SQLite. No experiment runner."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import tempfile

ROOT = Path(__file__).resolve().parents[2]
REG = Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def encode(value):
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)+'\n'

def read(path):
    def reject(value):
        raise ValueError('Non-finite JSON constant: '+value)
    return json.loads(path.read_text(), parse_constant=reject)

def relative_file(root, name):
    p=(root/name).resolve()
    if not p.is_relative_to(root.resolve()) or not p.is_file():
        raise ValueError('Source must be a real repository file: '+name)
    return p

def validate_sources(data, root):
    for x in data.get('source_files', []):
        p=relative_file(root,x['path'])
        if sha(p)!=x['sha256']:
            raise ValueError('Source SHA mismatch: '+x['path'])
        x['size_bytes']=p.stat().st_size

def build(root=ROOT, reg=REG, extra=None, publish=True):
    records=[]
    for path in sorted((reg/'records').glob('*.json')):
        records.append((path.name,read(path)))
    if extra is not None:
        records.append((extra['record_id']+'.json',extra))
    records.sort()
    out=reg/'output';out.mkdir(exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.paper-',suffix='.sqlite',dir=out);os.close(fd)
    cx=sqlite3.connect(tmp)
    try:
        cx.executescript((reg/'schema.sql').read_text())
        cx.executemany('INSERT INTO schema_meta VALUES (?,?)', [('version','1'),('role','paper_coordination_and_results_index_not_raw_science_master'),('legacy_registry','registry/output/polygen_evidence.sqlite (read-only; unchanged)')])
        observations=[]
        for name,data in records:
            validate_sources(data,root)
            rid=data['record_id']
            cx.execute('INSERT INTO ingest_runs VALUES (?,?,?)',(rid,data['recorded_at'],hashlib.sha256(encode(data).encode()).hexdigest()))
            for x in data.get('source_files',[]):
                cx.execute('INSERT INTO source_files VALUES (?,?,?,?,?)',(x['source_id'],x['path'],x['sha256'],x['size_bytes'],rid))
                cx.execute('INSERT INTO asset_registry VALUES (?,?,?,?,?)',(x['source_id'],x['source_id'],x['path'],'retain immutable input','sha256_verified'))
            for x in data.get('stages',[]):
                cx.execute('INSERT INTO stages VALUES (?,?,?,?)',(x['stage_id'],x['ordinal'],x['title'],x['acceptance']))
            for x in data.get('stage_events',[]):
                cx.execute('INSERT INTO stage_events VALUES (?,?,?,?,?,?,?,?)',(x['event_id'],x['sequence'],x['stage_id'],x['status'],x['acceptance_scope'],x['source_id'],x['note'],rid))
            for x in data.get('decisions',[]):
                cx.execute('INSERT INTO decisions VALUES (?,?,?,?,?,?,?,?)',(x['decision_id'],x['stage_id'],x['question'],x['proposed_owner'],x['status'],x['recommendation'],x['source_id'],rid))
            for x in data.get('reviews',[]):
                if x['reviewer_kind']=='human' and x['status']!='pending' and not x.get('attestation_path'):
                    raise ValueError('Human sign-off requires an explicit attestation_path')
                if x.get('attestation_path'):
                    relative_file(root,x['attestation_path'])
                cx.execute('INSERT INTO reviews VALUES (?,?,?,?,?,?,?,?)',(x['review_id'],x['stage_id'],x['reviewer'],x['reviewer_kind'],x['status'],x['source_id'],x['scope'],rid))
            for x in data.get('result_sets',[]):
                conditions=x['conditions']
                if x.get('review_state')=='human_reviewed':
                    review=cx.execute('SELECT reviewer_kind,status FROM reviews WHERE review_id=?',(x.get('human_review_id',''),)).fetchone()
                    if review!=('human','pass'):raise ValueError('Human-reviewed result requires an attested human pass review')
                if x['evidence_tier']=='observed_physical':
                    for key in ['temperature_K','salt','loading_mol_kg','DP','force_field']:
                        if conditions.get(key) is None:raise ValueError('Physical result missing '+key)
                if x['state']=='complete' and x['evidence_tier']=='planned':
                    raise ValueError('Planned evidence cannot be a completed result')
                cx.execute('INSERT INTO result_sets VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(x['result_id'],x['stage_id'],x['scope'],x['state'],x['evidence_tier'],x['source_id'],x['independent_unit'],json.dumps(conditions,sort_keys=True,allow_nan=False),x['interpretation_boundary'],x.get('review_state','unreviewed'),x.get('supersedes'),rid))
            observations.extend(data.get('observations',[]))
        for x in observations:
            result=cx.execute('SELECT state,evidence_tier FROM result_sets WHERE result_id=?',(x['result_id'],)).fetchone()
            if not result:raise ValueError('Unknown result_id')
            if x.get('value') is not None:
                if not math.isfinite(x['value']):raise ValueError('Non-finite metric')
                if result[0]!='complete' or result[1] in ['planned','analytical']:
                    raise ValueError('Unmeasured/planned result cannot carry observed numeric metrics')
            if not x['unit'].strip():raise ValueError('Metric unit required')
            cx.execute('INSERT INTO observations VALUES (?,?,?,?,?,?,?,?,?,?)',(x['observation_id'],x['result_id'],x['metric'],x['unit'],x.get('value'),x.get('missing_reason'),x.get('independent_n'),x.get('replicate_id'),x.get('ci_low'),x.get('ci_high')))
        for sid,status,scope in cx.execute('SELECT stage_id,status,acceptance_scope FROM stage_overview').fetchall():
            if status=='complete' and sid=='S1' and scope!='design':
                raise ValueError('S1 completion is design-only')
            if status=='complete' and sid!='S1':
                tier=" AND evidence_tier='observed_physical'" if sid=='S4' else " AND evidence_tier IN ('observed_prediction','observed_physical')"
                n=cx.execute("SELECT count(*) FROM result_sets WHERE stage_id=? AND scope='new_study' AND state='complete'"+tier,(sid,)).fetchone()[0]
                if not n or scope!='scientific':raise ValueError('Scientific stage completion requires completed new-study evidence: '+sid)
        queries={
            'stages':('SELECT * FROM stage_overview ORDER BY ordinal','S1 complete means design artifacts only; scientific results and human review are separate.'),
            'results':('SELECT r.result_id,r.stage_id,r.scope,r.state,r.evidence_tier,r.independent_unit,o.metric,o.unit,o.value,o.missing_reason,o.independent_n FROM result_sets r LEFT JOIN observations o USING(result_id) ORDER BY r.result_id,o.observation_id','Missing is NULL, never zero. Historical and new studies, synthetic and physical evidence stay explicit.'),
            'decisions':('SELECT decision_id,stage_id,question,proposed_owner,status,recommendation FROM decisions ORDER BY decision_id','Proposed owners are not accepted assignments; a record does not grant compute authorization.'),
            'reviews':('SELECT review_id,stage_id,reviewer,reviewer_kind,status,scope FROM reviews ORDER BY review_id','Agent verification is not human scientific sign-off.')}
        query_results={}
        for q,(sql,boundary) in queries.items():
            c=cx.execute(sql);cols=[x[0] for x in c.description];vals=c.fetchall()
            cx.execute('INSERT INTO query_catalog VALUES (?,?,?,?)',(q,sql,json.dumps(cols),boundary));query_results[q]={'columns':cols,'rows':vals}
        for table, in cx.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall():
            for row in cx.execute('PRAGMA table_info('+table+')').fetchall():
                unit='per-row unit column' if row[1] in ['value','ci_low','ci_high'] else None
                cx.execute('INSERT INTO data_dictionary VALUES (?,?,?,?,?)',(table,row[1],row[2],unit,'See schema, registry README and source record; no implicit scientific acceptance.'))
        cx.commit()
        assert cx.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert not cx.execute('PRAGMA foreign_key_check').fetchall()
        counts={t:cx.execute('SELECT count(*) FROM '+t).fetchone()[0] for (t,) in cx.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()}
        cx.close()
        receipt={'schema_version':1,'database_sha256':sha(Path(tmp)),'inputs':[{ 'name':n,'sha256':hashlib.sha256(encode(d).encode()).hexdigest()} for n,d in records],'counts':counts,'role':'coordination_and_results_index_not_scientific_acceptance','sql_integrity':'ok','foreign_keys':'ok'}
        if publish:
            os.replace(tmp,out/'paper_progress.sqlite')
            (out/'build_receipt.json').write_text(encode(receipt))
            for q,value in query_results.items():(out/(q+'.json')).write_text(encode(value))
        return receipt
    finally:
        cx.close()
        if Path(tmp).exists():Path(tmp).unlink()

def record(path,root=ROOT,reg=REG):
    data=read(path);rid=data['record_id']
    if not re.fullmatch('[a-zA-Z0-9_-]+',rid):raise ValueError('Unsafe record_id')
    dst=reg/'records'/(rid+'.json')
    if dst.exists():
        existing=read(dst)
        # Compare after source size normalization for a repeated exact record.
        validate_sources(data,root)
        previous={x['event_id']:x for x in existing.get('stage_events',[])}
        for event in data.get('stage_events',[]):
            if event['event_id'] in previous:event.setdefault('sequence',previous[event['event_id']]['sequence'])
        if encode(existing)!=encode(data):raise ValueError('Immutable record conflict; use a new ID and supersedes')
        return build(root,reg)
    validate_sources(data,root)
    maxseq=max([0]+[x['sequence'] for f in (reg/'records').glob('*.json') for x in read(f).get('stage_events',[])])
    for i,event in enumerate(data.get('stage_events',[]),1):event.setdefault('sequence',maxseq+i)
    build(root,reg,extra=data,publish=False)  # Validate the full batch before writing.
    with dst.open('x') as f:f.write(encode(data))
    try:return build(root,reg)
    except Exception:
        dst.unlink();raise

def main():
    ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='command',required=True)
    sub.add_parser('build');p=sub.add_parser('record');p.add_argument('--input',type=Path,required=True)
    p=sub.add_parser('query');p.add_argument('name',choices=['stages','results','decisions','reviews']);args=ap.parse_args()
    if args.command=='record':print(encode(record(args.input)),end='')
    elif args.command=='build':print(encode(build()),end='')
    else:
        cx=sqlite3.connect('file:'+str(REG/'output/paper_progress.sqlite')+'?mode=ro',uri=True);cx.execute('PRAGMA query_only=ON');sql=cx.execute('SELECT sql_text FROM query_catalog WHERE query_id=?',(args.name,)).fetchone()[0];c=cx.execute(sql);print(encode({'columns':[x[0] for x in c.description],'rows':c.fetchall()}),end='')
if __name__=='__main__':main()
