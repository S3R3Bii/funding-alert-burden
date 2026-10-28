from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from analyze import monitor,alerts

class Contracts(unittest.TestCase):
    def frame(self):return pd.DataFrame({'spread_bps':np.zeros(200),'month_end_window':np.zeros(200,bool)})
    def test_future_values_do_not_change_prior_scores(self):
        f=self.frame();spec=dict(window=30,alpha=.3,calendar=True)
        before=monitor(f,spec);f.loc[150:,'spread_bps']=100
        after=monitor(f,spec)
        np.testing.assert_array_equal(before[:150],after[:150])
    def test_persistence_requires_two_successive_high_scores(self):
        f=np.zeros((5,6));f[:,4]=[0,3,0,3,3]
        self.assertEqual(alerts(f,2).tolist(),[False,False,False,False,True])
    def test_scale_floor_prevents_constant_history_division_by_zero(self):
        f=self.frame();f.loc[100,'spread_bps']=10
        score=monitor(f,dict(window=30,alpha=.6,calendar=False))
        self.assertEqual(score[100,2],1);self.assertEqual(score[100,3],10)
        self.assertTrue(np.isfinite(score).all())
    def test_cached_intervention_matches_full_recalculation(self):
        f=self.frame();spec=dict(window=30,alpha=.3,calendar=True);base=monitor(f,spec)
        raw=f.spread_bps.to_numpy().copy();raw[100:105]+=10
        cached=monitor(f,spec,start=100,base=base,modified_raw=raw,stop=107)
        full=monitor(f,spec,modified_raw=raw)
        np.testing.assert_allclose(cached[100:107],full[100:107],rtol=0,atol=0)
    def test_infinite_threshold_is_explicit_no_alert_policy(self):
        f=np.ones((6,6))*999
        self.assertFalse(alerts(f,None).any())

if __name__=='__main__':unittest.main()
