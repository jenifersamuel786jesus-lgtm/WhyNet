import json
from app import create_app


def test_health_and_invalid_inputs(tmp_path):
    app=create_app({'TESTING':True,'DATABASE':str(tmp_path/'test.db')})
    c=app.test_client()
    assert c.get('/api/health').json['status']=='ok'
    assert c.post('/api/test/dns',json={'host':'bad host'}).status_code==400
    assert c.post('/api/test/tcp',json={'host':'example.com','port':70000}).status_code==400
    assert c.post('/api/test/latency',json={'host':'example.com','port':443,'attempts':20}).status_code==400


def test_mocked_endpoint_persistence_and_history(tmp_path,monkeypatch):
    import app as module
    app=module.create_app({'TESTING':True,'DATABASE':str(tmp_path/'test.db')})
    monkeypatch.setattr(module,'dns_check',lambda host,timeout:{'test_type':'dns','target':host,'status':'success','latency_ms':2.3,'timestamp':'2026-01-01T00:00:00+00:00','resolved_ips':['192.0.2.1']})
    c=app.test_client()
    result=c.post('/api/test/dns',json={'host':'example.com'})
    assert result.status_code==200 and result.json['status']=='success'
    history=c.get('/api/history').json['items']
    assert len(history)==1 and history[0]['test_type']=='dns'


def test_tcp_failure_returns_json(tmp_path,monkeypatch):
    import app as module
    app=module.create_app({'TESTING':True,'DATABASE':str(tmp_path/'test.db')})
    monkeypatch.setattr(module,'tcp_check',lambda host,port,timeout:{'test_type':'tcp','target':f'{host}:{port}','status':'refused','latency_ms':None,'error':'refused','timestamp':'2026-01-01T00:00:00+00:00'})
    r=app.test_client().post('/api/test/tcp',json={'host':'localhost','port':80})
    assert r.status_code==200 and r.json['status']=='refused'
