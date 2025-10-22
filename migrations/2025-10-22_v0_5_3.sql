-- v0.5.3 Reticulum+ DDL (nodes, links, link_versions)

BEGIN;

-- safety
CREATE TABLE IF NOT EXISTS nodes (
    path   TEXT PRIMARY KEY,
    parent TEXT,
    v1 REAL NOT NULL, v2 REAL NOT NULL, v3 REAL NOT NULL, v4 REAL NOT NULL, v5 REAL NOT NULL,
    label  TEXT,
    weight REAL DEFAULT 0.5,
    meta   TEXT
);
CREATE INDEX IF NOT EXISTS idx_nodes_parent ON nodes(parent);
CREATE INDEX IF NOT EXISTS idx_nodes_path   ON nodes(path);

CREATE TABLE IF NOT EXISTS links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_path TEXT NOT NULL,
    content_id TEXT NOT NULL,
    kind TEXT DEFAULT 'doc',
    score REAL DEFAULT 0.0,
    meta  TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_links_node    ON links(node_path);
CREATE INDEX IF NOT EXISTS idx_links_content ON links(content_id);

-- NEW: versioned links
CREATE TABLE IF NOT EXISTS link_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_path  TEXT NOT NULL,
    content_id TEXT NOT NULL,
    version    INTEGER NOT NULL,
    score REAL DEFAULT 0.0,
    kind  TEXT DEFAULT 'doc',
    meta  TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(node_path, content_id, version)
);
CREATE INDEX IF NOT EXISTS idx_lv_node    ON link_versions(node_path);
CREATE INDEX IF NOT EXISTS idx_lv_content ON link_versions(content_id);

COMMIT;
