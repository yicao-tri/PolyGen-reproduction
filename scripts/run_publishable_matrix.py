#!/usr/bin/env python3
"""Run the preregistered PolyGen conditioning matrix, one arm/seed per process."""
from __future__ import annotations
import argparse, hashlib, json, math, random, re, sys, time
from pathlib import Path
import numpy as np, pandas as pd, torch
from torch import nn
from torch.nn import functional as F
from torch.utils.data import Dataset, DataLoader
from rdkit import Chem, RDLogger

ROOT=Path(__file__).resolve().parents[1]; REPO=ROOT/'vendor/PolyGen-1.0.0'; sys.path.insert(0,str(REPO))
from minGPT.model.mingpt.model import GPT
PAT=re.compile(r"(\[[^\]]+]|Br?|Cl?|N|O|S|P|F|I|b|c|n|o|s|p|\(|\)|\.|=|#|-|\+|\\|/|:|~|@|\?|>>?|\*|\$|%[0-9]{2}|[0-9])")

class Tok:
 def __init__(self,p): self.t=Path(p).read_text().splitlines(); self.d={x:i for i,x in enumerate(self.t)}; self.pad,self.cls,self.sep,self.unk=[self.d[x] for x in ('[PAD]','[CLS]','[SEP]','[UNK]')]
 def enc(self,s): return [self.cls]+[self.d.get(x,self.unk) for x in PAT.findall(s)]+[self.sep]
 def dec(self,ids):
  x=[self.t[int(i)] for i in ids]
  try: a=x.index('[CLS]')+1; b=x.index('[SEP]',a); return ''.join(x[a:b])
  except ValueError: return ''

def canonical(s):
 try:
  m=Chem.MolFromSmiles(s); return Chem.MolToSmiles(m) if m else ''
 except Exception: return ''

def make_split(unique,seed=42):
 groups={}
 for i,s in enumerate(unique.mol_smiles): groups.setdefault(canonical(s),[]).append(i)
 keys=sorted(groups); rng=np.random.default_rng(seed); rng.shuffle(keys); n=len(keys); a=int(.8*n); b=int(.9*n)
 assignment={k:('train' if j<a else 'validation' if j<b else 'test') for j,k in enumerate(keys)}
 out=unique.copy(); out['canonical_psmiles']=[canonical(s) for s in out.mol_smiles]; out['group_id']=['canon_'+hashlib.sha1(x.encode()).hexdigest()[:12] for x in out.canonical_psmiles]; out['split']=[assignment[x] for x in out.canonical_psmiles]; return out

class DS(Dataset):
 def __init__(self,rows,tok,arm,mu,sd,shuffle_map=None): self.r=rows.reset_index(drop=True); self.t=tok; self.arm=arm; self.mu=mu; self.sd=sd; self.shuffle_map=shuffle_map
 def __len__(self): return len(self.r)
 def __getitem__(self,i):
  r=self.r.iloc[i]; body=self.t.enc(r.mol_smiles)[:60]; body += [self.t.pad]*(60-len(body)); y=math.log10(float(r.conductivity)); ycond=self.shuffle_map.get(r.mol_smiles,y) if self.shuffle_map else y
  if self.arm=='binary': lead=9 if int(r.binary)==1 else 8
  elif self.arm=='multibin': lead=1+int(np.clip(np.searchsorted(self.r.attrs['bin_edges'],ycond,side='right'),0,4))
  elif self.arm=='unconditional': lead=1
  else: lead=self.t.pad
  seq=torch.tensor([lead]*5+body); target=seq[1:].clone()
  if self.arm in ('continuous','linear','shuffled'): target[:4]=-1
  return seq[:-1],target,torch.tensor((ycond-self.mu)/self.sd,dtype=torch.float32)

