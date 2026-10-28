"""Forward-only robust monitoring and an explicitly synthetic persistence experiment."""
from datetime import datetime,timezone
import argparse
import json
import time
import numpy as np
import pandas as pd
from prepare import ROOT,load

R=ROOT/'results';THRESHOLDS=[.5,1.,1.5,2.,3.,4.,6.,8.]
BASE='w60_a0.3_cal0'

def save(name,obj):
    (R/name).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n',encoding='utf-8')

def candidates():return [dict(name=f'w{w}_a{a:g}_cal{int(c)}',window=w,alpha=a,calendar=c) for w in [30,60,120] for a in [.1,.3,.6] for c in [False,True]]

def one_step(raw,flags,adjusted,i,window,calendar):
    correction=0.
    if calendar and flags[i]:
        history=raw[max(0,i-756):i];groups=flags[max(0,i-756):i]
        if groups.sum()>=10 and (~groups).sum()>=10:correction=float(np.median(history[groups])-np.median(history[~groups]))
    value=raw[i]-correction
    if i<window:return value,0.,1.,0.,correction
    prior=adjusted[i-window:i];center=float(np.median(prior));scale=max(1.,1.4826*float(np.median(np.abs(prior-center))))
    return value,center,scale,(value-center)/scale,correction

def monitor(frame,spec,start=0,base=None,modified_raw=None,stop=None):
    raw=frame.spread_bps.to_numpy().copy() if modified_raw is None else modified_raw
    flags=frame.month_end_window.to_numpy();n=len(frame) if stop is None else stop
    if base is None:answer=np.zeros((len(frame),6));answer[:,2]=1.
    else:answer=base.copy()
    for i in range(start,n):
        value,center,scale,z,correction=one_step(raw,flags,answer[:,0],i,spec['window'],spec['calendar'])
        prior=answer[i-1,4] if i else 0.
        ewma=spec['alpha']*z+(1-spec['alpha'])*prior
        answer[i]=value,center,scale,z,ewma,correction
    return answer

def alerts(scores,threshold):
    if threshold is None:return np.zeros(len(scores),bool)
    high=np.abs(scores[:,4])>threshold
    return high&np.r_[False,high[:-1]]

def period_indices(frame,phase):
    date=frame.effective_date
    valid=(date>='2022-01-01')&(date<='2023-12-31')
    test=date>='2024-01-01'
    return np.flatnonzero(valid if phase=='validation' else test)

def intervention_cases(frame,spec,scores,threshold,indices):
    starts=indices[20:-7:40];base_alerts=alerts(scores,threshold);cases=[]
    raw=frame.spread_bps.to_numpy()
    for start in starts:
        end=int(start)+7
        for duration,label in [(1,'transient'),(5,'persistent')]:
            modified=raw.copy();modified[start:start+duration]+=10.
            changed=monitor(frame,spec,start=int(start),base=scores,modified_raw=modified,stop=end)
            raised=alerts(changed,threshold)[start:end];existing=base_alerts[start:end]
            new=raised&~existing;where=np.flatnonzero(new)
            cases.append(dict(model=spec['name'],start_date=frame.effective_date.iloc[start],start_index=int(start),duration_observations=duration,scenario=label,added_spread_bps=10.,new_persistent_alert=bool(new.any()),delay_observations=int(where[0]) if len(where) else None,any_persistent_alert=bool(raised.any()),unmodified_alert_in_window=bool(existing.any())))
    return cases

def case_summary(cases):
    answer={}
    for label in ['persistent','transient']:
        selected=[r for r in cases if r['scenario']==label];hits=[r for r in selected if r['new_persistent_alert']]
        answer[label+'_cases']=len(selected);answer[label+'_new_alerts']=len(hits)
        answer[label+'_fraction']=len(hits)/len(selected) if selected else None
        answer[label+'_median_delay']=float(np.median([r['delay_observations'] for r in hits])) if hits else None
    answer['objective']=answer['persistent_fraction']-answer['transient_fraction']
    return answer

