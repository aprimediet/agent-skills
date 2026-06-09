# Output Format Reference

This file defines the exact output format for researcher skill reports. Consult this when generating the final output files.

## Markdown Report — `./researcher/{slug}.md`

Use this exact structure:

```markdown
# {Title}

> Research type: {type} | Depth: {depth} | Generated: {date} | Sources: {count}

## Executive Summary

2-4 sentences answering the core question. If this is a comparison, state the recommendation here. If it's an investigation, state the key finding.

## Key Findings

- **Finding 1**: {claim} — supported by {N} sources [1][3][5]
- **Finding 2**: {claim} — supported by {N} sources [2][4]
- **Finding 3**: {claim} — note any disagreement between sources

## Detailed Analysis

### {Theme 1}
{Synthesized analysis with inline citations [N]}

### {Theme 2}
{Synthesized analysis with inline citations [N]}

## Comparison Matrix

{For tech-evaluation type only — omit for other types}

## Risks & Caveats

- What the sources don't cover
- Conflicts of interest in sources (vendor-authored, sponsored content)
- Areas where information is outdated or sparse
- Assumptions made during synthesis

## Recommendations

{Actionable recommendations based on evidence. If the evidence is insufficient for a strong recommendation, say so and suggest what additional research would help.}

## Sources

{Numbered list with full details — see format below}
```

Each source entry in the Sources section:

```markdown
[N] **{Title}** — {Source Type}
    URL: {url}
    Published: {date or "Unknown"}
    Reliability: {1-5} | Recency: {1-5} | Relevance: {1-5} | Composite: {score}
    Summary: {1-2 sentence summary of what this source contributed}
```

## JSON Metadata — `./researcher/{slug}.meta.json`

```json
{
  "title": "Research title",
  "slug": "url-friendly-slug",
  "research_type": "tech-evaluation|product-research|feature-investigation|landscape-analysis",
  "depth": "quick|standard|deep",
  "generated_at": "ISO 8601 timestamp",
  "query": "Original user query",
  "scope_constraints": ["constraint1", "constraint2"],
  "summary": "Executive summary text",
  "findings": [
    {
      "claim": "Finding text",
      "confidence": "high|medium|low",
      "supporting_sources": [1, 3]
    }
  ],
  "comparison_matrix": {
    "criteria": ["Performance", "DX", "Ecosystem", "Maintenance", "License"],
    "options": {
      "Option A": {"Performance": 4, "DX": 3, "Ecosystem": 5, "Maintenance": 4, "License": "MIT"},
      "Option B": {"Performance": 3, "DX": 5, "Ecosystem": 3, "Maintenance": 4, "License": "Apache 2.0"}
    }
  },
  "sources": [
    {
      "id": 1,
      "title": "Source title",
      "url": "https://...",
      "type": "official-docs|github|paper|publication|blog|community|vendor",
      "published": "2025-01-15",
      "scores": {
        "reliability": 5,
        "recency": 4,
        "relevance": 5,
        "composite": 4.7
      },
      "summary": "What this source contributed"
    }
  ],
  "risks": [
    "Risk or caveat description"
  ],
  "recommendations": [
    "Actionable recommendation"
  ]
}
```

## Slug derivation

The `slug` is derived from the research topic: lowercase, hyphens for spaces, max 60 chars. For example, "React vs Vue for enterprise apps" becomes `react-vs-vue-enterprise-apps`.

## Source scoring rubric

| Dimension | 5 | 3 | 1 |
|-----------|---|---|---|
| **Reliability** | Official docs, peer-reviewed, established publication | Practitioner blog, well-known author | Anonymous forum post, vendor marketing |
| **Recency** | Published < 6 months ago | Published 6-18 months ago | Published > 18 months ago |
| **Relevance** | Directly addresses the research question | Tangentially related, provides context | Marginally related |

Weighted composite: `score = reliability * 0.4 + recency * 0.3 + relevance * 0.3`

Sources scoring below 2.0 should be flagged as low-confidence and used only for supplementary context, never as primary evidence.
