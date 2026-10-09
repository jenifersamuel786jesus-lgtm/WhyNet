from diagnostics.fault_engine import diagnose


def r(kind,status,**extra): return {'test_type':kind,'status':status,**extra}

def cats(results): return {d['category'] for d in diagnose(results,high_latency_ms=100)}

def test_dns_failure_with_ip_connectivity():
    ds=diagnose([r('connectivity','online',target='1.1.1.1:443'),r('dns','failed',target='bad.test')])
    assert any(d['category']=='dns_resolution_failure' and d['confidence']=='strong' for d in ds)

def test_connectivity_failure(): assert 'internet_connectivity_failure' in cats([r('connectivity','offline')])

def test_tcp_unreachable_when_online(): assert 'tcp_service_unreachable' in cats([r('connectivity','online'),r('tcp','refused',target='example.com:9')])

def test_high_latency_and_possible_loss():
    result=r('latency','success',avg_ms=150,packet_loss_pct=25,successful_attempts=3,attempts=4)
    assert {'high_latency','possible_packet_loss'} <= cats([result])

def test_intermittent_connectivity():
    assert 'intermittent_connectivity' in cats([r('connectivity','online'),r('latency','success',avg_ms=40,packet_loss_pct=25,successful_attempts=3,attempts=4)])

def test_insufficient_evidence(): assert 'insufficient_evidence' in cats([])
