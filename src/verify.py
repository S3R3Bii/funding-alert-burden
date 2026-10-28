"""Independent source joins, median arithmetic, monitor and intervention checks."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import math
import statistics
import datetime
import calendar

ROOT=Path(__file__).resolve().parents[1];R=ROOT/'results'

def read(name):
    with (R/name).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def close(a,b):assert math.isclose(float(a),float(b),rel_tol=1e-9,abs_tol=1e-8),(a,b)

def truth(value):return value in [True,'True','true','1']

def recompute(frame,spec,start=0,base=None,modified=None,stop=None):
    raw=[float(r['spread_bps']) for r in frame] if modified is None else modified
    flags=[truth(r['month_end_window']) for r in frame]
    values=[dict(adjusted_spread=0.,prior_center=0.,prior_scale=1.,z=0.,ewma=0.,calendar_correction=0.) for _ in frame] if base is None else [r.copy() for r in base]
    window=int(spec['window']);alpha=float(spec['alpha']);cal=truth(spec['calendar'])
    for i in range(start,len(frame) if stop is None else stop):
        correction=0.
        if cal and flags[i]:
            history=range(max(0,i-756),i);special=[raw[j] for j in history if flags[j]];ordinary=[raw[j] for j in history if not flags[j]]
            if len(special)>=10 and len(ordinary)>=10:correction=statistics.median(special)-statistics.median(ordinary)
        adjusted=raw[i]-correction
        prior=[values[j]['adjusted_spread'] for j in range(max(0,i-window),i)]
        center=statistics.median(prior) if i>=window else 0.
        scale=max(1.,1.4826*statistics.median(abs(v-center) for v in prior)) if i>=window else 1.
        z=(adjusted-center)/scale if i>=window else 0.
        ewma=alpha*z+(1-alpha)*(values[i-1]['ewma'] if i else 0.)
        values[i]=dict(adjusted_spread=adjusted,prior_center=center,prior_scale=scale,z=z,ewma=ewma,calendar_correction=correction)
    return values

def alert(values,t):
    if t is None:return [False]*len(values)
    high=[abs(r['ewma'])>t for r in values]
    return [False]+[a and b for a,b in zip(high[:-1],high[1:])]

def verify(phase):
    source={}
    for m in json.loads((ROOT/'data/manifest.json').read_text()):
        p=ROOT/m['file'];assert hashlib.sha256(p.read_bytes()).hexdigest()==m['sha256']
        records=json.loads(p.read_text())['refRates'];assert len(records)==m['rows']
        source[m['rate']]={r['effectiveDate']:r for r in records};assert len(source[m['rate']])==len(records)
    dates=sorted(source['sofr'].keys()&source['effr'].keys());q=json.loads((R/'source_quality.json').read_text())
    assert len(dates)==q['joined_rows']==2123
    assert sorted(source['effr'].keys()-source['sofr'].keys())==q['effr_only_dates']
    frame=read('validation_input.csv' if phase=='validation' else 'full_input.csv')
    expected=[d for d in dates if phase=='test' or d<='2023-12-31']
    assert [r['effective_date'] for r in frame]==expected
    ends={i for i in range(len(dates)-1) if dates[i][:7]!=dates[i+1][:7]}
    last=datetime.date.fromisoformat(dates[-1])
    if last.day==calendar.monthrange(last.year,last.month)[1]:ends.add(len(dates)-1)
    expected_flags={j for i in ends for j in [i-1,i,i+1] if 0<=j<len(dates)}
    for i,row in enumerate(frame):
        assert truth(row['month_end_window'])==(i in expected_flags)
        d=row['effective_date'];sofr=source['sofr'][d]['percentRate'];effr=source['effr'][d]['percentRate']
        close(row['sofr_percent'],sofr);close(row['effr_percent'],effr);close(row['spread_bps'],100*(sofr-effr))
    selection=json.loads((R/'selection.json').read_text());specs={s['name']:s for s in selection['candidates']}
    table=read('search.csv' if phase=='validation' else 'test_metrics.csv');exports=read('validation_scores.csv' if phase=='validation' else 'test_scores.csv');events=read('validation_interventions.csv' if phase=='validation' else 'test_interventions.csv')
    indices=[i for i,r in enumerate(frame) if ('2022-01-01'<=r['effective_date']<='2023-12-31' if phase=='validation' else r['effective_date']>='2024-01-01')]
    for row in table:
        name=row['name'] if phase=='validation' else row['model'];spec=specs[name];scores=recompute(frame,spec)
        t=(float(row['threshold']) if row['threshold'] else None) if phase=='validation' else selection['selected_parameters'][name]['threshold']
        flags=alert(scores,t)
        for output in [r for r in exports if r['model']==name]:
            i=int(output['observation_index']);assert int(output['latest_center_input_index'])==i-1
            for key,value in scores[i].items():close(output[key],value)
            assert truth(output['persistent_alert'])==flags[i]
        count=sum(flags[i] for i in indices);close(row['background_alerts'],count);close(row['background_rate'],count/len(indices))
        selected=[e for e in events if e['model']==name]
        expected_starts=indices[20:-7:40];assert len(selected)==len(expected_starts)*2
        counts={label:[] for label in ['persistent','transient']}
        for e in selected:
            start=int(e['start_index']);assert start in expected_starts;duration=int(e['duration_observations']);modified=[float(r['spread_bps']) for r in frame]
            for j in range(start,start+duration):modified[j]+=10.
            changed=recompute(frame,spec,start=start,base=scores,modified=modified,stop=start+7);raised=alert(changed,t)
            new=[j-start for j in range(start,start+7) if raised[j] and not flags[j]]
            assert truth(e['new_persistent_alert'])==bool(new)
            assert (int(float(e['delay_observations'])) if e['delay_observations'] else None)==(new[0] if new else None)
            counts[e['scenario']].append(bool(new))
        for label,values in counts.items():
            close(row[label+'_cases'],len(values));close(row[label+'_new_alerts'],sum(values));close(row[label+'_fraction'],sum(values)/len(values))
            delays=[int(float(e['delay_observations'])) for e in selected if e['scenario']==label and truth(e['new_persistent_alert'])]
            if delays:close(row[label+'_median_delay'],statistics.median(delays))
            else:assert row[label+'_median_delay']==''
        close(row['objective'],sum(counts['persistent'])/len(counts['persistent'])-sum(counts['transient'])/len(counts['transient']))
        if phase=='validation':
            eligible=[]
            for trial in [r for r in read('threshold_search.csv') if r['model']==name]:
                threshold=float(trial['threshold']);n=sum(alert(scores,threshold)[i] for i in indices);close(trial['alerts'],n);close(trial['alert_rate'],n/len(indices))
                if n/len(indices)<=.01:eligible.append(threshold)
            assert t==(min(eligible) if eligible else None)
    if phase=='validation':
        best=min(table,key=lambda r:(-float(r['objective']),float(r['background_rate']),r['name']))['name'];assert best==selection['selected_model']
    else:
        summary=json.loads((R/'test_summary.json').read_text());assert summary['evaluated_utc']>selection['frozen_utc']
    receipt=dict(status='PASS',phase=phase,checks=['Original JSON hashes, date uniqueness and exact joins reconcile','Percentage-rate to basis-point conversion independently checked','Every exported monitor center, scale, calendar correction, EWMA and flag independently recomputed','Every controlled intervention and detection delay independently recomputed','All threshold budget trials and model selection checked' if phase=='validation' else 'Frozen test outcomes checked'],limits='Retrospective final snapshot and dependent synthetic interventions; no live-vintage or economic false-positive-rate proof')
    (R/f'{phase}_verification.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8');print(json.dumps(receipt))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['validation','test']);verify(p.parse_args().phase)
