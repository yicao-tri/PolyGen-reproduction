#!/usr/bin/env python3
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]; out=ROOT/'results/experiment-c/hierarchical_demo.csv'
chem=pd.read_csv(ROOT/'results/experiment-c/c1b/samples.csv'); form=pd.read_csv(ROOT/'results/experiment-c/c2/samples.csv')
chem=chem[(chem.arm=='continuous')&chem.valid&chem.novel].sort_values(['target','target_error'],ascending=[False,True]).drop_duplicates('smiles').head(10).reset_index(drop=True)
form=form[(form.method=='conditional_knn')&form.hit].sort_values(['temperature_K','target'],ascending=[True,False]).head(10).reset_index(drop=True)
n=min(len(chem),len(form)); demo=pd.DataFrame({'repeat_unit':chem.smiles.head(n),'chemistry_target_log_sigma':chem.target.head(n),'chemistry_verifier_prediction':chem.predicted_log_sigma.head(n),'salt':form.salt_shortname.head(n),'molality':form.molality.head(n),'temperature_K':form.temperature_K.head(n),'formulation_target_log_sigma':form.target.head(n),'formulation_verifier_prediction':form.predicted.head(n),'joint_support_status':'BLOCKED_no_training_data_for_generated_chemistry_plus_formulation','eligible_for_physical_claim':False})
demo.to_csv(out,index=False); print(demo.to_string(index=False))
