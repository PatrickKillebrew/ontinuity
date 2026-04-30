import sqlite3
import re
import os
import sys
from datetime import datetime
import unicodedata

def clean_text(text):
    """Normalize unicode smart quotes and punctuation."""
    if not text:
        return text
    text = text.replace('\u201c', '"').replace('\u201d', '"')
    text = text.replace('\u2018', "'").replace('\u2019', "'")
    text = text.replace('\u2014', '--').replace('\u2013', '-')
    return text


# ─────────────────────────────────────────────

# extract_to_db.py

# Ontinuity Behavioral Tendency Database

# Extracts session log data into SQLite database

# Usage: python extract_to_db.py <log_file_path> [db_path]

# ─────────────────────────────────────────────

DEFAULT_DB_PATH = “ontinuity_behavioral_data.db”

def init_db(db_path):
“”“Initialize database with three-table schema.”””
conn = sqlite3.connect(db_path)
c = conn.cursor()

```
c.executescript("""
    CREATE TABLE IF NOT EXISTS sessions (
        session_id       TEXT PRIMARY KEY,
        date             TEXT,
        start_time       TEXT,
        end_time         TEXT,
        total_cycles     INTEGER,
        model_a          TEXT,
        model_b          TEXT,
        model_c          TEXT,
        parietal         TEXT,
        knowtext_version TEXT,
        session_outcome  TEXT,
        errors           TEXT
    );

    CREATE TABLE IF NOT EXISTS challenges (
        challenge_id      TEXT PRIMARY KEY,
        session_id        TEXT,
        cycle_number      INTEGER,
        ruling_type       TEXT,
        claim_summary     TEXT,
        grounds_summary   TEXT,
        resolution        TEXT,
        challenger_model  TEXT,
        researcher_model  TEXT,
        FOREIGN KEY (session_id) REFERENCES sessions(session_id)
    );

    CREATE TABLE IF NOT EXISTS signals (
        signal_id         TEXT PRIMARY KEY,
        session_id        TEXT,
        cycle_number      INTEGER,
        signal_value      INTEGER,
        signal_reason     TEXT,
        researcher_tag    TEXT,
        challenger_tag    TEXT,
        FOREIGN KEY (session_id) REFERENCES sessions(session_id)
    );
""")

conn.commit()
return conn
```

def parse_session_header(log_text):
“”“Extract session metadata from log header.”””
meta = {}

```
# Session start/end
start_match = re.search(r'Session start:\s*(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})', log_text)
end_match   = re.search(r'Session end:\s*(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})', log_text)

if start_match:
    meta['date']       = start_match.group(1)
    meta['start_time'] = start_match.group(2).replace('-', ':')
    raw_id             = f"{start_match.group(1)}_{start_match.group(2)}"
    meta['session_id'] = raw_id
else:
    meta['date']       = 'unknown'
    meta['start_time'] = 'unknown'
    meta['session_id'] = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

meta['end_time'] = end_match.group(2).replace('-', ':') if end_match else 'unknown'

# Total cycles
cycles_match = re.search(r'Total cycles:\s*(\d+)', log_text)
meta['total_cycles'] = int(cycles_match.group(1)) if cycles_match else 0

# Model assignments
meta['model_a']  = _extract_model(log_text, 'Model A')
meta['model_b']  = _extract_model(log_text, 'Model B')
meta['model_c']  = _extract_model(log_text, 'Model C')
meta['parietal'] = _extract_model(log_text, 'Projenius')  # Projenius used as fallback

# Knowtext version
kv_match = re.search(r'Knowtext version:\s*(KNOWTEXT SCHEMA VERSION:\s*[\d.]+)', log_text)
meta['knowtext_version'] = kv_match.group(1).strip() if kv_match else 'unknown'

# Errors section
errors_match = re.search(r'ERRORS:\s*(.*?)(?=\Z)', log_text, re.DOTALL)
if errors_match:
    errors_text = errors_match.group(1).strip()
    meta['errors'] = errors_text if errors_text and errors_text.lower() != 'none' else None
else:
    meta['errors'] = None

return meta
```

def _extract_model(log_text, role_name):
“”“Extract model name for a given role.”””
pattern = rf’{re.escape(role_name)}:\s*(.+)’
match = re.search(pattern, log_text)
return match.group(1).strip() if match else ‘unknown’

def parse_status_tags(log_text):
“””
Parse STATUS TAG SEQUENCE into dict:
{ cycle_number: {‘a’: tag, ‘b’: tag} }
“””
tags = {}
section_match = re.search(
r’STATUS TAG SEQUENCE:(.*?)(?=FRICTION SIGNAL SEQUENCE:|$)’,
log_text, re.DOTALL
)
if not section_match:
return tags

