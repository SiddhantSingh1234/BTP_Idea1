# Phase 6 additional references

Primary papers consulted for bounded repair are retained here, with PDF source URLs, SHA-256 hashes, page counts and page-marked extracted text in [manifest.json](manifest.json). [references.bib](references.bib) contains citation entries.

| Reference | Local source / relevant sections | Role |
| --- | --- | --- |
| H. R. Lourenco, O. C. Martin and T. Stutzle, Iterated Local Search, arXiv math/0102188 (2001 manuscript) | [PDF](iterated_local_search_2001.pdf), [text](iterated_local_search_2001.txt), framework, perturbation/acceptance and stopping sections; [arXiv](https://arxiv.org/abs/math/0102188) | Separates neighborhood generation from the acceptance objective; supports explicit strict-better acceptance and finite budgets. Phase6 is a bounded improvement heuristic, not a new global-search theorem. |
| W.-H. Lin, D. B. Tan and J. Cong, Reuse-Aware Compilation for Zoned Quantum Architectures Based on Neutral Atoms, HPCA2025 / arXiv2411.11784 | [PDF](zac_arxiv.pdf), [text](zac_arxiv.txt), SectionV placement/SA and reuse-aware dynamic placement; [arXiv](https://arxiv.org/abs/2411.11784), [author publication](https://vast.cs.ucla.edu/sites/default/files/publications/HPCA25_ZAC-2.pdf) | Move/exchange neighborhoods and future-state uncertainty motivate joint pair proposals and full suffix evaluation. Zoned/global-pulse architecture and its reported gains are not imported into RFT. |
| Lourenco, Martin and Stutzle, Iterated Local Search: Framework and Applications | [Author-hosted manuscript](https://iridia.ulb.ac.be/~stuetzle/publications/LouMarStu10.pdf), Sections2-3.3 | Online primary-source review of acceptance choices. Its strict-better rule supports conservative incumbent retention; Phase6 does not accept uphill moves. The locally archived source is the earlier arXiv manuscript above. |

Previously archived sources are reused: [Phase5 references](../phase05_primary/README.md), especially routing-aware placement and scalable bounded search. The supplied RFT/proposal, Enola, ZAP and Atomique sections are mapped to design choices in [Phase6 source research](../../reports/phase_06/source_research.md). Original PDFs and the internship report are not modified; the internship report is not used.

The author-hosted ILS PDF could not be downloaded with Python certificate verification; the official arXiv source was downloaded using Windows certificate validation. No TLS check was disabled. PDF extraction reports rotated-text omissions in ZAC; the original PDF/official HTML was used for the method review.

Retrieved 29 October2026. No reported gains on a different architecture are treated as this project's results.
