import importlib.util
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest

HERE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('paper_progress',HERE/'progress.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.reg=self.root/'registry/paper';self.reg.mkdir(parents=True)
        shutil.copy2(HERE/'schema.sql',self.reg/'schema.sql');shutil.copytree(HERE/'records',self.reg/'records')
        for f in (self.reg/'records').glob('*.json'):
            for row in m.read(f).get('source_files',[]):
                p=self.root/row['path'];p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(m.ROOT/row['path'],p)
        m.build(self.root,self.reg)
    def record(self, data):
        p=self.root/'incoming.json';p.write_text(m.encode(data));return m.record(p,self.root,self.reg)
    def sample(self):
        p=self.root/'summary.json';p.write_text('{"software_fixture": true}\n')
        return {'record_id':'0009-software-fixture','recorded_at':'2026-11-25T01:00:00Z','source_files':[{'source_id':'test-source','path':'summary.json','sha256':m.sha(p)}],
                'result_sets':[{'result_id':'test-result','stage_id':'S2','scope':'new_study','state':'complete','evidence_tier':'engineering','source_id':'test-source','independent_unit':'software fixture','conditions':{},'interpretation_boundary':'test only'}],
                'observations':[{'observation_id':'test-observation','result_id':'test-result','metric':'fixture_value','unit':'count','value':2,'independent_n':1}]}
    def test_rebuild_and_registered_queries(self):
        a=m.build(self.root,self.reg);b=m.build(self.root,self.reg);self.assertEqual(a,b)
        cx=sqlite3.connect('file:'+str(self.reg/'output/paper_progress.sqlite')+'?mode=ro',uri=True);self.addCleanup(cx.close);cx.execute('PRAGMA query_only=ON')
        self.assertEqual(cx.execute('PRAGMA integrity_check').fetchone()[0],'ok')
        for sql,cols in cx.execute('SELECT sql_text,expected_columns_json FROM query_catalog').fetchall():
            cur=cx.execute(sql);self.assertEqual([x[0] for x in cur.description],json.loads(cols));cur.fetchall()
        self.assertEqual(cx.execute("SELECT status,acceptance_scope FROM stage_overview WHERE stage_id='S1'").fetchone(),('complete','design'))
        self.assertEqual(cx.execute("SELECT status FROM reviews WHERE reviewer_kind='human'").fetchone()[0],'pending')
    def test_real_ingest_idempotence_and_history(self):
        x=self.sample();x['stage_events']=[{'event_id':'test-active','stage_id':'S2','status':'active','acceptance_scope':'none','source_id':'test-source','note':'software test only'}]
        a=self.record(x);b=self.record(x);self.assertEqual(a,b)
        cx=sqlite3.connect(self.reg/'output/paper_progress.sqlite');self.addCleanup(cx.close)
        self.assertEqual(cx.execute('SELECT count(*) FROM result_sets').fetchone()[0],2)
        x['observations'][0]['value']=3
        with self.assertRaisesRegex(ValueError,'Immutable'):self.record(x)
    def test_bad_hash_does_not_mutate_snapshot(self):
        x=self.sample();before=m.sha(self.reg/'output/paper_progress.sqlite');x['source_files'][0]['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'SHA mismatch'):self.record(x)
        self.assertEqual(m.sha(self.reg/'output/paper_progress.sqlite'),before)
        self.assertFalse((self.reg/'records/0009-software-fixture.json').exists())
    def test_planned_zero_cannot_be_observed(self):
        x=self.sample();x['result_sets'][0].update(state='planned',evidence_tier='planned');x['observations'][0]['value']=0
        with self.assertRaisesRegex(ValueError,'Unmeasured'):self.record(x)
    def test_missing_value_remains_null(self):
        x=self.sample();x['result_sets'][0]['state']='failed';x['observations'][0].update(value=None,missing_reason='fit failed')
        self.record(x);cx=sqlite3.connect(self.reg/'output/paper_progress.sqlite');self.addCleanup(cx.close)
        self.assertEqual(cx.execute("SELECT value,missing_reason FROM observations WHERE observation_id='test-observation'").fetchone(),(None,'fit failed'))
    def test_foreign_key_and_unit_guards(self):
        x=self.sample();x['result_sets'][0]['stage_id']='unknown'
        with self.assertRaises(sqlite3.IntegrityError):self.record(x)
        x=self.sample();x['observations'][0]['unit']=''
        with self.assertRaisesRegex(ValueError,'unit'):self.record(x)
    def test_physics_requires_conditions_and_real_result(self):
        x=self.sample();x['result_sets'][0]['evidence_tier']='observed_physical'
        with self.assertRaisesRegex(ValueError,'Physical'):self.record(x)
        x=self.sample();x['stage_events']=[{'event_id':'fake-physics','stage_id':'S4','status':'complete','acceptance_scope':'scientific','source_id':'test-source','note':'must reject software as physical'}]
        with self.assertRaisesRegex(ValueError,'Scientific stage'):self.record(x)
    def test_human_attestation_not_inferred(self):
        x=self.sample();x['reviews']=[{'review_id':'fake-human','stage_id':'S1','reviewer':'Someone','reviewer_kind':'human','status':'pass','source_id':'test-source','scope':'must reject'}]
        with self.assertRaisesRegex(ValueError,'attestation'):self.record(x)
        x=self.sample();x['result_sets'][0]['review_state']='human_reviewed'
        with self.assertRaisesRegex(ValueError,'Human-reviewed'):self.record(x)

if __name__=='__main__':unittest.main()
