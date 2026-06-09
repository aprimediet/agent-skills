---
title: Yjs vs Automerge for Real-Time Collaboration
category: researches
slug: yjs-vs-automerge-real-time-collaboration
created: 2025-06-09T10:30:00Z
updated: 2025-06-09T14:22:00Z
tags: ["crdt", "real-time", "collaboration", "yjs", "automerge"]
scope: project
---

# Yjs vs Automerge for Real-Time Collaboration

## Executive Summary

For a real-time collaboration app built today, **Yjs is the recommended choice** for most use cases. It offers better performance, smaller bundle size, and a vastly larger ecosystem.

## Key Findings

- Yjs is 2-5× faster across standard benchmarks with significantly smaller update messages
- Yjs has 140× more npm downloads and broader editor support (15+ editors)
- Automerge 3.0 offers better DX with automerge-repo's batteries-included approach

## Recommendation

Use Yjs for most real-time collaboration apps. Consider Automerge if you need built-in version control APIs or prefer an immutable state model aligned with React/Redux patterns.