```
for line in section_match.group(1).split('\n'):
    line = line.strip()
    a_match = re.match(r'Cycle\s+(\d+)\s+A:\s+(\S+)', line)
    b_match = re.match(r'Cycle\s+(\d+)\s+B:\s+(\S+)', line)
    if a_match:
        cycle = int(a_match.group(1))
        tags.setdefault(cycle, {})['a'] = a_match.group(2)
    elif b_match:
        cycle = int(b_match.group(1))
        tags.setdefault(cycle, {})['b'] = b_match.group(2)

return tags
```

def parse_friction_signals(log_text):
“””
Parse FRICTION SIGNAL SEQUENCE into dict:
{ cycle_number: {‘value’: int, ‘reason’: str} }
“””
signals = {}
section_match = re.search(
r’FRICTION SIGNAL SEQUENCE:(.*?)(?=CHALLENGE EVENTS:|$)’,
log_text, re.DOTALL
)
if not section_match:
return signals

```
for line in section_match.group(1).split('\n'):
    line = line.strip()
    m = re.match(r'Cycle\s+(\d+):\s+SIGNAL\s+(\d+)\s*[-–]\s*(.*)', line)
    if m:
        signals[int(m.group(1))] = {
            'value':  int(m.group(2)),
            'reason': m.group(3).strip()
        }

return signals
```

def parse_challenge_events(log_text):
“””
Parse CHALLENGE EVENTS section into list of dicts.
Each dict: { cycle, ruling_type, claim_summary,
grounds_summary, resolution }
“””
events = []
section_match = re.search(
r’CHALLENGE EVENTS:(.*?)(?=SESSION LEDGER:|$)’,
log_text, re.DOTALL
)
if not section_match:
return events

```
section = section_match.group(1)

# Split on cycle markers
blocks = re.split(r'(?=Cycle\s+\d+:)', section)

for block in blocks:
    block = block.strip()
    if not block:
        continue

    cycle_match = re.match(r'Cycle\s+(\d+):', block)
    if not cycle_match:
        continue

    cycle_num = int(cycle_match.group(1))
    content   = block[cycle_match.end():].strip()

    # Determine ruling type
    ruling_type = _extract_ruling_type(content)

    # Extract claim summary (first substantial sentence after ruling tag)
    claim_summary = _extract_claim_summary(content)

    # Extract grounds
    grounds_summary = _extract_grounds(content)

    # Resolution text for RESOLVED/ESCALATED blocks
    resolution = _extract_resolution(content)

    events.append({
        'cycle':           cycle_num,
        'ruling_type':     ruling_type,
        'claim_summary':   claim_summary[:500] if claim_summary else None,
        'grounds_summary': grounds_summary[:500] if grounds_summary else None,
        'resolution':      resolution[:500] if resolution else None,
    })

return events
```

def _extract_ruling_type(content):
“”“Identify the ruling type from block content.”””
upper = content.upper()
if ‘[RULING: UPHOLD]’      in upper: return ‘UPHOLD’
if ‘[RULING: REJECT]’      in upper: return ‘REJECT’
if ‘[RULING: PURSUE BOTH]’ in upper: return ‘PURSUE_BOTH’
if ‘[RULING: ESCALATE]’    in upper: return ‘ESCALATE’
if ‘RESOLVED’              in upper: return ‘RESOLVED’
if ‘ESCALATED’             in upper: return ‘ESCALATED’
if ‘AUTO-CHECKPOINT’       in upper: return ‘AUTO_CHECKPOINT’
return ‘UNKNOWN’

def _extract_claim_summary(content):
“”“Extract claim being challenged — first substantive sentence.”””
# Look for explicit “claim” or “disputed claim” pattern
patterns = [
r’(?:disputed claim|claim challenged|you claim)[:\s]+(.{20,200}?)(?:\n|$)’,
r’(?:challenge|challenges)[:\s]+(.{20,200}?)(?:\n|$)’,
]
for p in patterns:
m = re.search(p, content, re.IGNORECASE)
if m:
return m.group(1).strip()

```
# Fallback: first non-tag sentence
lines = [l.strip() for l in content.split('\n')
         if l.strip() and not l.strip().startswith('[')]
return lines[0][:200] if lines else None
```

def _extract_grounds(content):
“”“Extract grounds for challenge.”””
m = re.search(r’(?:grounds?|grounds? for challenge)[:\s]+(.{20,400}?)(?:\n\n|\Z)’,
content, re.IGNORECASE | re.DOTALL)
if m:
return m.group(1).strip()

```
# Fallback: second paragraph
paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
return paragraphs[1][:400] if len(paragraphs) > 1 else None
```

def _extract_resolution(content):
“”“Extract resolution text for RESOLVED/ESCALATED blocks.”””
m = re.search(r’(?:RESOLVED|ESCALATED)\s*[—–-]\s*(.+)’,
content, re.DOTALL)
return m.group(1).strip()[:400] if m else None

