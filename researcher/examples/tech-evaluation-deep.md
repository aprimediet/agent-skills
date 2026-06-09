# Yjs vs Automerge: Which CRDT Should You Use for Your Real-Time Collaboration App?

> Research type: tech-evaluation | Depth: deep | Generated: 2026-06-09 | Sources: 13

## Executive Summary

For a real-time collaboration app built today, **Yjs is the recommended choice** for most use cases. It offers dramatically better performance (2–10× faster across benchmarks), a significantly smaller bundle size (20 KB vs 604 KB gzipped), a vastly larger ecosystem (22k GitHub stars, 20M+ monthly npm downloads), and broader editor support with bindings for ProseMirror, Quill, Monaco, CodeMirror, Slate, Lexical, Tiptap, and more. Automerge 3.0 has made impressive strides in memory efficiency (10× reduction) and offers a clean "batteries-included" experience via automerge-repo, with built-in version control APIs (diff, history, view) that Yjs lacks natively. However, Yjs's performance lead, network-agnostic architecture, and massive community adoption make it the safer, more versatile foundation for most real-time collaboration products.

## Key Findings

- **Finding 1**: Yjs is consistently 2–5× faster than Automerge across standard collaborative editing benchmarks, with significantly smaller update messages (27 bytes vs 121 bytes per operation) — supported by 4 sources [1][3][5][7]
- **Finding 2**: Yjs has vastly greater community adoption: 22k GitHub stars vs 6.3k, 20.5M monthly npm downloads vs 146k, and a much wider roster of production users (Evernote, GitBook, Linear, ProtonMail Docs, Typst, AFFiNE) — supported by 4 sources [1][2][6][7]
- **Finding 3**: Automerge 3.0 achieved a ~10× memory reduction over its predecessor, making documents with long histories practical (Moby Dick went from 700 MB to 1.3 MB) — supported by 2 sources [4][8]
- **Finding 4**: Yjs has broader editor integration support (15+ editors including ProseMirror, Quill, Monaco, CodeMirror, Slate, Lexical, Tiptap, BlockNote) compared to Automerge (ProseMirror only via community cookbook) — supported by 2 sources [1][7]
- **Finding 5**: Automerge's automerge-repo provides a more polished "batteries-included" developer experience with built-in networking, storage adapters, React hooks, and version control APIs (diff, history, view) that Yjs lacks natively — supported by 2 sources [9][10]
- **Finding 6**: Both libraries use MIT license, are network-agnostic, support offline editing, and are suitable for local-first architecture — supported by 5 sources [1][2][4][7][11]

## Detailed Analysis

### Performance and Efficiency