class Model(nn.Module):
 def __init__(self,cfg,arm):
  super().__init__(); self.g=GPT(cfg); self.arm=arm
  if arm in ('continuous','shuffled'): self.c=nn.Sequential(nn.Linear(1,cfg.n_embd),nn.GELU(),nn.Linear(cfg.n_embd,cfg.n_embd))
  elif arm=='linear': self.c=nn.Linear(1,cfg.n_embd)
  else: self.c=None
 def forward(self,idx,target=None,z=None):
  b,t=idx.shape; pos=torch.arange(t,device=idx.device)[None]; e=self.g.transformer.wte(idx)
  if self.c is not None: e[:,:5]=self.c(z[:,None])[:,None,:].expand(-1,5,-1)
  x=self.g.transformer.drop(e+self.g.transformer.wpe(pos))
  for block in self.g.transformer.h: x=block(x)
  logit=self.g.lm_head(self.g.transformer.ln_f(x)); loss=None if target is None else F.cross_entropy(logit.reshape(-1,logit.size(-1)),target.reshape(-1),ignore_index=-1); return logit,loss

def sample(m,tok,arm,target,mu,sd,n,temp,seed,threshold,edges,device):
 torch.manual_seed(seed)
 if arm=='binary': lead=9 if target>=threshold else 8
 elif arm=='multibin': lead=1+int(np.clip(np.searchsorted(edges,target,side='right'),0,4))
 else: lead=1 if arm=='unconditional' else tok.pad
 idx=torch.full((n,5),lead,dtype=torch.long,device=device); z=torch.full((n,),(target-mu)/sd,device=device); m.eval()
 with torch.no_grad():
  for _ in range(59):
   q,_=m(idx,z=z); p=F.softmax(q[:,-1]/temp,dim=-1); p[:,8:10]=0; p=p/p.sum(1,keepdim=True); idx=torch.cat([idx,torch.multinomial(p,1)],1)
 return [tok.dec(x[5:].tolist()) for x in idx]

def validity(s):
 m=Chem.MolFromSmiles(s) if s else None
 syntactic=bool(s); rd=bool(m); ends=rd and s.count('[Cu]')==1 and s.count('[Au]')==1
 single=ends and not any(x in s for x in ('=[Cu]','[Cu]=','=[Au]','[Au]=','#[Cu]','[Cu]#','#[Au]','[Au]#')) and all(a.GetDegree()==1 for a in m.GetAtoms() if a.GetSymbol() in ('Cu','Au'))
 return syntactic,rd,ends,single

