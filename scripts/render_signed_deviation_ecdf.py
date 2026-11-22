from pathlib import Path
import sys
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'results/upper-tail'
kind = sys.argv[1] if len(sys.argv) > 1 else 'blind'
if kind == 'blind':
    data = pd.read_csv(BASE / 'candidate_predictions.csv')
    pred, valid = 'predicted_log_sigma', 'valid'
    outdir = BASE / 'publication_v2'
    title = 'Signed target deviation under the Q80-only blind RF'
else:
    data = pd.read_csv(BASE / 'full-rf-audit/fullrf_candidate_predictions.csv')
    pred, valid = 'fullrf_prediction', 'fullrf_valid'
    outdir = BASE / 'full-rf-audit/publication'
    title = 'Signed target deviation under the full-source RF audit'
outdir.mkdir(parents=True, exist_ok=True)
targets = ['Q80_boundary_actual_train_max','Q85','Q90','Q95']
labels = {'Q80_boundary_actual_train_max':'Boundary','Q85':'Q85','Q90':'Q90','Q95':'Q95'}
arms = ['continuous','binary','unconditional_reranking']
names = {'continuous':'Continuous','binary':'Binary','unconditional_reranking':'Unconditional + reranking'}
colors = {'continuous':(0,126,130),'binary':(213,95,2),'unconditional_reranking':(105,105,105)}
def font(size):
    for p in ['/System/Library/Fonts/Helvetica.ttc','/System/Library/Fonts/Supplemental/Arial.ttf']:
        try: return ImageFont.truetype(p,size)
        except OSError: pass
    return ImageFont.load_default()
W,H=1500,1480
img=Image.new('RGB',(W,H),'white'); d=ImageDraw.Draw(img)
title_f,panel_f,small_f=font(31),font(24),font(15)
d.text((55,28),title,fill='black',font=title_f)
d.text((55,70),'x = RF prediction − requested target; negative values indicate under-target prediction',fill=(80,80,80),font=small_f)
left,right,top0,ph=170,1370,125,245
xmin,xmax=-0.65,0.15
for p,target in enumerate(targets):
    top=top0+p*285; bottom=top+ph
    d.text((55,top+8),labels[target],fill='black',font=panel_f)
    d.line((left,top,left,bottom),fill=(20,20,20),width=3); d.line((left,bottom,right,bottom),fill=(20,20,20),width=3)
    for val in [-.6,-.4,-.2,0,.1]:
        x=left+int((val-xmin)/(xmax-xmin)*(right-left)); d.line((x,bottom,x,bottom+7),fill=(20,20,20),width=2); d.text((x,bottom+13),f'{val:.1f}',anchor='ma',fill=(20,20,20),font=small_f)
    zero=left+int((0-xmin)/(xmax-xmin)*(right-left)); d.line((zero,top,zero,bottom),fill=(40,40,40),width=2)
    for arm in arms:
        g=data[(data.target_label==target)&(data.arm==arm)]
        vals=(g.loc[g[valid],pred]-g.loc[g[valid],'target']).dropna().sort_values().tolist()
        if vals:
            pts=[]
            for i,v in enumerate(vals,1):
                x=left+int(max(0,min(1,(v-xmin)/(xmax-xmin)))*(right-left)); y=bottom-int(i/len(vals)*ph); pts.append((x,y))
            d.line(pts,fill=colors[arm],width=4); d.ellipse((pts[-1][0]-5,pts[-1][1]-5,pts[-1][0]+5,pts[-1][1]+5),fill=colors[arm])
        nvalid=int(g[valid].sum()); N=len(g); d.text((right-270,top+18+arms.index(arm)*18),f'{names[arm]} {nvalid}/{N}',fill=colors[arm],font=small_f)
    d.text((left+10,top+ph-28),'0 = exact target',fill=(70,70,70),font=small_f)
d.text((55,1440),'Invalid candidates are excluded from the ECDF but retained as valid n/N; MD validation is not available.',fill=(75,75,75),font=small_f)
base=outdir / ('Figure_signed_target_deviation_ecdf_' + kind)
img.save(str(base)+'.png',dpi=(300,300)); img.save(str(base)+'.pdf',resolution=300.0); print(base)
