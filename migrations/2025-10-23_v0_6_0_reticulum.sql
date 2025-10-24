-- Migration: Reticulum v0.6.0 - Link versioning and backref tracking
-- Created: 2025-10-23
-- Purpose: Add versioned links from nodes to content with recency scoring and reverse navigation

BEGIN;

-- Versioned links: node -> content with score, kind, metadata
-- Supports tracking multiple versions of the same link with different scores
CREATE TABLE IF NOT EXISTS link_versions (
  node_path   TEXT NOT NULL,
  content_id  TEXT NOT NULL,
  version     INTEGER NOT NULL,
  score       REAL NOT NULL,         -- base weight (without time decay)
  kind        TEXT,                  -- content type, optional
  meta        TEXT,                  -- JSON as string
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (node_path, content_id, version)
);

-- Index for fast lookups by content_id (latest versions first)
CREATE INDEX IF NOT EXISTS ix_linkv_content ON link_versions (content_id, version DESC);

-- Index for fast lookups by node_path (most recent first)
CREATE INDEX IF NOT EXISTS ix_linkv_node    ON link_versions (node_path, created_at DESC);

-- Backward references: tracks which nodes are reached from a given content
-- Used for reverse navigation and popularity ranking
CREATE TABLE IF NOT EXISTS link_backrefs (
  content_id   TEXT NOT NULL,
  node_path    TEXT NOT NULL,
  hit_count    INTEGER NOT NULL DEFAULT 0,
  last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (content_id, node_path)
);

-- Index for fast lookups and sorting by hit_count (popular nodes first)
CREATE INDEX IF NOT EXISTS ix_backref_content ON link_backrefs (content_id, hit_count DESC);

-- Index for fast updates by (content_id, node_path)
CREATE INDEX IF NOT EXISTS ix_backref_node ON link_backrefs (node_path, hit_count DESC);

COMMIT;
