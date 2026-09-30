#!/usr/bin/env python3
"""cr_api_auth.py — access layer for the EGT lattice API (audit category F).

Signup -> API key -> per-key rate-limited access. SQLite-backed (stdlib), so
accounts / keys / usage persist across restarts.

Security:
  - API keys are stored HASHED (sha256). The plaintext key is returned ONCE at
    signup and is never stored or logged. A lost key cannot be recovered, only
    reissued.
  - Rate limits are per-key (per-minute and per-day), enforced + recorded on each
    protected call. This also protects the SHARED physical rig from being hammered.
  - Loopback (127.0.0.1 / ::1) is treated as trusted INTERNAL by the caller and
    bypasses auth (so the internal harness/campaign keep working). This module
    does not make that decision — the API gate does — but the default limits here
    are for external self-serve users.
"""
import sqlite3, secrets, hashlib, time, os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'api_accounts.db')
DEFAULT_PER_MIN = 30
DEFAULT_PER_DAY = 500


def _conn():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    c = sqlite3.connect(DB, timeout=5)
    c.execute('PRAGMA journal_mode=WAL')
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _conn() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS accounts(
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT, created REAL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS api_keys(
            key_hash TEXT PRIMARY KEY, account_id INTEGER, label TEXT,
            per_min INTEGER, per_day INTEGER, active INTEGER DEFAULT 1, created REAL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS usage(
            id INTEGER PRIMARY KEY AUTOINCREMENT, key_hash TEXT, ts REAL)''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_usage_key_ts ON usage(key_hash, ts)')


def _hash(key):
    return hashlib.sha256(key.encode()).hexdigest()


def create_account(name, email=None, label='default',
                   per_min=DEFAULT_PER_MIN, per_day=DEFAULT_PER_DAY):
    """Create an account + issue one API key. Returns the plaintext key ONCE."""
    key = 'egt_' + secrets.token_urlsafe(32)
    kh = _hash(key)
    now = time.time()
    with _conn() as c:
        aid = c.execute('INSERT INTO accounts(name,email,created) VALUES(?,?,?)',
                        (name, email, now)).lastrowid
        c.execute('INSERT INTO api_keys(key_hash,account_id,label,per_min,per_day,active,created) '
                  'VALUES(?,?,?,?,?,1,?)', (kh, aid, label, per_min, per_day, now))
    return {'api_key': key, 'account_id': aid, 'per_min': per_min, 'per_day': per_day}


def verify_key(key):
    if not key:
        return None
    with _conn() as c:
        row = c.execute('SELECT * FROM api_keys WHERE key_hash=? AND active=1',
                        (_hash(key),)).fetchone()
        return dict(row) if row else None


def check_and_record(key):
    """Verify key + enforce rate limit + record one usage.
    Returns (ok: bool, http_status: int, info: dict)."""
    k = verify_key(key)
    if not k:
        return (False, 401, {'error': 'invalid or missing API key',
                             'how': 'POST /api/v1/signup to get one; then send header X-API-Key: <key>'})
    kh = k['key_hash']
    now = time.time()
    with _conn() as c:
        c.execute('DELETE FROM usage WHERE ts < ?', (now - 86400,))  # prune > 1 day
        n_min = c.execute('SELECT COUNT(*) FROM usage WHERE key_hash=? AND ts>?',
                          (kh, now - 60)).fetchone()[0]
        n_day = c.execute('SELECT COUNT(*) FROM usage WHERE key_hash=? AND ts>?',
                          (kh, now - 86400)).fetchone()[0]
        if n_min >= k['per_min']:
            return (False, 429, {'error': 'rate limit exceeded (per-minute)',
                                 'per_min': k['per_min'], 'retry_after_s': 60})
        if n_day >= k['per_day']:
            return (False, 429, {'error': 'rate limit exceeded (per-day)', 'per_day': k['per_day']})
        c.execute('INSERT INTO usage(key_hash,ts) VALUES(?,?)', (kh, now))
    return (True, 200, {'account_id': k['account_id'],
                        'per_min': k['per_min'], 'per_day': k['per_day'],
                        'used_min': n_min + 1, 'used_day': n_day + 1})


def usage_summary(key):
    k = verify_key(key)
    if not k:
        return None
    kh = k['key_hash']
    now = time.time()
    with _conn() as c:
        n_min = c.execute('SELECT COUNT(*) FROM usage WHERE key_hash=? AND ts>?',
                          (kh, now - 60)).fetchone()[0]
        n_day = c.execute('SELECT COUNT(*) FROM usage WHERE key_hash=? AND ts>?',
                          (kh, now - 86400)).fetchone()[0]
    return {'account_id': k['account_id'], 'per_min': k['per_min'], 'per_day': k['per_day'],
            'used_min': n_min, 'used_day': n_day}


if __name__ == '__main__':
    # tiny self-test
    init_db()
    a = create_account('selftest', per_min=3, per_day=100)
    key = a['api_key']
    assert verify_key(key), 'verify failed'
    assert not verify_key('egt_bogus'), 'bogus accepted'
    r = [check_and_record(key)[0] for _ in range(5)]
    print('create/verify OK; rate (per_min=3):', r, '-> expect [True,True,True,False,False]')
    print('usage:', usage_summary(key))
