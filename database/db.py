import json
import os
import sqlite3
from datetime import datetime, timezone


def connect(path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    db = sqlite3.connect(path, timeout=5)
    db.row_factory = sqlite3.Row
    return db


def init_db(path):
    with connect(path) as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS test_results (
          id INTEGER PRIMARY KEY AUTOINCREMENT, test_type TEXT NOT NULL,
          target TEXT, status TEXT NOT NULL, latency_ms REAL,
          details TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_test_created ON test_results(created_at DESC);
        CREATE TABLE IF NOT EXISTS incidents (
          id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT NOT NULL,
          severity TEXT NOT NULL, summary TEXT NOT NULL, evidence TEXT NOT NULL,
          recommendations TEXT NOT NULL, confidence TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        ''')


def save_result(path, result):
    created = result.get('timestamp') or datetime.now(timezone.utc).isoformat()
    with connect(path) as db:
        cur = db.execute('INSERT INTO test_results(test_type,target,status,latency_ms,details,created_at) VALUES(?,?,?,?,?,?)',
            (result['test_type'], result.get('target'), result['status'], result.get('latency_ms'), json.dumps(result), created))
        result['id'] = cur.lastrowid
    return result


def save_incidents(path, diagnoses):
    now = datetime.now(timezone.utc).isoformat()
    with connect(path) as db:
        for d in diagnoses:
            if d['category'] == 'insufficient_evidence':
                continue
            db.execute('INSERT INTO incidents(category,severity,summary,evidence,recommendations,confidence,created_at) VALUES(?,?,?,?,?,?,?)',
                (d['category'], d['severity'], d['symptom'], json.dumps(d['evidence']), json.dumps(d['recommendations']), d['confidence'], now))


def recent(path, table, limit=50):
    if table not in ('test_results', 'incidents'):
        raise ValueError('Unsupported table')
    with connect(path) as db:
        return [dict(r) for r in db.execute(f'SELECT * FROM {table} ORDER BY created_at DESC LIMIT ?', (limit,)).fetchall()]