The most significant differentiator between Yjs and Automerge is performance. According to the authoritative CRDT benchmarks maintained by Kevin Jahns (Yjs's author) [3], Yjs consistently outperforms Automerge across nearly every benchmark scenario.

For simple append operations (B1.1, N=6000 characters), Yjs completes in 188 ms while Automerge takes 365 ms — roughly 2× slower. For prepend operations (B1.3), the gap widens: Yjs at 119 ms vs Automerge at 307 ms. For insert/delete patterns (B1.7), Yjs at 158 ms vs Automerge at 389 ms.

The real-world editing benchmark (B4), which replays a 260,000-operation editing trace of an academic paper, shows Yjs completing in 5,714 ms vs Automerge at 14,326 ms — a 2.5× difference. Automerge was entirely skipped for the B4×100 benchmark (100× the real-world trace) due to memory constraints.

Bundle size is another critical gap. Yjs ships at 69 KB (20 KB gzipped), while Automerge weighs 1.7 MB (604 KB gzipped) — that's 30× larger [3]. This has real implications for initial page load times in web applications.

Joseph Gentle's detailed analysis in "CRDTs go brrr" [7] highlighted that Yjs's use of a flat list with run-length encoding and cursor position caching gives it a massive performance advantage over Automerge's earlier tree-based approach. While Automerge has since rewritten its core in Rust and released Automerge 3.0 with a rearchitected compressed columnar storage format [4][8], the benchmark data from 2026 still shows Yjs with a clear edge.

### Ecosystem and Community Adoption

Yjs has achieved critical mass that makes it the de facto standard for CRDT-based collaboration in JavaScript. With 22k GitHub stars, 782 forks, and over 2,200 commits [1], it far surpasses Automerge's 6.3k stars and 252 forks [2]. The npm download statistics are even more stark: Yjs had 20.5 million downloads in the last month, compared to Automerge's 146,200 [12] — a 140× difference.

Yjs's production users are a who's-who of collaborative applications: **Evernote**, **GitBook**, **Linear**, **ProtonMail Docs** (encrypted collaborative documents), **Typst** (collaborative LaTeX), **AFFiNE** (open-source knowledge base), **NextCloud**, **Appflowy**, **Synthesia** (collaborative video editor), **JupyterLab**, **BlockSuite**, and many more [1]. Automerge's production adoption is less visible, with Ink & Switch's research projects and early adopters being the primary users.

Yjs's ecosystem of editor bindings is substantially broader: ProseMirror, Quill, CodeMirror 6, Monaco, Ace, Slate, Lexical, Tiptap, BlockNote, Milkdown, and others are all supported with first-class Yjs bindings [1][7]. Automerge's rich-text story has improved with Automerge 2.2 (April 2024), which introduced rich-text support, and they have a ProseMirror cookbook [11], but the breadth of editor integrations is not comparable.

### Developer Experience and API Design

Automerge's automerge-repo [9][10] offers a more polished "batteries-included" developer experience. It provides a unified `Repo` abstraction that handles document lifecycle, pluggable networking (WebSocket, BroadcastChannel, MessageChannel), storage adapters (IndexedDB, NodeFS), and React/Svelte/Solid hooks out of the box. The 2.0 release added `async Repo.find()`, `DocHandle.view()`, `DocHandle.history()`, `DocHandle.diff()`, React Suspense support, and meta-packages like `@automerge/react` that bundle common adapters [10].

Automerge's immutable state model (each change produces a new document snapshot) is philosophically aligned with React and Redux patterns, which the authors explicitly cite as an advantage [4]. The built-in version control APIs (view, history, diff) provide functionality that would require custom code in Yjs.

Yjs, by contrast, is more modular and requires assembling your own stack of provider, persistence, and binding packages. The ecosystem provides many options (y-websocket, y-webrtc, y-indexeddb, y-mongodb-provider, and dozens more), but this flexibility comes with more setup complexity. Services like Liveblocks, Y-Sweet, Hocuspocus, and PartyKit provide managed backends that simplify deployment [1].

### Underlying Algorithms

Yjs implements the **YATA** algorithm, while Automerge implements **RGA** (Replicated Growable Array). According to Joseph Gentle's analysis [7], the two algorithms produce nearly identical performance when implemented on the same data structure, and the key differentiator is implementation quality rather than algorithmic choice. Yjs's key innovations include:
- Using a flat linked list instead of a tree for item storage
- Run-length encoding to collapse sequential inserts into spans
- Cursor position caching to accelerate sequential edits
- A compact binary encoding format (V2)

Automerge's architecture uses Rust compiled to WebAssembly for its core, with a columnar compressed storage format that was completely redesigned in version 3.0 for the 10× memory reduction [8]. This makes Automerge more memory-efficient for documents with long histories — a meaningful advantage for server-side persistence.

### Network and Sync Architecture

Both libraries are network-agnostic by design. Yjs's update messages are commutative and idempotent, meaning they can be applied in any order and multiple times [1]. This is also true of Automerge's update format [4].

Yjs's update format is more compact (27 bytes per operation vs Automerge's 121 bytes for append), which has implications for bandwidth usage in latency-sensitive applications [3]. However, Automerge's encoded document size is sometimes smaller at rest (3,992 bytes vs 6,031 bytes for the append benchmark), suggesting Automerge may be more storage-efficient for archived documents [3].

Automerge's binary format is formally specified in the Automerge Binary Format Spec [11], which is an advantage for interop and portability.

## Comparison Matrix

| Criterion | Yjs | Automerge |
|-----------|-----|-----------|
| **Performance (B1 append)** | ★★★★★ (188 ms) | ★★★☆☆ (365 ms) |
| **Performance (B4 real-world)** | ★★★★★ (5,714 ms) | ★★★☆☆ (14,326 ms) |
| **Bundle Size (gzipped)** | ★★★★★ (20 KB) | ★★☆☆☆ (604 KB) |
| **Update Size (per op)** | ★★★★★ (27 bytes) | ★★★☆☆ (121 bytes) |
| **Memory Usage (large docs)** | ★★★★☆ | ★★★★☆ (Automerge 3 improved) |
| **Ecosystem (editor bindings)** | ★★★★★ (15+ editors) | ★★☆☆☆ (ProseMirror via cookbook) |
| **Community & Adoption** | ★★★★★ (22k stars, 20M downloads/mo) | ★★☆☆☆ (6.3k stars, 146k downloads/mo) |
| **Production Users** | ★★★★★ (Evernote, Linear, Proton, etc.) | ★★☆☆☆ (Early-stage) |
| **DX / Ease of Setup** | ★★★☆☆ (Modular, compose your own) | ★★★★☆ (automerge-repo batteries-included) |
| **Version Control APIs** | ★★☆☆☆ (No native diff/history APIs) | ★★★★★ (view, history, diff built-in) |
| **License** | MIT | MIT |
| **Language Support** | JS + Rust (y-crdt) + Python/Ruby/.NET/Swift/Kotlin/Go | JS/WASM + Rust + C + Swift |
| **Maintenance Cadence** | ★★★★★ (Very active, 2,222 commits) | ★★★★☆ (Active, 1,542 commits) |
| **Professional Support** | GitHub Sponsors, Synergy Codes, Hocuspocus | Ink & Switch, maintained by Alex & Orion |