def determine_session_outcome(log_text, total_cycles):
“””
Classify session outcome from log content.
“””
log_upper = log_text.upper()

```
# Fabrication: very short session, no challenges
challenge_count = len(re.findall(r'\[RULING:', log_text))
if total_cycles <= 6 and challenge_count == 0:
    return 'fabrication_detected'

# Finding produced: SESSION_END with substantive work product
if 'SESSION_END' in log_upper and challenge_count > 0:
    if 'STRUCTURAL BLIND SPOT' in log_upper or \
       'FINDING' in log_upper or \
       'CONFIRMED' in log_upper:
        return 'finding_produced'

# Category error: repeated ESCALATE on same construct
escalate_count = log_text.upper().count('[RULING: ESCALATE]')
if escalate_count >= 3:
    return 'category_error_found'

# Deadlock: forward progress blocked message
if 'FORWARD PROGRESS IS BLOCKED' in log_upper:
    return 'deadlock_reached'

# Default for completed sessions
if 'SESSION_END' in log_upper:
    return 'completed'

return 'incomplete'
```

def extract_and_store(log_text, db_path=DEFAULT_DB_PATH):
“””
Main entry point. Parse log_text and write to database.
Returns dict with counts of rows inserted.
“””
log_text = clean_text(log_text)
conn = init_db(db_path)
c    = conn.cursor()

```
# ── Parse ──────────────────────────────────────
meta     = parse_session_header(log_text)
tags     = parse_status_tags(log_text)
signals  = parse_friction_signals(log_text)
events   = parse_challenge_events(log_text)
outcome  = determine_session_outcome(log_text, meta['total_cycles'])

session_id = meta['session_id']

# Check for duplicate
existing = c.execute(
    "SELECT session_id FROM sessions WHERE session_id = ?",
    (session_id,)
).fetchone()

if existing:
    print(f"Session {session_id} already exists in database. Skipping.")
    conn.close()
    return {'sessions': 0, 'challenges': 0, 'signals': 0}

# ── Insert session row ──────────────────────────
c.execute("""
    INSERT INTO sessions VALUES
    (?,?,?,?,?,?,?,?,?,?,?,?)
""", (
    session_id,
    meta['date'],
    meta['start_time'],
    meta['end_time'],
    meta['total_cycles'],
    meta['model_a'],
    meta['model_b'],
    meta['model_c'],
    meta['parietal'],
    meta['knowtext_version'],
    outcome,
    meta['errors'],
))

# ── Insert challenge rows ───────────────────────
challenge_count = 0
for i, event in enumerate(events):
    challenge_id = f"{session_id}-ch{i+1:03d}"
    c.execute("""
        INSERT OR IGNORE INTO challenges VALUES
        (?,?,?,?,?,?,?,?,?)
    """, (
        challenge_id,
        session_id,
        event['cycle'],
        event['ruling_type'],
        event['claim_summary'],
        event['grounds_summary'],
        event['resolution'],
        meta['model_b'],   # challenger
        meta['model_a'],   # researcher
    ))
    challenge_count += 1

# ── Insert signal rows ──────────────────────────
signal_count = 0
for cycle_num, sig in signals.items():
    signal_id = f"{session_id}-sig{cycle_num:03d}"
    cycle_tags = tags.get(cycle_num, {})
    c.execute("""
        INSERT OR IGNORE INTO signals VALUES
        (?,?,?,?,?,?,?)
    """, (
        signal_id,
        session_id,
        cycle_num,
        sig['value'],
        sig['reason'],
        cycle_tags.get('a'),
        cycle_tags.get('b'),
    ))
    signal_count += 1

conn.commit()
conn.close()

return {
    'sessions':   1,
    'challenges': challenge_count,
    'signals':    signal_count,
    'session_id': session_id,
    'outcome':    outcome,
}
```

# ─────────────────────────────────────────────

# CLI entry point

# ─────────────────────────────────────────────

if **name** == ‘**main**’:
if len(sys.argv) < 2:
print(“Usage: python extract_to_db.py <log_file_path> [db_path]”)
sys.exit(1)

```
log_path = sys.argv[1]
db_path  = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_DB_PATH

if not os.path.exists(log_path):
    print(f"Error: log file not found: {log_path}")
    sys.exit(1)

with open(log_path, 'r', encoding='utf-8') as f:
    log_text = f.read()

result = extract_and_store(log_text, db_path)

print(f"Database updated: {db_path}")
print(f"  Session:    {result.get('session_id', 'none')}")
print(f"  Outcome:    {result.get('outcome', 'unknown')}")
print(f"  Challenges: {result['challenges']} rows")
print(f"  Signals:    {result['signals']} rows")
```
