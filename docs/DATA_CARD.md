# Data Card for Atlas Semantic Space

## Current Version (v0.1.0)

**Status**: Rule-based system, no training data used

The current version of Atlas uses hand-crafted rules and heuristics for encoding/decoding. No machine learning training has been performed, and therefore no training data has been collected or used.

### Vocabulary

- **Source**: Hand-curated by developers
- **Size**: ~100 Russian words
- **License**: Created for this project, MIT License
- **Languages**: Russian (primary), English (limited)
- **Selection Criteria**: Common words representing different semantic categories

## Planned Data Sources (v0.2+)

For future neural network versions, we plan to use the following data sources:

### 1. Wikipedia Dumps

**Dataset**: Wikipedia articles in Russian and English

| Property | Value |
|----------|-------|
| **Source** | https://dumps.wikimedia.org/ |
| **License** | CC BY-SA 3.0 |
| **Languages** | Russian, English |
| **Volume** | ~2M articles (Russian), ~6M articles (English) |
| **Format** | XML dumps, text extracted |
| **Last Updated** | Monthly snapshots available |
| **Attribution** | Required per CC BY-SA 3.0 |

**Preprocessing**:
- Extract plain text from XML
- Remove markup and templates
- Sentence segmentation
- Length filtering (10-500 characters)
- Quality filtering (language detection, encoding validation)

**Usage**: General-purpose semantic knowledge

**Limitations**:
- May contain factual errors
- Reflects contributor biases
- Not representative of conversational language
- Formal, encyclopedic style

### 2. OpenSubtitles Corpus

**Dataset**: Movie and TV show subtitles

| Property | Value |
|----------|-------|
| **Source** | http://opus.nlpl.eu/OpenSubtitles.php |
| **License** | Various (mostly permissive) |
| **Languages** | Russian, English, multilingual |
| **Volume** | ~100M sentence pairs |
| **Format** | Aligned subtitle files |
| **Domain** | Conversational, informal |

**Preprocessing**:
- Alignment verification
- Duplicate removal
- Profanity filtering (optional)
- Speaker diarization (if available)
- Length normalization

**Usage**: Conversational language, emotional expression

**Limitations**:
- Not natural conversation (scripted)
- May contain inappropriate content
- Quality varies by source
- Translation artifacts in subtitles

### 3. Common Crawl (Filtered)

**Dataset**: Web crawl data

