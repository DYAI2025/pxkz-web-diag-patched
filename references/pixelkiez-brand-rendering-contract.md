# Pixelkiez Brand Rendering Contract

Canonical machine tokens live in `assets/brand-tokens.json`. The detailed renderer contract is `references/brand-rendering-contract-v2.md`.

## Required tokens

- primary display family: `Schibsted Grotesk` requested by the project brand contract;
- data family: `IBM Plex Mono` requested by the project brand contract;
- proof fallback is allowed only when the render receipt marks it explicitly;
- customer release requires exact runtime availability of both requested families;
- body text minimum: 12 pt;
- chart label minimum: 10 pt;
- note/footer minimum: 8.5 pt;
- no font shrinking to fix overflow;
- only colors present in the canonical brand token palette may be used.

## Current runtime status

Both requested families ship manifest-pinned in `assets/fonts/` and resolve from the package first, so exact-font rendering no longer depends on the host. `reports/brand-font-capability.json` records the resolved sources, checksums and manifest SHA-256 of the evaluated candidate. Exact fonts make the strict font gate pass; customer release still requires actual visual and semantic QA bound to the PDF SHA-256. Only the manifest-pinned files may be bundled.