def main():
 p=argparse.ArgumentParser(); p.add_argument('--output',type=Path,required=True); p.add_argument('--arm',choices=('binary','continuous','linear','shuffled','multibin','unconditional'),required=True); p.add_argument('--seed',type=int,required=True); p.add_argument('--steps',type=int,default=10000); p.add_argument('--samples',type=int,default=500); p.add_argument('--temperature',type=float,default=1.0); a=p.parse_args(); out=a.output/a.arm/f'seed_{a.seed}'; out.mkdir(parents=True,exist_ok=True)
 random.seed(a.seed); np.random.seed(a.seed); torch.manual_seed(a.seed); RDLogger.DisableLog('rdApp.*'); device=torch.device('mps' if torch.backends.mps.is_available() else 'cpu')
 unique=pd.read_csv(ROOT/'inputs/release-data/PolyGen-train-set-from-HTP-MD.csv')[['mol_smiles','conductivity']].drop_duplicates('mol_smiles').reset_index(drop=True); split=make_split(unique); split.to_csv(a.output/'split_manifest.csv',index_label='polymer_id')
 labels=pd.read_csv(REPO/'minGPT/htp_md.csv',sep='\t').rename(columns={'conductivity':'binary'}); balanced=labels.merge(unique,on='mol_smiles'); balanced=balanced.merge(split[['mol_smiles','split']],on='mol_smiles'); base=unique.merge(split[['mol_smiles','split']],on='mol_smiles')
 train_unique=base[base.split=='train']; logs=np.log10(train_unique.conductivity.astype(float)); mu=float(logs.mean()); sd=float(logs.std()); targets=[float(x) for x in logs.quantile([.1,.3,.5,.7,.9])]; threshold=float(logs.quantile(.95)); edges=[float(x) for x in logs.quantile([.2,.4,.6,.8])]
 rows=base[base.split=='train'].copy() if a.arm=='unconditional' else balanced[balanced.split=='train'].copy(); rows.attrs['bin_edges']=edges
 shuffle=None
 if a.arm=='shuffled': vals=np.log10(rows.drop_duplicates('mol_smiles').conductivity.astype(float).to_numpy()); np.random.default_rng(a.seed).shuffle(vals); shuffle=dict(zip(rows.drop_duplicates('mol_smiles').mol_smiles,vals))
 tok=Tok(REPO/'minGPT/vocab.txt'); cfg=GPT.get_default_config(); cfg.model_type='gpt-nano'; cfg.vocab_size=len(tok.t); cfg.block_size=64; m=Model(cfg,a.arm).to(device); opt=torch.optim.AdamW(m.parameters(),lr=5e-4,betas=(.9,.95),weight_decay=.1)
 ds=DS(rows,tok,a.arm,mu,sd,shuffle); gen=torch.Generator().manual_seed(a.seed); loader=iter(DataLoader(ds,batch_size=64,sampler=torch.utils.data.RandomSampler(ds,replacement=True,num_samples=a.steps*64,generator=gen),num_workers=0)); hist=[]; start=time.time(); m.train()
 for step in range(a.steps):
  x,y,z=next(loader); x,y,z=x.to(device),y.to(device),z.to(device); _,loss=m(x,y,z); opt.zero_grad(set_to_none=True); loss.backward(); torch.nn.utils.clip_grad_norm_(m.parameters(),1); opt.step()
  if step==0 or (step+1)%100==0: hist.append((step+1,float(loss.item())))
 torch.save(m.state_dict(),out/'final.pt'); pd.DataFrame(hist,columns=['step','loss']).to_csv(out/'loss.csv',index=False)
 records=[]; train_canon={canonical(s) for s in train_unique.mol_smiles}; rank=0
 for ti,target in enumerate(targets):
  ss=sample(m,tok,a.arm,target,mu,sd,a.samples,a.temperature,a.seed*100+ti,threshold,edges,device)
  seen=set()
  for j,s in enumerate(ss,1):
   rank+=1; can=canonical(s); syn,rd,end,poly=validity(s); uq=bool(can) and can not in seen; seen.add(can)
   records.append({'run_id':f'{a.arm}_seed{a.seed}','arm':a.arm,'seed':a.seed,'target_log_sigma':target,'target_sigma':10**target,'raw_generated_string':s,'canonical_p-SMILES':can,'syntactic_validity':syn,'rdkit_validity':rd,'connection_point_validity':end,'polymer_validity':poly,'unique':uq,'novel':bool(can) and can not in train_canon,'sampling_temperature':a.temperature,'generation_rank':j})
 pd.DataFrame(records).to_csv(out/'generated_candidates.csv',index=False)
 meta={'arm':a.arm,'seed':a.seed,'steps':a.steps,'samples_per_target':a.samples,'targets':targets,'binary_threshold_q95':threshold,'bin_edges':edges,'train_unique':len(train_unique),'train_rows_after_oversampling':len(rows),'validation_unique':int((base.split=='validation').sum()),'test_unique':int((base.split=='test').sum()),'mu':mu,'std':sd,'elapsed_seconds':time.time()-start,'device':str(device),'checkpoint_sha256':hashlib.sha256((out/'final.pt').read_bytes()).hexdigest()}; (out/'run.json').write_text(json.dumps(meta,indent=2)+'\n'); print(json.dumps(meta))
if __name__=='__main__': main()