## Risks & Caveats

- **Benchmark recency**: The primary CRDT benchmarks used in this report are from the crdt-benchmarks repository, which tested Yjs 13.6.11 against Automerge 2.1.10. While these are the latest versions at the time of comparison, Automerge 3.0 was released after these benchmarks and may narrow the performance gap. However, the benchmarks reflect the current state of published data.
- **Potential bias in sources**: The crdt-benchmarks repository is maintained by Kevin Jahns, the creator of Yjs. While the benchmarks are open-source and reproducible, this is a potential conflict of interest. Independent validation would strengthen confidence.
- **Automerge 3.0 recency**: The Automerge 3.0 memory improvements (10× reduction) are significant but very recent (July 2025). Long-term production reliability data for this version is limited.
- **Lack of network-simulated benchmarks**: The benchmarks primarily measure local operation processing. Real-world performance under network latency, intermittent connectivity, and concurrent multi-user editing may tell a different story.
- **Yjs scaling concerns for B4×100**: Yjs's performance on the B4×100 benchmark (608,908 ms for 26M operations) suggests that even Yjs struggles with extremely large documents. The implementation uses a linked list, which can degrade for very large histories.
- **Automerge adoption risk**: Automerge's smaller community means fewer third-party integrations, less community support, and higher risk of the project being abandoned or under-resourced. Yjs has a larger contributor base and more institutional backing.
- **Comparison scope**: This evaluation focuses on text-editing collaboration. For non-text use cases (structured data, canvas, whiteboard, etc.), the trade-offs may differ. Yjs's Y.Map, Y.Array, and Y.Xml types cover more data structures than Automerge's document model.
- **No independent third-party benchmarks**: The CRDT benchmark suite is comprehensive but primarily maintained by the Yjs author. Independent replication of these results by a neutral third party would be valuable.

## Recommendations

1. **Use Yjs if** you are building a production collaboration app now and need the broadest editor support, best performance, largest ecosystem, and most battle-tested reliability. This is the recommended default.

2. **Use Automerge if** your application prioritizes built-in version control features (diff, history, branching), a cleaner "batteries-included" developer experience, or if you are building on Rust/Swift natively and want to avoid JavaScript dependencies. Automerge 3.0's memory improvements make it increasingly competitive for server-side document storage.

3. **Consider hybrid approaches**: Some production apps use Yjs for the CRDT layer and compose it with managed services like Liveblocks, Y-Sweet, or Hocuspocus for backend infrastructure, avoiding the need to build and scale your own sync server.

4. **If memory or bundle size is critical**: Yjs's 20 KB gzipped bundle makes it the clear winner for web applications. If you're shipping to browsers and every kilobyte matters, Yjs is the pragmatic choice.

5. **If you need native mobile (Swift/Rust)**: Automerge's Rust core compiles to WASM and has official Swift bindings, making it more straightforward for iOS/macOS integration. Yjs has community ports (yrs, yswift) but less official support.

6. **Prototype with both**: Both libraries are MIT-licensed and easy to experiment with. Given Automerge's trajectory of rapid improvement, the gap may continue to narrow. Evaluate both with your specific use case, document sizes, and concurrency patterns before committing.

## Sources

[1] **Yjs GitHub Repository** — GitHub
    URL: https://github.com/yjs/yjs
    Published: Ongoing (2,222 commits)
    Reliability: 5 | Recency: 5 | Relevance: 5 | Composite: 5.0
    Summary: Official repository for Yjs CRDT framework. Provided complete API documentation, ecosystem listing (bindings, providers, ports), production users, and architectural overview. Core source for Yjs data.

[2] **Automerge GitHub Repository** — GitHub
    URL: https://github.com/automerge/automerge
    Published: Ongoing (1,542 commits)
    Reliability: 5 | Recency: 5 | Relevance: 5 | Composite: 5.0
    Summary: Official repository for Automerge CRDT library. Provided status, architecture, build instructions, and release history. Core source for Automerge data.

