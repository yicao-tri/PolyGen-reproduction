#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]; base=ROOT/'results/experiment-c'
required=['c1/result.json','c1/arm_seed_target_metrics.csv','c1/paired_primary.csv','c1b/result.json','c1b/metrics.csv','c1b/paired.csv','c2/result.json','c2/metrics.csv','c2/paired.csv','pedatamine/audit.json','pedatamine/conductivity_long.csv','hierarchical_demo.csv']
checks={p:(base/p).is_file() and (base/p).stat().st_size>0 for p in required}
c1_samples=list((base/'c1').glob('*-seed*/samples.csv')); checks['six_c1_sample_files']=len(c1_samples)==6; checks['c1_1800_samples']=sum(len(pd.read_csv(p)) for p in c1_samples)==1800; checks['c1b_1800_samples']=len(pd.read_csv(base/'c1b/samples.csv'))==1800; checks['c2_8100_samples']=len(pd.read_csv(base/'c2/samples.csv'))==8100
pair=pd.read_csv(base/'c1/paired_primary.csv'); checks['c1_three_paired_seeds']=set(pair.seed)=={17,42,907}; demo=pd.read_csv(base/'hierarchical_demo.csv'); checks['hierarchical_joint_claims_blocked']=bool((~demo.eligible_for_physical_claim).all())
manifest={'status':'pass' if all(checks.values()) else 'fail','checks':checks,'artifacts':{p:hashlib.sha256((base/p).read_bytes()).hexdigest() for p in required}}
(base/'verification.json').write_text(json.dumps(manifest,indent=2)+'\n'); print(json.dumps(manifest,indent=2)); raise SystemExit(0 if manifest['status']=='pass' else 1)
