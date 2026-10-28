"""Source-backed decision, search and monitoring figures."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1];R=ROOT/'results';F=ROOT/'figures';F.mkdir(exist_ok=True)
selection=json.loads((R/'selection.json').read_text());winner=selection['selected_model'];base=selection['comparator']
metrics=pd.read_csv(R/'test_metrics.csv').set_index('model');search=pd.read_csv(R/'search.csv');scores=pd.read_csv(R/'test_scores.csv')
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False,'axes.spines.left':False,'axes.edgecolor':'#bac4d1','text.color':'#17283d','axes.labelcolor':'#17283d','xtick.color':'#526273','ytick.color':'#526273','figure.facecolor':'white','savefig.facecolor':'white'})
TEAL='#087f8c';ORANGE='#d18337';GRAY='#a5b2c2';INK='#17283d'
SOURCE='Derived from Secured Overnight Financing Rate and Effective Federal Funds Rate. © 2026 Federal Reserve Bank of New York.\nContent subject to New York Fed Terms of Use; see SOURCES.md. Current historical snapshot; no endorsement implied.'

def save(fig,name):
    fig.savefig(F/f'{name}.png',dpi=180,bbox_inches='tight');fig.savefig(F/f'{name}.pdf',bbox_inches='tight');plt.close(fig)

fig,axes=plt.subplots(1,3,figsize=(13,4.4));names=[base,winner];colors=[ORANGE,TEAL];labels=['Fixed comparator','Validation-selected']
for ax,key,title in zip(axes,['persistent_fraction','transient_fraction','background_rate'],['Five-observation shift detected','One-observation shift triggers persistence','Unmodified days flagged']):
    values=[float(metrics.loc[n,key])*100 for n in names]
    ax.bar(np.arange(2),values,color=colors,width=.55);ax.set_xticks(np.arange(2),labels,rotation=15,ha='right');ax.set_ylabel('Percent');ax.set_title(title,loc='left',fontsize=11,fontweight='bold')
    ax.set_ylim(0,100 if key!='background_rate' else 1.05)
    for i,v in enumerate(values):ax.text(i,v+(1.5 if key!='background_rate' else .02),f'{v:.1f}%' if key!='background_rate' else f'{v:.2f}%',ha='center',fontsize=10)
fig.suptitle('A small review queue can still miss persistent disturbances',x=.01,ha='left',fontsize=16,fontweight='bold',y=1.04)
fig.text(.01,-.16,'Test: 686 observed-rate days · 17 cases per intervention · +10 basis points for one or five observations\nSynthetic interventions on measured history. Right panel uses 0–1%; others 0–100%. Background burden is not an economic false-positive rate.',fontsize=9,color='#526273')
fig.text(.01,-.28,SOURCE,fontsize=8,color='#526273');fig.tight_layout(w_pad=3);save(fig,'decision-summary')

fig,ax=plt.subplots(figsize=(10,7));order=search.sort_values(['objective','background_rate','name'],ascending=[False,True,True])
labels=[n.replace('w','Window ').replace('_a',' / alpha ').replace('_cal0',' / no calendar').replace('_cal1',' / calendar') for n in order.name]
colors=[TEAL if n==winner else ORANGE if n==base else GRAY for n in order.name]
ax.barh(np.arange(len(order)),order.objective,color=colors,height=.66);ax.set_yticks(np.arange(len(order)),labels);ax.invert_yaxis();ax.set_xlim(0,1)
for i,value in enumerate(order.objective):ax.text(value+.012,i,f'{value:.3f}',va='center',fontsize=9)
ax.set_xlabel('Validation persistent-detection fraction − transient-call fraction');ax.set_title('All 18 declared monitoring configurations',loc='left',fontweight='bold',pad=17)
fig.text(.01,-.02,'Thresholds use a ≤1% unmodified validation-day alert budget. Four configurations require a no-alert policy.\nSelected window 30 and alpha .6 are grid boundaries; no global-optimum claim.',fontsize=9,color='#526273')
fig.text(.01,-.12,SOURCE,fontsize=8,color='#526273');fig.tight_layout();save(fig,'optimization-evidence')

fig,axes=plt.subplots(2,1,figsize=(12,6),sharex=True,gridspec_kw={'height_ratios':[1,1.2]})
chosen=scores[scores.model==winner];dates=pd.to_datetime(chosen.effective_date)
axes[0].plot(dates,chosen.spread_bps,color=INK,lw=1);axes[0].set_ylabel('SOFR − EFFR (bp)');axes[0].set_title('Unmodified published history, with the frozen monitor',loc='left',fontweight='bold')
for name,label,color in [(base,'Fixed comparator',ORANGE),(winner,'Validation-selected',TEAL)]:
    f=scores[scores.model==name];dd=pd.to_datetime(f.effective_date);axes[1].plot(dd,f.ewma,label=label,color=color,lw=1.1)
    flags=f.persistent_alert.astype(str).eq('True');axes[1].scatter(dd[flags],f.ewma[flags],color=color,marker='D',s=40,zorder=3)
axes[1].axhline(6,color=GRAY,ls='--',lw=.8);axes[1].axhline(-6,color=GRAY,ls='--',lw=.8);axes[1].set_ylabel('Signed robust EWMA');axes[1].legend(frameon=False,fontsize=10,loc='upper left');axes[1].set_xlabel('Effective date; 2024–2026 Q3 test interval')
fig.text(.01,-.03,'Diamonds: persistent flags. Dashed lines: frozen threshold ±6. Source revisions can affect this historical snapshot.',fontsize=9,color='#526273')
fig.text(.01,-.14,SOURCE,fontsize=8,color='#526273');fig.tight_layout();save(fig,'historical-monitor')
print('Three checked-input monitoring figures exported.')
