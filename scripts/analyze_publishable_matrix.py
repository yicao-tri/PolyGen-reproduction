#!/usr/bin/env python3
"""Analyze one completed seed of the publishable PolyGen conditioning matrix."""
from pathlib import Path
import argparse, json, math
import numpy as np, pandas as pd
from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import AllChem, Descriptors, Lipinski
from rdkit.Contrib.SA_Score import sascorer
from scipy.stats import pearsonr, spearmanr, wasserstein_distance
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.decomposition import PCA

ROOT=Path(__file__).resolve().parents[1]; RDLogger.DisableLog('rdApp.*'); GEN=AllChem.GetMorganGenerator(radius=2,fpSize=2048)
ARMS=('binary','continuous','linear','shuffled','multibin','unconditional')
ETHER=Chem.MolFromSmarts('[#6]-[OX2]-[#6]')

def mol(s):
 try: return Chem.MolFromSmiles(s)
 except Exception: return None
def fp(s): return np.asarray(GEN.GetFingerprintAsNumPy(mol(s)),dtype=np.uint8)
def desc(s):
 m=mol(s); atoms=[a for a in m.GetAtoms() if a.GetSymbol() not in ('Cu','Au')]; heavy=[a for a in atoms if a.GetAtomicNum()>1]; n=max(len(heavy),1); het=sum(a.GetSymbol() not in ('C','H') for a in heavy); aro=sum(a.GetIsAromatic() for a in heavy); rings=sum(a.IsInRing() for a in heavy)
 return [n,het/n,aro/n,rings/n,len(m.GetSubstructMatches(ETHER)),Lipinski.NumRotatableBonds(m),Descriptors.MolLogP(m),Descriptors.TPSA(m)]
