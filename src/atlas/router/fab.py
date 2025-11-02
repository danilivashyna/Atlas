"""
Atlas β — FAB (Filter-and-Blend) Router

Stateless routing layer for multi-level semantic search.
Implements deterministic fusion: RRF (Reciprocal Rank Fusion) and max_sim.

Version: 0.2.0-beta

⚠️ SCOPE: FAB is a pure data routing layer, NOT a feedback or learning loop.
- Stateless: no hidden state, no caching between calls
- Deterministic: same input → same output (RRF k=60, max_sim)
- No online learning, no self-modification
- All parameters git-tracked in configs/
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Literal


@dataclass
class SearchHit:
    """Single search hit from one hierarchical level."""

    level: Literal["sentence", "paragraph", "document"]
    id: str  # e.g., "s:123", "p:45", "d:1"
    score: float  # Cosine similarity or other distance
    metadata: Dict = field(default_factory=dict)


@dataclass
class FusionResult:
    """Result after multi-level fusion."""

    hit: SearchHit
    fused_score: float
    rank: int  # 1-indexed rank after fusion
    trace: Dict = field(default_factory=dict)  # Debug info: per-level ranks, raw scores, etc.


class FABRouter:
    """
    Filter-and-Blend router for multi-level search.

    Stateless routing layer that:
    1. Filters: queries multiple index levels (sent/para/doc)
    2. Blends: fuses results using deterministic algorithms (RRF, max_sim)

    ⚠️ Safety boundaries:
    - No state between calls (stateless)
    - No learning or adaptation (deterministic)
    - No config mutation (read-only)
    - Reproducible via unit tests
    """

    def __init__(self, rrf_k: int = 60):
        """
        Initialize FAB router.

        Args:
            rrf_k: RRF constant (default 60, per TZ_ATLAS_BETA.md)

        Notes:
            - rrf_k should be git-tracked in configs/api/routes.yaml
            - Stateless: no instance state beyond immutable params
        """
        self.rrf_k = rrf_k

    def route(
        self,
        level_hits: Dict[str, List[SearchHit]],
        fusion_method: Literal["RRF", "max_sim"] = "RRF",
        top_k: int = 7,
        debug: bool = False,
    ) -> List[FusionResult]:
        """
        Route query across multiple levels and fuse results.

        Args:
            level_hits: Pre-retrieved hits per level {"sentence": [...], "paragraph": [...], ...}
            fusion_method: "RRF" (Reciprocal Rank Fusion) or "max_sim" (max similarity)
            top_k: Number of results to return after fusion
            debug: Include trace info in FusionResult

        Returns:
            List of FusionResult, sorted by fused_score (descending)

        Notes:
            - Stateless: no side effects
            - Deterministic: same input → same output
            - RRF formula: score = Σ 1/(rank + k) for k=60
            - max_sim: score = max(cosine_similarity across levels)
        """
        if fusion_method == "RRF":
            return self._fuse_rrf(level_hits, top_k=top_k, debug=debug)
        elif fusion_method == "max_sim":
            return self._fuse_max_sim(level_hits, top_k=top_k, debug=debug)
        else:
            raise ValueError(f"Unknown fusion method: {fusion_method}")

    def _fuse_rrf(
        self,
        level_hits: Dict[str, List[SearchHit]],
        top_k: int,
        debug: bool,
    ) -> List[FusionResult]:
        """
        Fuse hits using Reciprocal Rank Fusion (RRF).

        Args:
            level_hits: Per-level hits (pre-sorted by score descending)
            top_k: Number of results to return
            debug: Include trace info

        Returns:
            Ranked list of FusionResult

        Algorithm:
            RRF_score(hit_id) = Σ_{level} 1 / (rank_in_level + k)
            where k = self.rrf_k (default 60)

        Notes:
            - Deterministic: ranks are stable given same input order
            - No randomness, no ties broken randomly
            - If multiple hits have same ID, they're treated as separate (should not happen)
        """
        # Aggregate RRF scores across levels
        rrf_scores: Dict[str, float] = defaultdict(float)
        hit_by_id: Dict[str, SearchHit] = {}
        traces: Dict[str, Dict] = defaultdict(dict)

        for level, hits in level_hits.items():
            for rank, hit in enumerate(hits, start=1):
                hit_id = hit.id
                rrf_contrib = 1.0 / (rank + self.rrf_k)
                rrf_scores[hit_id] += rrf_contrib
                hit_by_id[hit_id] = hit

                if debug:
                    if "per_level_ranks" not in traces[hit_id]:
                        traces[hit_id]["per_level_ranks"] = {}
                    traces[hit_id]["per_level_ranks"][level] = rank
                    traces[hit_id][f"rrf_contrib_{level}"] = rrf_contrib

        # Sort by RRF score descending
        ranked = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        # Build FusionResult objects
        results = []
        for global_rank, (hit_id, fused_score) in enumerate(ranked[:top_k], start=1):
            hit = hit_by_id[hit_id]
            trace = traces[hit_id] if debug else {}
            if debug:
                trace["fusion_method"] = "RRF"
                trace["rrf_k"] = self.rrf_k
                trace["fused_score"] = fused_score

            results.append(FusionResult(
                hit=hit,
                fused_score=fused_score,
                rank=global_rank,
                trace=trace
            ))

        return results

    def _fuse_max_sim(
        self,
        level_hits: Dict[str, List[SearchHit]],
        top_k: int,
        debug: bool,
    ) -> List[FusionResult]:
        """
        Fuse hits using max similarity across levels.

        Args:
            level_hits: Per-level hits (pre-sorted by score descending)
            top_k: Number of results to return
            debug: Include trace info

        Returns:
            Ranked list of FusionResult

        Algorithm:
            max_sim_score(hit_id) = max_{level} score_in_level

        Notes:
            - Deterministic: takes max score per hit_id
            - If hit appears in multiple levels, uses highest score
        """
        # Aggregate max similarity scores
        max_scores: Dict[str, float] = {}
        hit_by_id: Dict[str, SearchHit] = {}
        traces: Dict[str, Dict] = defaultdict(dict)

        for level, hits in level_hits.items():
            for hit in hits:
                hit_id = hit.id
                if hit_id not in max_scores or hit.score > max_scores[hit_id]:
                    max_scores[hit_id] = hit.score
                    hit_by_id[hit_id] = hit

                if debug:
                    if "per_level_scores" not in traces[hit_id]:
                        traces[hit_id]["per_level_scores"] = {}
                    traces[hit_id]["per_level_scores"][level] = hit.score

        # Sort by max score descending
        ranked = sorted(max_scores.items(), key=lambda x: x[1], reverse=True)

        # Build FusionResult objects
        results = []
        for global_rank, (hit_id, fused_score) in enumerate(ranked[:top_k], start=1):
            hit = hit_by_id[hit_id]
            trace = traces[hit_id] if debug else {}
            if debug:
                trace["fusion_method"] = "max_sim"
                trace["fused_score"] = fused_score

            results.append(FusionResult(
                hit=hit,
                fused_score=fused_score,
                rank=global_rank,
                trace=trace
            ))

        return results


def create_fab_router(rrf_k: int = 60) -> FABRouter:
    """
    Factory function to create FAB router with config-driven parameters.

    Args:
        rrf_k: RRF constant (should come from configs/api/routes.yaml)

    Returns:
        FABRouter instance

    Notes:
        - Call this from API routes or ConfigLoader integration
        - rrf_k should be read from config, not hardcoded
    """
    return FABRouter(rrf_k=rrf_k)
