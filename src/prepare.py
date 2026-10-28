"""Checked date join and calendar-only flags for public aggregate rates."""
from pathlib import Path
import hashlib
import json
import sqlite3
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]

def load(end=None):
    manifest=json.loads((ROOT/'data/manifest.json').read_text());source={}
    for item in manifest:
        p=ROOT/item['file'];assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256']
        rows=json.loads(p.read_text())['refRates'];assert len(rows)==item['rows']
        f=pd.DataFrame(rows)
        assert f.effectiveDate.is_unique,'Duplicate effective date needs review'
        assert f.type.str.upper().eq(item['rate'].upper()).all()
        source[item['rate']]=f.rename(columns={'effectiveDate':'effective_date','percentRate':'rate','revisionIndicator':'revision'})[['effective_date','rate','revision']]
    with sqlite3.connect(':memory:') as con:
        for name,frame in source.items():frame.to_sql(name,con,index=False)
        frame=pd.read_sql_query((ROOT/'sql/join_rates.sql').read_text(),con)
    dates={name:set(value.effective_date) for name,value in source.items()}
    quality={'source_rows':{k:len(v) for k,v in source.items()},'joined_rows':len(frame),'sofr_only_dates':sorted(dates['sofr']-dates['effr']),'effr_only_dates':sorted(dates['effr']-dates['sofr']),'revision_flags':{name:int(f.revision.astype(bool).sum()) for name,f in source.items()}}
    assert len(frame)==len(dates['sofr']&dates['effr']) and frame.effective_date.is_monotonic_increasing
    assert np.isfinite(frame[['sofr_percent','effr_percent','spread_bps']].to_numpy()).all()
    # Calendar dates only: month-end observation, its predecessor and successor.
    month=frame.effective_date.str[:7];last=(month!=month.shift(-1)).to_numpy()
    last[-1]=pd.Timestamp(frame.effective_date.iloc[-1]).is_month_end
    flag=last.copy();flag[:-1]|=last[1:];flag[1:]|=last[:-1]
    frame['month_end_window']=flag
    if end is not None:frame=frame[frame.effective_date<=end].reset_index(drop=True)
    return frame,quality