DESC_NAMES=['heavy_atoms','heteroatom_fraction','aromatic_fraction','ring_atom_fraction','ether_count','rotatable_bonds','logp','tpsa']
def perf(y,p): return {'rmse':mean_squared_error(y,p)**.5,'mae':mean_absolute_error(y,p),'r2':r2_score(y,p)}

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--run',type=Path,required=True); ap.add_argument('--seed',type=int,default=101); a=ap.parse_args(); run=a.run.resolve(); tables=run/'tables'; tables.mkdir(exist_ok=True)
 split=pd.read_csv(run/'split_manifest.csv'); data=split.copy(); data['log_sigma']=np.log10(data.conductivity.astype(float))
 X=np.stack([fp(s) for s in data.mol_smiles]); D=np.stack([desc(s) for s in data.mol_smiles]); tr=data.split.eq('train').to_numpy(); te=data.split.eq('test').to_numpy()
 rf=RandomForestRegressor(n_estimators=500,min_samples_leaf=2,n_jobs=-1,random_state=a.seed).fit(X[tr],data.log_sigma[tr]); gb=HistGradientBoostingRegressor(max_iter=300,l2_regularization=1.0,random_state=a.seed).fit(D[tr],data.log_sigma[tr])
 metrics=[]
 for name,model,xx in [('rf_morgan',rf,X),('hgb_descriptors',gb,D)]:
  p=model.predict(xx[te]); q=perf(data.log_sigma[te],p); q.update({'model':name,'split':'heldout_test','n':int(te.sum())}); metrics.append(q)
 pd.DataFrame(metrics).to_csv(tables/'verifier_metrics.csv',index=False)
 train_fps=[GEN.GetFingerprint(mol(s)) for s in data.loc[tr,'mol_smiles']]
 # Exact identities are grouped before splitting. Quantify the remaining
 # near-neighbour relationship rather than calling the split "leakage free".
 audit=[]
 for split_name in ('validation','test'):
  query=data[data.split.eq(split_name)]
  nearest=[]
  for s in query.mol_smiles:
   nearest.append(max(DataStructs.BulkTanimotoSimilarity(GEN.GetFingerprint(mol(s)),train_fps)))
  nearest=np.asarray(nearest)
  audit.append({'split':split_name,'n':len(nearest),'exact_canonical_overlap':0,
                'nearest_tanimoto_mean':nearest.mean(),'nearest_tanimoto_median':np.median(nearest),
                'nearest_tanimoto_q90':np.quantile(nearest,.9),'fraction_ge_0_8':np.mean(nearest>=.8),
                'fraction_ge_0_9':np.mean(nearest>=.9)})
 pd.DataFrame(audit).to_csv(tables/'split_audit.csv',index=False)
 frames=[]
 for arm in ARMS:
  f=run/arm/f'seed_{a.seed}'/'generated_candidates.csv'
  if not f.exists(): continue
  d=pd.read_csv(f); frames.append(d)
 g=pd.concat(frames,ignore_index=True); valid=g.polymer_validity.fillna(False).astype(bool); g['nearest_training_similarity']=np.nan; g['structural_support']=False; g['rf_pred_log_sigma']=np.nan; g['rf_tree_std']=np.nan; g['descriptor_pred_log_sigma']=np.nan; g['sa_score']=np.nan
 idx=np.flatnonzero(valid)
 if len(idx):
  gx=np.stack([fp(g.iloc[i]['canonical_p-SMILES']) for i in idx]); gd=np.stack([desc(g.iloc[i]['canonical_p-SMILES']) for i in idx]); tree=np.stack([t.predict(gx) for t in rf.estimators_]); g.loc[idx,'rf_pred_log_sigma']=tree.mean(0); g.loc[idx,'rf_tree_std']=tree.std(0); g.loc[idx,'descriptor_pred_log_sigma']=gb.predict(gd)
  sims=[]
  for i in idx: sims.append(max(DataStructs.BulkTanimotoSimilarity(GEN.GetFingerprint(mol(g.iloc[i]['canonical_p-SMILES'])),train_fps)))
  g.loc[idx,'nearest_training_similarity']=sims; g.loc[idx,'structural_support']=np.asarray(sims)>=.25
  vals=np.stack([desc(g.iloc[i]['canonical_p-SMILES']) for i in idx]);
  for j,n in enumerate(DESC_NAMES): g.loc[idx,n]=vals[:,j]
  g.loc[idx,'sa_score']=[sascorer.calculateScore(mol(g.iloc[i]['canonical_p-SMILES'])) for i in idx]
 g['synthesizable_sa_lt5']=g.sa_score.lt(5) & valid
 g['verifier_disagreement']=(g.rf_pred_log_sigma-g.descriptor_pred_log_sigma).abs(); g['ensemble_pred_log_sigma']=g[['rf_pred_log_sigma','descriptor_pred_log_sigma']].mean(axis=1); g['target_error']=g.ensemble_pred_log_sigma-g.target_log_sigma; g.to_csv(tables/'generated_candidates.csv',index=False)
 quality=[]; response=[]
 for (arm,target),d in g.groupby(['arm','target_log_sigma']):
  clean=d[d.polymer_validity & d.unique & d.novel]; q={'arm':arm,'seed':a.seed,'target_log_sigma':target,'n':len(d),'syntactic_validity':d.syntactic_validity.mean(),'rdkit_validity':d.rdkit_validity.mean(),'connection_validity':d.connection_point_validity.mean(),'polymer_validity':d.polymer_validity.mean(),'uniqueness':d.unique.mean(),'novelty':d.novel.mean(),'synthesizable_sa_lt5':d.synthesizable_sa_lt5.mean(),'mean_sa_score':d.sa_score.mean(),'duplicate_rate':1-d.unique.mean(),'supported_rate':d.structural_support.mean(),'mean_nearest_similarity':d.nearest_training_similarity.mean()}
  if len(clean)>1:
   fps=[GEN.GetFingerprint(mol(s)) for s in clean['canonical_p-SMILES']]; rng=np.random.default_rng(0); pairs=rng.integers(0,len(fps),size=(min(20000,len(fps)*20),2)); q['diversity']=float(np.mean([1-DataStructs.TanimotoSimilarity(fps[i],fps[j]) for i,j in pairs if i!=j]))
  quality.append(q)
  z=d[d.polymer_validity & d.structural_support & d.ensemble_pred_log_sigma.notna()]; err=z.ensemble_pred_log_sigma-target; response.append({'arm':arm,'seed':a.seed,'target_log_sigma':target,'n_scored':len(z),'mean_pred':z.ensemble_pred_log_sigma.mean(),'std_pred':z.ensemble_pred_log_sigma.std(),'bias':err.mean(),'mae_to_target':err.abs().mean(),'rmse_to_target':float(np.sqrt(np.mean(err**2))) if len(z) else np.nan,'strict_hit_rate':(err.abs()<=.10).mean(),'relaxed_hit_rate':(err.abs()<=.20).mean(),'mean_uncertainty':z.rf_tree_std.mean(),'mean_disagreement':z.verifier_disagreement.mean()})
 pd.DataFrame(quality).to_csv(tables/'generation_metrics.csv',index=False); resp=pd.DataFrame(response); resp.to_csv(tables/'target_level_metrics.csv',index=False)
 endpoints=[]
 for arm,d in resp.groupby('arm'):
  x=d.target_log_sigma.to_numpy(); y=d.mean_pred.to_numpy(); slope,intercept=np.polyfit(x,y,1); adj=[]
  raw=g[(g.arm==arm)&g.polymer_validity&g.structural_support]
  ts=sorted(raw.target_log_sigma.unique())
  for lo,hi in zip(ts[:-1],ts[1:]): adj.append(wasserstein_distance(raw[raw.target_log_sigma==lo].ensemble_pred_log_sigma.dropna(),raw[raw.target_log_sigma==hi].ensemble_pred_log_sigma.dropna()))
  endpoints.append({'arm':arm,'seed':a.seed,'pearson_r':pearsonr(x,y).statistic,'spearman_rho':spearmanr(x,y).statistic,'slope':slope,'intercept':intercept,'mean_abs_calibration_error':np.mean(np.abs(y-x)),'mean_strict_hit_rate':d.strict_hit_rate.mean(),'mean_relaxed_hit_rate':d.relaxed_hit_rate.mean(),'monotonic_steps':int(np.sum(np.diff(y)>0)),'total_steps':len(y)-1,'mean_adjacent_wasserstein':np.mean(adj)})
 pd.DataFrame(endpoints).to_csv(tables/'controllability_endpoints.csv',index=False)
 chemistry=g[g.polymer_validity].groupby(['arm','target_log_sigma'])[DESC_NAMES].mean().reset_index(); chemistry.to_csv(tables/'chemistry_descriptors.csv',index=False)
 subset=g[g.polymer_validity & g.novel].drop_duplicates('canonical_p-SMILES').copy(); sx=np.stack([fp(s) for s in subset['canonical_p-SMILES']]); coords=PCA(n_components=2,random_state=a.seed).fit_transform(sx); subset['pc1']=coords[:,0]; subset['pc2']=coords[:,1]; subset[['arm','seed','target_log_sigma','canonical_p-SMILES','pc1','pc2','ensemble_pred_log_sigma','nearest_training_similarity']].to_csv(tables/'structural_embedding.csv',index=False)
 candidates=g[g.polymer_validity & g.novel & g.unique & g.structural_support & (g.rf_tree_std<=g.rf_tree_std.quantile(.75)) & (g.verifier_disagreement<=g.verifier_disagreement.quantile(.75))].copy(); candidates['selection_score']=candidates.target_error.abs()+candidates.rf_tree_std+candidates.verifier_disagreement; candidates=candidates[candidates.arm.isin(['binary','continuous'])].sort_values(['arm','selection_score']).groupby('arm').head(20); candidates['STATUS']='WAITING_FOR_MD_VALIDATION'; candidates.to_csv(tables/'md_candidates.csv',index=False)
 print(pd.DataFrame(metrics).to_string(index=False)); print(pd.DataFrame(endpoints).to_string(index=False))
if __name__=='__main__': main()