def output_scores(frame,spec,scores,threshold,indices):
    f=frame.iloc[indices].copy();f['model']=spec['name']
    for j,column in enumerate(['adjusted_spread','prior_center','prior_scale','z','ewma','calendar_correction']):f[column]=scores[indices,j]
    f['persistent_alert']=alerts(scores,threshold)[indices]
    f['latest_center_input_index']=indices-1;f['observation_index']=indices
    return f

def validation():
    R.mkdir(exist_ok=True);frame,quality=load('2023-12-31');indices=period_indices(frame,'validation');save('source_quality.json',quality)
    frame.to_csv(R/'validation_input.csv',index=False)
    trials=[];outcomes=[];events=[];daily=[]
    for spec in candidates():
        start=time.perf_counter();scores=monitor(frame,spec);threshold=None
        for t in THRESHOLDS:
            flags=alerts(scores,t)[indices];rate=float(flags.mean());trials.append(dict(model=spec['name'],threshold=t,days=len(indices),alerts=int(flags.sum()),alert_rate=rate))
            if threshold is None and rate<=.01:threshold=t
        cases=intervention_cases(frame,spec,scores,threshold,indices);events.extend(cases)
        flags=alerts(scores,threshold)[indices]
        row={**spec,'threshold':threshold,'validation_days':len(indices),'background_alerts':int(flags.sum()),'background_rate':float(flags.mean()),**case_summary(cases),'elapsed_seconds':time.perf_counter()-start,'status':'completed'}
        outcomes.append(row);daily.append(output_scores(frame,spec,scores,threshold,indices));print(spec['name'],row['objective'],threshold,flush=True)
    table=pd.DataFrame(outcomes).sort_values(['objective','background_rate','name'],ascending=[False,True,True]);winner=table.iloc[0]['name']
    table.to_csv(R/'search.csv',index=False);pd.DataFrame(trials).to_csv(R/'threshold_search.csv',index=False);pd.DataFrame(events).to_csv(R/'validation_interventions.csv',index=False);pd.concat(daily).to_csv(R/'validation_scores.csv',index=False)
    parameters={r['name']:r for r in outcomes}
    save('selection.json',dict(frozen_utc=datetime.now(timezone.utc).isoformat(),selected_model=winner,comparator=BASE,selected_parameters={name:parameters[name] for name in dict.fromkeys([winner,BASE])},candidates=candidates(),threshold_grid=THRESHOLDS,objective='Persistent new-alert fraction minus transient new-alert fraction; then lower background rate and name',validation_dates=['2022-01-01','2023-12-31'],test_dates=['2024-01-01','2026-09-30'],information_boundary='Current historical snapshot; forward-only adaptive history; not initial publication vintages'))

def test():
    selection=json.loads((R/'selection.json').read_text());frame,quality=load();indices=period_indices(frame,'test');save('source_quality.json',quality);frame.to_csv(R/'full_input.csv',index=False)
    specs={s['name']:s for s in candidates()};outcomes=[];daily=[];events=[]
    for name,param in selection['selected_parameters'].items():
        spec=specs[name];scores=monitor(frame,spec);t=param['threshold'];flags=alerts(scores,t)[indices]
        cases=intervention_cases(frame,spec,scores,t,indices);events.extend(cases)
        outcomes.append(dict(model=name,days=len(indices),background_alerts=int(flags.sum()),background_rate=float(flags.mean()),**case_summary(cases)))
        daily.append(output_scores(frame,spec,scores,t,indices))
    pd.DataFrame(outcomes).to_csv(R/'test_metrics.csv',index=False);pd.concat(daily).to_csv(R/'test_scores.csv',index=False);pd.DataFrame(events).to_csv(R/'test_interventions.csv',index=False)
    save('test_summary.json',dict(evaluated_utc=datetime.now(timezone.utc).isoformat(),selected_model=selection['selected_model'],comparator=BASE,metrics=outcomes,limits=['Controlled +10 basis-point interventions, not observed crises','Dependent cases share adaptive history; no independent-case confidence interval claimed','Current historical snapshot may include revisions; no live-vintage availability proof','Unlabeled background alert rate is review burden, not measured economic false positives']))
    print(json.dumps(outcomes))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['validate','test']);args=parser.parse_args();validation() if args.phase=='validate' else test()
