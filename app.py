from concurrent.futures import ThreadPoolExecutor
from flask import Flask, jsonify, render_template, request
from config import Config
from database.db import init_db, recent, save_incidents, save_result
from diagnostics.checks import connectivity, dns_check, latency_check, tcp_check, validate_host
from diagnostics.fault_engine import diagnose


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    init_db(app.config['DATABASE'])

    def persist(result):
        return save_result(app.config['DATABASE'], result)

    @app.get('/')
    def index():
        return render_template('index.html')

    @app.get('/api/health')
    def health():
        return jsonify({'status':'ok','service':'WhyNet Live'})

    @app.get('/api/status')
    def status():
        rows = recent(app.config['DATABASE'], 'test_results', 30)
        latest = {}
        for row in rows:
            if row['test_type'] not in latest:
                latest[row['test_type']] = row
        return jsonify({'status':'ok','latest':latest,'updated_at':rows[0]['created_at'] if rows else None})

    @app.post('/api/test/connectivity')
    def test_connectivity():
        return jsonify(persist(connectivity(app.config['CHECK_TIMEOUT'])))

    @app.post('/api/test/dns')
    def test_dns():
        data = request.get_json(silent=True) or {}
        try:
            host = validate_host(data.get('host','example.com'))
        except ValueError as e:
            return jsonify({'error':str(e)}), 400
        return jsonify(persist(dns_check(host, app.config['CHECK_TIMEOUT'])))

    @app.post('/api/test/tcp')
    def test_tcp():
        data = request.get_json(silent=True) or {}
        try:
            host = validate_host(data.get('host','example.com'))
            port = int(data.get('port',443))
            if not 1 <= port <= 65535: raise ValueError('Port must be an integer from 1 to 65535.')
        except (ValueError, TypeError):
            return jsonify({'error':'Enter a valid hostname/IP and a port from 1 to 65535.'}), 400
        return jsonify(persist(tcp_check(host, port, app.config['CHECK_TIMEOUT'])))

    @app.post('/api/test/latency')
    def test_latency():
        data = request.get_json(silent=True) or {}
        try:
            host = validate_host(data.get('host','1.1.1.1'))
            port = int(data.get('port',443))
            attempts = int(data.get('attempts',app.config['LATENCY_ATTEMPTS']))
            if not 1 <= port <= 65535 or not 1 <= attempts <= 10: raise ValueError
        except (ValueError, TypeError):
            return jsonify({'error':'Host, port, or attempts are invalid. Attempts must be 1–10.'}), 400
        return jsonify(persist(latency_check(host,port,attempts,app.config['CHECK_TIMEOUT'])))

    @app.post('/api/diagnostics/run')
    def run_diagnostics():
        data = request.get_json(silent=True) or {}
        try:
            dns_host = validate_host(data.get('dns_host','example.com'))
            tcp_host = validate_host(data.get('tcp_host','example.com'))
            tcp_port = int(data.get('tcp_port',443))
            if not 1 <= tcp_port <= 65535: raise ValueError
        except (ValueError, TypeError):
            return jsonify({'error':'Invalid diagnostic host or port.'}), 400
        timeout = app.config['CHECK_TIMEOUT']
        attempts = app.config['LATENCY_ATTEMPTS']
        tasks = [
            ('connectivity',lambda:connectivity(timeout)),
            ('dns',lambda:dns_check(dns_host,timeout)),
            ('tcp',lambda:tcp_check(tcp_host,tcp_port,timeout)),
            ('latency',lambda:latency_check('1.1.1.1',443,attempts,timeout)),
        ]
        results = []
        with ThreadPoolExecutor(max_workers=app.config['MAX_CONCURRENT_DIAGNOSTICS']) as pool:
            futures = [(name,pool.submit(fn)) for name,fn in tasks]
            for name,future in futures:
                try:
                    results.append(persist(future.result(timeout=timeout*attempts+2)))
                except Exception as e:
                    results.append(persist({'test_type':name,'status':'unavailable','target':None,'latency_ms':None,'error':str(e)}))
        findings = diagnose(results,app.config['HIGH_LATENCY_MS'])
        save_incidents(app.config['DATABASE'],findings)
        return jsonify({'results':results,'diagnoses':findings})

    @app.get('/api/history')
    def history():
        try: limit = max(1,min(200,int(request.args.get('limit',50))))
        except ValueError: limit = 50
        rows = recent(app.config['DATABASE'],'test_results',limit)
        return jsonify({'items':rows})

    @app.get('/api/incidents')
    def incidents():
        rows = recent(app.config['DATABASE'],'incidents',50)
        import json
        for row in rows:
            row['evidence'] = json.loads(row['evidence'])
            row['recommendations'] = json.loads(row['recommendations'])
        return jsonify({'items':rows})

    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=int(__import__('os').getenv('PORT',5000)))
