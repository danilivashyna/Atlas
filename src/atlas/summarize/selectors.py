# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Evidence selection and deduplication for proportional summarization.

Provides utilities for extracting n-grams, facts, and managing anti-repeat mechanisms.
"""

import re
from typing import List, Set, Tuple, Dict
from collections import Counter


def extract_sentences(text: str) -> List[str]:
    """
    Split text into sentences.
    
    Args:
        text: Input text
        
    Returns:
        List of sentences
    """
    # Simple sentence splitting (handles . ! ?)
    sentences = re.split(r'[.!?]+', text)
    return [s.strip() for s in sentences if s.strip()]


def extract_ngrams(text: str, n: int = 3, max_ngrams: int = 100) -> List[Tuple[str, int]]:
    """
    Extract n-grams from text with frequency counts.
    
    Args:
        text: Input text
        n: N-gram size (default: 3 for trigrams)
        max_ngrams: Maximum number of n-grams to return
        
    Returns:
        List of (ngram, frequency) tuples sorted by frequency
    """
    # Tokenize
    tokens = re.findall(r'\b\w+\b', text.lower())
    
    if len(tokens) < n:
        return []
    
    # Generate n-grams
    ngrams = []
    for i in range(len(tokens) - n + 1):
        ngram = ' '.join(tokens[i:i+n])
        ngrams.append(ngram)
    
    # Count and sort by frequency
    ngram_counts = Counter(ngrams)
    return ngram_counts.most_common(max_ngrams)


def extract_keywords(text: str, top_k: int = 20) -> List[Tuple[str, int]]:
    """
    Extract keywords (important words) from text.
    
    Uses simple frequency-based approach with stopword filtering.
    
    Args:
        text: Input text
        top_k: Number of top keywords to return
        
    Returns:
        List of (keyword, frequency) tuples
    """
    # Simple stopwords (EN/RU)
    stopwords = {
        'the', 'is', 'at', 'which', 'on', 'a', 'an', 'as', 'are', 'was', 'were',
        'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
        'but', 'if', 'or', 'because', 'until', 'while', 'of', 'to', 'from',
        'in', 'out', 'for', 'with', 'by', 'and', 'not', 'can', 'will', 'just',
        'в', 'и', 'на', 'с', 'по', 'не', 'что', 'как', 'это', 'к', 'из',
        'у', 'за', 'от', 'о', 'для', 'до', 'при', 'или', 'но', 'так', 'же'
    }
    
    # Tokenize and filter
    tokens = re.findall(r'\b\w+\b', text.lower())
    filtered = [t for t in tokens if t not in stopwords and len(t) > 2]
    
    # Count and return top-k
    word_counts = Counter(filtered)
    return word_counts.most_common(top_k)


def detect_repeats(pieces: List[str], threshold: float = 0.7) -> Set[int]:
    """
    Detect repeated or near-duplicate text pieces.
    
    Uses simple token overlap to find similar pieces.
    
    Args:
        pieces: List of text pieces (sentences, phrases)
        threshold: Similarity threshold (0.0-1.0)
        
    Returns:
        Set of indices to remove (keeps first occurrence)
    """
    to_remove = set()
    
    # Tokenize all pieces
    tokenized = []
    for piece in pieces:
        tokens = set(re.findall(r'\b\w+\b', piece.lower()))
        tokenized.append(tokens)
    
    # Compare each pair
    for i in range(len(pieces)):
        if i in to_remove:
            continue
            
        for j in range(i + 1, len(pieces)):
            if j in to_remove:
                continue
            
            # Calculate Jaccard similarity
            tokens_i, tokens_j = tokenized[i], tokenized[j]
            if not tokens_i or not tokens_j:
                continue
                
            intersection = len(tokens_i & tokens_j)
            union = len(tokens_i | tokens_j)
            
            if union > 0:
                similarity = intersection / union
                if similarity >= threshold:
                    to_remove.add(j)  # Keep first, remove later duplicates
    
    return to_remove


def deduplicate_pieces(pieces: List[str], threshold: float = 0.7) -> List[str]:
    """
    Remove duplicate pieces from list.
    
    Args:
        pieces: List of text pieces
        threshold: Similarity threshold for considering duplicates
        
    Returns:
        Deduplicated list
    """
    if not pieces:
        return []
    
    to_remove = detect_repeats(pieces, threshold)
    return [p for i, p in enumerate(pieces) if i not in to_remove]


def estimate_tokens(text: str) -> int:
    """
    Rough estimate of token count in text.
    
    Uses simple word-based tokenization as approximation.
    
    Args:
        text: Input text
        
    Returns:
        Estimated token count
    """
    # Simple approximation: ~1.3 tokens per word on average
    words = len(re.findall(r'\b\w+\b', text))
    return int(words * 1.3)


def select_evidence_pieces(
    candidates: List[str],
    target_tokens: int,
    used_pieces: Set[str],
    dedup_threshold: float = 0.7
) -> List[str]:
    """
    Select evidence pieces up to target token count.
    
    Prioritizes diversity and avoids repeats.
    
    Args:
        candidates: Candidate text pieces (sorted by relevance)
        target_tokens: Target token count
        used_pieces: Already used pieces (for anti-repeat)
        dedup_threshold: Threshold for duplicate detection
        
    Returns:
        Selected pieces
    """
    selected = []
    current_tokens = 0
    
    for candidate in candidates:
        # Skip if too similar to already used pieces
        if any(is_similar(candidate, used, dedup_threshold) for used in used_pieces):
            continue
        
        # Estimate tokens
        piece_tokens = estimate_tokens(candidate)
        
        # Check if we have room
        if current_tokens + piece_tokens <= target_tokens:
            selected.append(candidate)
            used_pieces.add(candidate)
            current_tokens += piece_tokens
        elif current_tokens == 0:
            # If nothing selected yet, take at least one piece (truncated)
            truncated = truncate_to_tokens(candidate, target_tokens)
            selected.append(truncated)
            used_pieces.add(truncated)
            break
        else:
            # Target reached
            break
    
    return selected


def is_similar(text1: str, text2: str, threshold: float = 0.7) -> bool:
    """
    Check if two texts are similar.
    
    Args:
        text1: First text
        text2: Second text
        threshold: Similarity threshold
        
    Returns:
        True if texts are similar
    """
    tokens1 = set(re.findall(r'\b\w+\b', text1.lower()))
    tokens2 = set(re.findall(r'\b\w+\b', text2.lower()))
    
    if not tokens1 or not tokens2:
        return False
    
    intersection = len(tokens1 & tokens2)
    union = len(tokens1 | tokens2)
    
    if union == 0:
        return False
    
    similarity = intersection / union
    return similarity >= threshold


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """
    Truncate text to approximately max_tokens.
    
    Args:
        text: Input text
        max_tokens: Maximum tokens
        
    Returns:
        Truncated text
    """
    words = text.split()
    # Approximate: 1.3 tokens per word
    max_words = int(max_tokens / 1.3)
    
    if len(words) <= max_words:
        return text
    
    return ' '.join(words[:max_words]) + '...'


def merge_pieces(pieces: List[str], separator: str = ' ') -> str:
    """
    Merge text pieces into coherent text.
    
    Args:
        pieces: List of text pieces
        separator: Separator between pieces
        
    Returns:
        Merged text
    """
    if not pieces:
        return ""
    
    # Clean and merge
    cleaned = [p.strip() for p in pieces if p.strip()]
    return separator.join(cleaned)
