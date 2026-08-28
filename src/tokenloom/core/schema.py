"""The on-disk shape, transcribed from `docs/CORE.md`'s *On disk*.

The DDL here is the locked one, verbatim. Nothing is added to it -- no foreign keys, no
indices beyond the keys the document states. Closure is checked by `check.py` rather than
declared, because a checker that trusts the schema checks nothing.
"""

MARKER = "token-loom/nodes-1"

TREE_FILE = "tree.json"
BULK_FILE = "bulk.sqlite"
LOCK_FILE = "lock"

DDL = """
CREATE TABLE vocab (                       -- one row per id ever stored
  token_id INTEGER PRIMARY KEY,
  bytes    BLOB NOT NULL);                 -- may be a fragment of a character

CREATE TABLE sources (
  id   INTEGER PRIMARY KEY,
  kind TEXT NOT NULL,                      -- 'user' | 'model'
  name TEXT NOT NULL,                      -- '' is the unnamed user, and nothing else
  UNIQUE (kind, name));

CREATE TABLE nodes (
  id       INTEGER PRIMARY KEY,
  parent   INTEGER,                        -- NULL for a root
  token_id INTEGER NOT NULL,
  source   INTEGER NOT NULL,
  deleted  INTEGER,                        -- 1 if this node is deleted, else NULL
  UNIQUE (parent, token_id, source));      -- roots are exempt: NULL parents never collide,
                                           -- which is Sources' rule, not an artefact

CREATE TABLE edges (                       -- ranked, not taken
  node     INTEGER NOT NULL,
  source   INTEGER NOT NULL,
  rank     INTEGER NOT NULL,
  token_id INTEGER NOT NULL,
  logprob  REAL NOT NULL,
  PRIMARY KEY (node, source, rank),
  UNIQUE (node, source, token_id));

CREATE TABLE params (
  id   INTEGER PRIMARY KEY,
  json TEXT NOT NULL UNIQUE);              -- canonical: keys sorted, no insignificant whitespace

CREATE TABLE acts (
  id      INTEGER PRIMARY KEY,
  op      TEXT NOT NULL,                   -- 'create' | 'generate' | 'realise'
  source  INTEGER NOT NULL,
  origin  INTEGER,                         -- NULL if the act began a root
  tip     INTEGER,                         -- NULL if the act produced no nodes
  created TEXT NOT NULL,                   -- ISO 8601, UTC, ending 'Z'
  params  INTEGER, seed INTEGER, terminator TEXT,   -- 'generate' only
  rank    INTEGER);                                 -- 'realise' only
"""

OPS = ("create", "generate", "realise")

TERMINATORS = ("eos", "limit", "cancelled", "failed", "aborted", "refused")

#: Terminators of a generation that wrote nothing and can therefore name no tip.
#: `cancelled` may or may not name one, so it is not here.
TERMINATORS_WITHOUT_TIP = ("failed", "aborted", "refused")

KINDS = ("user", "model")
