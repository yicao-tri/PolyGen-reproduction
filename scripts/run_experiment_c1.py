#!/usr/bin/env python3
"""Paired binary vs continuous soft-prefix chemistry generation experiment."""

from __future__ import annotations
import argparse, csv, hashlib, json, math, os, random, sys, time
from pathlib import Path
import numpy as np, pandas as pd, torch
from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import AllChem
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from torch import nn
from torch.nn import functional as F
from torch.utils.data import Dataset, DataLoader

ROOT=Path(__file__).resolve().parents[1]; REPO=ROOT/'vendor/PolyGen-1.0.0'
RDLogger.DisableLog('rdApp.warning')
sys.path.insert(0,str(REPO))
from deepchem.feat.smiles_tokenizer import SmilesTokenizer
from minGPT.model.mingpt.model import GPT

TARGETS=(-5.0,-4.0,-3.0); PREFIX=5; BLOCK=64; CUTOFF=-4.0

def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def fp(smiles):
    m=Chem.MolFromSmiles(smiles.replace('[Cu]','[*]').replace('[Au]','[*]'))
    return None if m is None else AllChem.GetMorganFingerprintAsBitVect(m,2,nBits=2048)
def arr(f):
    a=np.zeros(2048,dtype=np.uint8); DataStructs.ConvertToNumpyArray(f,a); return a

class SeqDataset(Dataset):
    def __init__(self, frame, tokenizer):
        self.cond=torch.tensor(frame.log_sigma.to_numpy(),dtype=torch.float32)
        seq=[]
        for s in frame.mol_smiles:
            ids=tokenizer.encode(s)
            ids=np.pad(ids,(0,BLOCK+1-PREFIX-len(ids)),constant_values=0)[:BLOCK+1-PREFIX]
            seq.append(np.concatenate([np.ones(PREFIX,dtype=np.int64),ids]))
        self.seq=torch.tensor(np.stack(seq),dtype=torch.long)
    def __len__(self): return len(self.seq)
    def __getitem__(self,i): return self.seq[i,:-1],self.seq[i,1:],self.cond[i]

class SoftConditionGPT(nn.Module):
    def __init__(self, config, arm, mean, std):
        super().__init__(); self.gpt=GPT(config); self.arm=arm; self.mean=mean; self.std=std
        n=config.n_embd
        self.cont=nn.Sequential(nn.Linear(1,n),nn.Tanh(),nn.Linear(n,n))
        self.binary=nn.Embedding(2,n)
    def configure_optimizers(self,lr): return torch.optim.AdamW(self.parameters(),lr=lr,betas=(.9,.95),weight_decay=.1)
    def forward(self,idx,cond,targets=None):
        b,t=idx.shape; pos=torch.arange(t,device=idx.device).unsqueeze(0)
        tok=self.gpt.transformer.wte(idx); norm=((cond-self.mean)/self.std).view(-1,1)
        emb=self.cont(norm) if self.arm=='continuous' else self.binary((cond>=CUTOFF).long())
        tok=tok.clone(); tok[:,:PREFIX,:]+=emb[:,None,:]
        x=self.gpt.transformer.drop(tok+self.gpt.transformer.wpe(pos))
        for block in self.gpt.transformer.h: x=block(x)
        logits=self.gpt.lm_head(self.gpt.transformer.ln_f(x)); loss=None
        if targets is not None: loss=F.cross_entropy(logits.reshape(-1,logits.size(-1)),targets.reshape(-1),ignore_index=-1)
        return logits,loss
    @torch.no_grad()
    def generate(self,cond,n,temperature=1.0):
        idx=torch.ones((n,PREFIX),dtype=torch.long,device=cond.device)
        for _ in range(BLOCK-PREFIX):
            logits,_=self(idx,cond); logits=logits[:,-1,:]/temperature
            v,_=torch.topk(logits,40); logits[logits<v[:,[-1]]]=-float('inf')
            idx=torch.cat([idx,torch.multinomial(F.softmax(logits,dim=-1),1)],1)
        return idx[:,PREFIX:]

def prepare():
    d=pd.read_csv(ROOT/'inputs/release-data/htpmd-trainset.csv')[['mol_smiles','conductivity']].copy()
    d['log_sigma']=np.log10(d.conductivity); bins=pd.qcut(d.log_sigma,10,labels=False,duplicates='drop')
    train,test=train_test_split(d,test_size=.2,random_state=20260923,stratify=bins)
    return train.reset_index(drop=True),test.reset_index(drop=True)

def verifier(train,test):
    tr=[fp(x) for x in train.mol_smiles]; te=[fp(x) for x in test.mol_smiles]
    model=RandomForestRegressor(n_estimators=300,min_samples_leaf=2,max_features='sqrt',n_jobs=-1,random_state=20260923)
    model.fit(np.stack([arr(x) for x in tr]),train.log_sigma)
    p=model.predict(np.stack([arr(x) for x in te])); metrics={'test_rows':len(test),'rmse':float(mean_squared_error(test.log_sigma,p)**.5),'mae':float(mean_absolute_error(test.log_sigma,p)),'r2':float(r2_score(test.log_sigma,p))}
    return model,tr,metrics

def decode(tokenizer,row):
    s=tokenizer.decode(row).replace(' ','');
    if '[CLS]' not in s or '[SEP]' not in s:return ''
    return s.split('[CLS]',1)[1].split('[SEP]',1)[0]

