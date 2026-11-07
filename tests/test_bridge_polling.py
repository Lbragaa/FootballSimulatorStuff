import time
from braga_era.bridge.github import GitHub


def test_polling_rate_budget_and_unchanged_status(monkeypatch):
    g=GitHub('owner/private',123,456,'unused')
    assert g.polling_delay(5)==5
    g.rate_remaining=210; g.rate_reset=time.time()+3000
    assert g.polling_delay(5)==300
    g.rate_remaining=4900
    assert g.polling_delay(5)==5
    calls=[]
    monkeypatch.setattr(g,'privacy',lambda:calls.append('privacy'))
    def call(path,method='GET',data=None):
        calls.append((path,method))
        return {'user':{'id':456},'title':'[BRAGA STATUS]','body':''}
    monkeypatch.setattr(g,'call',call)
    g.status({'test':'same'})
    before=list(calls)
    g.status({'test':'same'})
    assert calls==before
    g.status({'test':'changed'})
    assert len(calls)>len(before)
