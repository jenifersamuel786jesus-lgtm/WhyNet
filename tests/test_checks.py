from unittest.mock import patch, MagicMock
import pytest
from diagnostics.checks import validate_host, tcp_check, latency_check


def test_validate_host_accepts_domain_and_ip():
    assert validate_host('example.com')=='example.com'
    assert validate_host('127.0.0.1')=='127.0.0.1'

@pytest.mark.parametrize('value',['','bad host','http://example.com','a'*254,'example.com:443'])
def test_validate_host_rejects_invalid(value):
    with pytest.raises(ValueError): validate_host(value)

@patch('diagnostics.checks.socket.create_connection')
def test_tcp_success(mock_connect):
    sock=MagicMock();mock_connect.return_value=sock
    r=tcp_check('example.com',443)
    assert r['status']=='success' and r['latency_ms'] is not None
    sock.close.assert_called_once()

@patch('diagnostics.checks.socket.create_connection',side_effect=ConnectionRefusedError('refused'))
def test_tcp_refused(_):
    assert tcp_check('example.com',443)['status']=='refused'

@patch('diagnostics.checks.socket.create_connection',side_effect=TimeoutError('timed out'))
def test_tcp_timeout(_):
    assert tcp_check('example.com',443)['status']=='timeout'

@patch('diagnostics.checks.tcp_check')
def test_latency_average_and_loss(mock_tcp):
    mock_tcp.side_effect=[{'status':'success','latency_ms':10},{'status':'timeout','error':'timeout'},{'status':'success','latency_ms':30},{'status':'success','latency_ms':20}]
    r=latency_check('1.1.1.1',443,4)
    assert r['avg_ms']==20 and r['min_ms']==10 and r['max_ms']==30
    assert r['packet_loss_pct']==25 and r['successful_attempts']==3

@patch('diagnostics.checks.tcp_check',return_value={'status':'timeout','error':'timeout'})
def test_latency_unavailable_not_zero(_):
    r=latency_check('1.1.1.1',443,2)
    assert r['avg_ms'] is None and r['status']=='unavailable' and r['packet_loss_pct']==100