def run_arm(arm,seed,train,model_v,train_fp,tokenizer,out,steps=1000,temperature=1.0,samples_per_target=100,allocation=None):
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    cfg=GPT.get_default_config(); cfg.model_type='gpt-nano'; cfg.vocab_size=tokenizer.vocab_size; cfg.block_size=BLOCK
    model=SoftConditionGPT(cfg,arm,float(train.log_sigma.mean()),float(train.log_sigma.std())); opt=model.configure_optimizers(5e-4)
    loader=iter(DataLoader(SeqDataset(train,tokenizer),batch_size=64,sampler=torch.utils.data.RandomSampler(train,replacement=True,num_samples=10**9)))
    losses=[]; started=time.time(); model.train()
    for step in range(steps):
        x,y,c=next(loader); _,loss=model(x,c,y); opt.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(),1); opt.step(); losses.append(float(loss))
    rows=[]; model.eval(); train_smiles=set(train.mol_smiles)
    for target_i,target in enumerate(TARGETS):
        n = allocation[target_i] if allocation is not None else samples_per_target
        cond=torch.full((n,),target)
        toks=model.generate(cond,n,temperature=temperature)
        for i,t in enumerate(toks):
            s=decode(tokenizer,t); f=fp(s) if s else None; valid=f is not None and s.count('[Cu]')==1 and s.count('[Au]')==1
            if valid:
                a=arr(f).reshape(1,-1); tree=np.array([q.predict(a)[0] for q in model_v.estimators_]); pred=float(tree.mean()); unc=float(tree.std(ddof=1)); support=max(DataStructs.TanimotoSimilarity(f,z) for z in train_fp); novel=s not in train_smiles
            else: pred=unc=support=np.nan; novel=False
            hit=bool(valid and novel and support>=.35 and unc<.35 and abs(pred-target)<.5)
            rows.append(dict(arm=arm,seed=seed,target=target,index=i,smiles=s,valid=valid,novel=novel,predicted_log_sigma=pred,uncertainty=unc,support=support,target_error=abs(pred-target) if valid else np.nan,hit=hit))
    out.mkdir(parents=True,exist_ok=True); pd.DataFrame(rows).to_csv(out/'samples.csv',index=False)
    summary={'arm':arm,'seed':seed,'steps':steps,'temperature':temperature,'samples_per_target':samples_per_target,'allocation':allocation,'elapsed_seconds':time.time()-started,'first_loss':losses[0],'last_loss':losses[-1],'samples':len(rows)}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n'); torch.save(model.state_dict(),out/'final.pt')
    return rows,summary

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--output',type=Path,default=ROOT/'results/experiment-c/c1')
    ap.add_argument(
        '--seeds',
        type=int,
        nargs='+',
        default=[17,42,907],
        help='One or more paired training/generation seeds (default: 17 42 907)',
    )
    ap.add_argument('--steps',type=int,default=1000)
    ap.add_argument('--temperature',type=float,default=1.0)
    ap.add_argument('--samples-per-target',type=int,default=100)
    ap.add_argument('--allocation',type=int,nargs=3,default=None,metavar=('N1','N2','N3'))
    args=ap.parse_args()
    if len(set(args.seeds)) != len(args.seeds):
        ap.error('--seeds must not contain duplicates')
    train,test=prepare(); mv,tfp,vm=verifier(train,test); tok=SmilesTokenizer(vocab_file=str(REPO/'minGPT/vocab.txt'))
    args.output.mkdir(parents=True,exist_ok=True); train.assign(split='generator_train_and_verifier_train').to_csv(args.output/'train_rows.csv',index=False); test.assign(split='verifier_test_only').to_csv(args.output/'test_rows.csv',index=False)
    allrows=[]; runs=[]
    for seed in args.seeds:
      for arm in ('binary','continuous'):
        rows,s=run_arm(arm,seed,train,mv,tfp,tok,args.output/f'{arm}-seed{seed}',args.steps,args.temperature,args.samples_per_target,args.allocation); allrows+=rows; runs.append(s)
    raw=pd.DataFrame(allrows); summary=raw.groupby(['arm','seed','target']).agg(n=('hit','size'),validity=('valid','mean'),novelty=('novel','mean'),hit_rate=('hit','mean'),target_mae=('target_error','mean'),ood_rate=('support',lambda x:float((x<.35).mean()))).reset_index(); summary.to_csv(args.output/'arm_seed_target_metrics.csv',index=False)
    per=summary.groupby(['arm','seed']).agg(hit_rate=('hit_rate','mean'),target_mae=('target_mae','mean'),validity=('validity','mean')).reset_index(); wide=per.pivot(index='seed',columns='arm',values='hit_rate'); paired=pd.DataFrame({'seed':wide.index,'delta_hit_continuous_minus_binary':wide.continuous-wide.binary}); paired.to_csv(args.output/'paired_primary.csv',index=False)
    agg={'seeds':args.seeds,'verifier':vm,'mean_paired_delta_hit':float(paired.delta_hit_continuous_minus_binary.mean()),'paired_deltas':paired.to_dict('records'),'runs':runs,'source_sha256':digest(ROOT/'inputs/release-data/htpmd-trainset.csv')}; (args.output/'result.json').write_text(json.dumps(agg,indent=2)+'\n'); print(json.dumps(agg,indent=2))
if __name__=='__main__':main()