| Property | Value |
|----------|-------|
| **Source** | https://commoncrawl.org/ |
| **License** | Various, mostly permissive |
| **Languages** | All languages, filtered for Russian/English |
| **Volume** | Petabytes (we'll use small filtered subset) |
| **Format** | WARC files |
| **Quality** | Highly variable |

**Preprocessing** (Strict filtering):
- Language detection and filtering
- Quality scoring (perplexity, coherence)
- Deduplication (exact and near-duplicate)
- PII filtering
- Profanity filtering
- Length filtering
- Domain filtering (exclude low-quality domains)

**Target Volume**: ~10M high-quality sentences

**Usage**: Diverse language use, modern expressions

**Limitations**:
- Noisy and low-quality content
- Potential copyright issues
- Web-specific biases (social media, news, blogs)
- Temporal biases (reflects crawl date)

### 4. News Corpora

**Dataset**: News articles in Russian and English

**Potential Sources**:
- Russian National Corpus (available sections)
- News API aggregators
- Public news archives

| Property | Value |
|----------|-------|
| **License** | Varies by source (to be determined) |
| **Languages** | Russian, English |
| **Volume** | ~1M articles (target) |
| **Domain** | Formal news text |

**Preprocessing**:
- Article extraction (title, body)
- Date filtering (recent years)
- Topic diversification
- Deduplication
- Quality filtering

**Usage**: Formal language, current events

**Limitations**:
- News-specific biases
- Formal style
- May reflect political/ideological biases
- Event-centric, not conceptual

## Data Filtering and Cleaning

### Language Detection

- **Tool**: langdetect or fastText language ID
- **Threshold**: Confidence > 0.95
- **Languages**: Russian (ru), English (en)

### Profanity Filtering

- **Method**: Blocklist-based filtering
- **Blocklists**: 
  - Russian: Community-curated list
  - English: Standard profanity lists
- **Action**: Remove sentences containing blocked words
- **Limitations**: May miss context-dependent profanity

### PII (Personal Identifiable Information) Filtering

**Detection Methods**:
- Email addresses: Regex pattern matching
- Phone numbers: Pattern matching with country codes
- URLs with personal info
- Named entity recognition (person names)

**Action**: 
- Remove sentences with high PII probability
- Redact specific PII instances in some cases

**Limitations**:
- May have false positives (mentions of public figures)
- May miss creative PII obfuscation
- NER not perfect, especially for Slavic names

### Deduplication

**Exact Duplicates**:
- Hash-based deduplication (MD5 or SHA-1)

**Near Duplicates**:
- MinHash LSH for similarity detection
- Threshold: > 80% similarity
- Keep highest quality instance

### Quality Filtering

**Criteria**:
- Minimum length: 10 characters
- Maximum length: 500 characters (for sentences)
- No excessive punctuation (> 30% of characters)
- No excessive capitalization (> 50% of characters)
- Valid UTF-8 encoding
- Language-specific character ratio

**Perplexity Filtering** (optional):
- Use pre-trained language model
- Remove high-perplexity outliers (bottom 5%)

## Data Volume Summary

| Dataset | Raw Size | After Filtering | License |
|---------|----------|----------------|---------|
| Wikipedia (ru) | ~2M articles | ~5M sentences | CC BY-SA 3.0 |
| Wikipedia (en) | ~6M articles | ~15M sentences | CC BY-SA 3.0 |
| OpenSubtitles | ~100M pairs | ~10M sentences | Various |
| Common Crawl | Petabytes | ~10M sentences | Various |
| News | ~1M articles | ~5M sentences | TBD |
| **Total** | - | **~45M sentences** | Mixed |

**Training/Val/Test Split**:
- Training: 90% (~40M sentences)
- Validation: 5% (~2.5M sentences)
- Test: 5% (~2.5M sentences)

## Bias and Limitations

### Known Biases

1. **Language Bias**:
   - Russian and English only
   - May not generalize to other Slavic languages
   - English likely overrepresented in some sources

2. **Cultural Bias**:
   - Western/European cultural perspective
   - Urban/educated language use
   - Internet user demographics

3. **Temporal Bias**:
   - Reflects language use from specific time period
   - May not capture historical language
   - Slang and neologisms time-dependent

4. **Domain Bias**:
   - Over-representation of encyclopedic and formal text
   - Under-representation of spoken, informal language
   - Technical/scientific language may be underrepresented

5. **Demographic Bias**:
   - Wikipedia contributors are not representative
   - Movie subtitles reflect entertainment industry
   - Web crawl reflects internet user population

### Limitations

1. **Coverage**:
   - Cannot cover all possible meanings
   - Rare words underrepresented
   - Domain-specific terminology limited

2. **Ambiguity**:
   - Polysemous words may have mixed representations
   - Context-dependent meanings may be averaged

3. **Ethical Content**:
   - Despite filtering, may contain biased associations
   - Stereotypes may be encoded in embeddings
   - Harmful associations possible

4. **Quality Variance**:
   - Some sources higher quality than others
   - Noise and errors in web data
   - Translation artifacts in parallel corpora

## Bias Mitigation Strategies

### During Data Collection

- [ ] Diversify sources across domains and styles
- [ ] Balance formal/informal language
- [ ] Include underrepresented demographics where possible
- [ ] Document known limitations

### During Training

- [ ] Monitor for bias in learned representations
- [ ] Use fairness-aware training objectives
- [ ] Test on diverse evaluation sets
- [ ] Ablation studies to identify bias sources

### During Deployment

- [ ] Provide bias warnings in documentation
- [ ] Allow users to report problematic outputs
- [ ] Regular audits of model behavior
- [ ] Clear communication of limitations

## Data Versioning

Each training dataset will be versioned:

```
atlas-data-v1.0.0/
├── train/
│   ├── wikipedia_ru_filtered.jsonl
│   ├── wikipedia_en_filtered.jsonl
│   ├── subtitles_filtered.jsonl
│   └── manifest.json (with SHA-256 hashes)
├── val/
│   └── ...
├── test/
│   └── ...
└── README.md (data card)
```

**Versioning Scheme**:
- Major version: Significant data changes
- Minor version: Additions, minor filtering changes
- Patch version: Bug fixes, metadata updates

## License Compliance

### Attribution Requirements

**Wikipedia (CC BY-SA 3.0)**:
- Attribute Wikipedia and contributors
- Share-alike: Derivative models inherit license
- Provide link to original articles (not feasible for all)

**OpenSubtitles**:
- Check individual subtitle licenses
- Attribute original creators where required

**Common Crawl**:
- Varies by source
- Terms of use compliance required
- May need to exclude certain domains

### License Compatibility

Training data under multiple licenses. Atlas code is MIT, but:
- Models trained on CC BY-SA data may inherit that license
- Clear documentation required
- Consider separate model releases for different license requirements

## Privacy and Security

### PII Handling

- Automated PII detection during preprocessing
- Manual review of sample data
- No intentional collection of personal data
- User consent for any data contribution

### Data Retention

- Training data retained for reproducibility
- Version snapshots frozen and archived
- Raw data not included in model distribution
- Processed data available on request (if licenses permit)

### Security

- Data storage: Encrypted at rest
- Access control: Limited to project maintainers
- Audit logging: Track data access
- Compliance: GDPR/CCPA considerations for EU/US users

## Evaluation Data

### Test Set Composition

Separate test set with known properties:
- Balanced across semantic categories
- Include edge cases and challenging examples
- Multiple annotators for quality
- Disjoint from training data

### Annotation Process

For future human-annotated data:
- Annotation guidelines developed
- Multiple annotators per instance
- Inter-annotator agreement measured (Krippendorff's α)
- Disagreements resolved by consensus or expert

## Updates and Maintenance

### Data Refresh

- Plan for periodic data updates
- Monitor for data drift
- Retrain when performance degrades
- Document update schedule

### Community Contribution

- Accept user-contributed examples (with consent)
- Curated contribution process
- Credit contributors
- Clear terms for contributed data

## Contact

For questions about data:
- Open an issue: https://github.com/danilivashyna/Atlas/issues
- See CONTRIBUTING.md for contribution guidelines

---

**Data Card Version**: 1.0  
**Last Updated**: 2025-01-19  
**Applies to**: Atlas v0.1.0 (rule-based), planning for v0.2.0 (neural)
