#!/usr/bin/env python3
import hashlib, json, re
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]; SOURCE=ROOT/'inputs/external/pedatamine/Cleaned_Final_Data_6_2_2020.csv'; OUT=ROOT/'results/experiment-c/pedatamine'
EXPECTED='c85f0568e8bde46913c009935ce0bf0643a72b9f086f5cc5d21ac724412baa63'
def main():
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest()!=EXPECTED: raise ValueError('PEDatamine hash mismatch')
    d=pd.read_csv(SOURCE,encoding='latin1'); cond=[c for c in d if re.fullmatch(r'Conductivity at \d+C',c)]
    rows=[]
    for _,r in d.iterrows():
      for c in cond:
        if pd.notna(r[c]) and float(r[c])>0:
          rows.append({'source_index':int(r['Index']),'polymer':r['Polymer'],'smiles_1':r['SMILES descriptor 1'],'smiles_2':r['SMILES descriptor 2'],'anion':r['Anion'],'li_monomer':r['Li:monomer'],'salt_wt_percent':r['salt wt%'],'mn_kda':r['Polymer Mn (kDa)'],'mw_kda':r['Polymer Mw (kDa)'],'architecture':r['chain architecture'],'temperature_C':int(re.search(r'\d+',c).group()),'conductivity_S_cm':float(r[c]),'doi':r['DOI'],'reference':r['Reference']})
    long=pd.DataFrame(rows); OUT.mkdir(parents=True,exist_ok=True); long.to_csv(OUT/'conductivity_long.csv',index=False)
    audit={'system_rows':len(d),'conductivity_points':len(long),'temperature_columns':len(cond),'polymers':int(d.Polymer.nunique()),'smiles_1':int(d['SMILES descriptor 1'].nunique()),'anions':int(d.Anion.nunique()),'dois':int(d.DOI.nunique()),'architectures':int(d['chain architecture'].nunique()),'rows_with_mn':int(d['Polymer Mn (kDa)'].notna().sum()),'rows_with_mw':int(d['Polymer Mw (kDa)'].notna().sum()),'source_sha256':EXPECTED,'limitations':['secondary literature compilation','SMILES descriptors are not standardized two-ended p-SMILES','temperature curves are sparse and irregular','Mn/Mw/architecture fields are missing for many systems']}; (OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n'); print(json.dumps(audit,indent=2))
if __name__=='__main__':main()
