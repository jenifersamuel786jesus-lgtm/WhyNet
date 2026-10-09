import ipaddress
import re
import socket
import time
from datetime import datetime, timezone

HOST_RE = re.compile(r'^(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)(?:\.(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?))*\.?$')


def validate_host(value):
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 253:
        raise ValueError('Enter a valid hostname or IP address.')
    value = value.strip().rstrip('.')
    try:
        ipaddress.ip_address(value)
        return value
    except ValueError:
        if not HOST_RE.fullmatch(value):
            raise ValueError('Enter a valid hostname or IP address.')
        return value


def _result(kind, target, status, **kwargs):
    return {'test_type': kind, 'target': target, 'status': status,
            'timestamp': datetime.now(timezone.utc).isoformat(), **kwargs}


def connectivity(timeout=2.5, target='1.1.1.1', port=443):
    start = time.perf_counter()
    try:
        socket.create_connection((target, port), timeout=timeout).close()
        return _result('connectivity', f'{target}:{port}', 'online', latency_ms=round((time.perf_counter()-start)*1000, 2), details={'method':'TCP connect','note':'Checks outbound connectivity from the application host.'})
    except (OSError, TimeoutError) as e:
        return _result('connectivity', f'{target}:{port}', 'offline', latency_ms=None, error=str(e), details={'method':'TCP connect','note':'Failure is confirmed for this target; it does not prove all internet access is down.'})


def dns_check(host='example.com', timeout=2.5):
    host = validate_host(host)
    old_timeout = socket.getdefaulttimeout()
    start = time.perf_counter()
    try:
        socket.setdefaulttimeout(timeout)
        addresses = sorted({item[4][0] for item in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)})
        return _result('dns', host, 'success', latency_ms=round((time.perf_counter()-start)*1000, 2), resolved_ips=addresses, details={'address_count':len(addresses)})
    except (OSError, TimeoutError) as e:
        return _result('dns', host, 'failed', latency_ms=None, error=str(e), details={})
    finally:
        socket.setdefaulttimeout(old_timeout)


def tcp_check(host, port, timeout=2.5):
    host = validate_host(host)
    try:
        port = int(port)
        if not 1 <= port <= 65535: raise ValueError
    except (TypeError, ValueError):
        raise ValueError('Port must be an integer from 1 to 65535.')
    start = time.perf_counter()
    try:
        socket.create_connection((host, port), timeout=timeout).close()
        return _result('tcp', f'{host}:{port}', 'success', latency_ms=round((time.perf_counter()-start)*1000, 2), details={'port':port})
    except socket.timeout as e:
        return _result('tcp', f'{host}:{port}', 'timeout', latency_ms=None, error=str(e) or 'Connection timed out.', details={'port':port})
    except ConnectionRefusedError as e:
        return _result('tcp', f'{host}:{port}', 'refused', latency_ms=round((time.perf_counter()-start)*1000, 2), error=str(e), details={'port':port})
    except OSError as e:
        return _result('tcp', f'{host}:{port}', 'failed', latency_ms=None, error=str(e), details={'port':port})


def latency_check(host='1.1.1.1', port=443, attempts=4, timeout=2.5):
    host = validate_host(host)
    if not 1 <= int(attempts) <= 10: raise ValueError('Attempts must be from 1 to 10.')
    values, failures = [], []
    for _ in range(int(attempts)):
        result = tcp_check(host, port, timeout)
        if result['status'] == 'success': values.append(result['latency_ms'])
        else: failures.append(result.get('error') or result['status'])
    return _result('latency', f'{host}:{int(port)}', 'success' if values else 'unavailable',
        latency_ms=round(sum(values)/len(values),2) if values else None,
        min_ms=round(min(values),2) if values else None, max_ms=round(max(values),2) if values else None,
        avg_ms=round(sum(values)/len(values),2) if values else None,
        packet_loss_pct=round(100*len(failures)/int(attempts),1), successful_attempts=len(values), attempts=int(attempts),
        errors=failures[:3], details={'method':'TCP handshake timing','note':'Not ICMP ping; firewall, routing, server load, and hosted runtime affect results.'})