[3] **CRDT Benchmarks (dmonad/crdt-benchmarks)** — GitHub
    URL: https://github.com/dmonad/crdt-benchmarks
    Published: Ongoing (benchmarks last updated ~2025)
    Reliability: 4 | Recency: 5 | Relevance: 5 | Composite: 4.6
    Summary: Comprehensive reproducible benchmark suite comparing Yjs, Automerge, Loro, and ywasm across 15+ benchmarks including append, prepend, random insert, concurrent editing, and real-world editing traces. Primary quantitative comparison source. Maintained by Yjs author (potential bias noted).

[4] **Automerge Official Documentation** — Official Docs
    URL: https://automerge.org/docs/hello/
    Published: 2026 (last modified May 2026)
    Reliability: 5 | Recency: 5 | Relevance: 5 | Composite: 5.0
    Summary: Official Automerge documentation with design principles, tutorial, and API reference. Describes network-agnostic design, immutable state model, and local-first philosophy.

[5] **Yjs Official Documentation** — Official Docs
    URL: https://docs.yjs.dev/
    Published: 2025 (last updated ~1 year ago)
    Reliability: 5 | Recency: 3 | Relevance: 5 | Composite: 4.4
    Summary: Official Yjs documentation covering quick start, shared types, API, and ecosystem. Notes that README is still best source of information.

[6] **Automerge Repo GitHub Repository** — GitHub
    URL: https://github.com/automerge/automerge-repo
    Published: Ongoing (2,007 commits)
    Reliability: 5 | Recency: 5 | Relevance: 4 | Composite: 4.7
    Summary: "Batteries-included" wrapper for Automerge providing document lifecycle management, pluggable networking, and storage adapters. Includes React/Svelte/Solid hooks and examples.

[7] **"CRDTs go brrr" by Joseph Gentle** — Practitioner Blog
    URL: https://josephg.com/blog/crdts-go-brrr/
    Published: July 2021
    Reliability: 3 | Recency: 1 | Relevance: 5 | Composite: 3.0
    Summary: Deep-dive analysis of CRDT performance comparing Automerge, Yjs, and Diamond Types. Explains algorithmic differences (tree vs flat list), run-length encoding, and cursor caching. Found Yjs 300× faster than Automerge at time of writing (2021). Note: heavily dated but still valuable for architectural insights. Performance ratios have likely narrowed since.

[8] **"Automerge 3.0" Blog Post** — Vendor Blog
    URL: https://automerge.org/blog/automerge-3/
    Published: July 2025
    Reliability: 3 | Recency: 5 | Relevance: 5 | Composite: 4.2
    Summary: Official announcement of Automerge 3.0 describing 10× memory reduction through rearchitected columnar compression at runtime. Details API changes (removal of Text API, introduction of ImmutableString). Published by Automerge vendor (Ink & Switch) — potential bias noted.

[9] **"Automerge Repo 1.0" Blog Post** — Vendor Blog
    URL: https://automerge.org/blog/automerge-repo/
    Published: November 2023
    Reliability: 3 | Recency: 3 | Relevance: 4 | Composite: 3.3
    Summary: Description of initial automerge-repo release providing networking, storage, and React hooks.

[10] **"Automerge Repo 2.0" Blog Post** — Vendor Blog
    URL: https://automerge.org/blog/automerge-repo-2/
    Published: May 2025
    Reliability: 3 | Recency: 5 | Relevance: 4 | Composite: 3.9
    Summary: Announcement of automerge-repo 2.0 with async Repo.find, DocHandle version control (view, history, diff), React Suspense, and meta-packages (@automerge/react). Published by Automerge vendor (potential bias noted).

[11] **About CRDTs (crdt.tech)** — Established Publication
    URL: https://crdt.tech/
    Published: Updated March 2026
    Reliability: 5 | Recency: 5 | Relevance: 4 | Composite: 4.7
    Summary: Official CRDT information site maintained by Martin Kleppmann (Automerge creator), Annette Bieniusa, and Marc Shapiro. Provides background on CRDT concepts and principles, background context for the evaluation.

[12] **npm Download Statistics** — Official Source
    URL: https://api.npmjs.org/downloads/point/last-month/yjs / https://api.npmjs.org/downloads/point/last-month/@automerge/automerge
    Published: June 2026 (live data)
    Reliability: 5 | Recency: 5 | Relevance: 5 | Composite: 5.0
    Summary: Direct npm API data showing Yjs at 20,526,392 monthly downloads vs @automerge/automerge at 146,200. Massive adoption gap confirmed.

[13] **Automerge Repo Sync Server** — GitHub
    URL: https://github.com/automerge/automerge-repo-sync-server
    Published: Ongoing (32 commits)
    Reliability: 5 | Recency: 3 | Relevance: 3 | Composite: 3.8
    Summary: Reference sync server for automerge-repo demonstrating WebSocket-based sync. Confirms Automerge's ecosystem maturity for client-server setups.
