"""Retrieve bounded, cached public reference-rate snapshots with attribution."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib
import json
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
URLS={
 'sofr':'https://markets.newyorkfed.org/api/rates/secured/sofr/search.json?startDate=2018-04-02&endDate=2026-09-30',
 'effr':'https://markets.newyorkfed.org/api/rates/unsecured/effr/search.json?startDate=2018-04-02&endDate=2026-09-30'}

def main():
    data=ROOT/'data';data.mkdir(exist_ok=True);manifest=[]
    for rate,url in URLS.items():
        path=data/f'{rate}.json'
        if not path.exists():
            with urllib.request.urlopen(url,timeout=60) as response:path.write_bytes(response.read())
        rows=json.loads(path.read_text())['refRates']
        manifest.append(dict(rate=rate,url=url,file=path.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),rows=len(rows),retrieved_utc=datetime.now(timezone.utc).isoformat()))
    (data/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps([{'rate':r['rate'],'rows':r['rows'],'sha256':r['sha256']} for r in manifest]))

if __name__=='__main__':main()
