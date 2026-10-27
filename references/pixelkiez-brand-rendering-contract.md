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

The bundled `reports/brand-font-capability.json` records that IBM Plex Mono resolves exactly while Schibsted Grotesk is not present in the current runtime and an approved proof fallback is used. Therefore proof rendering is possible, but exact-font customer release remains blocked until the runtime supplies the requested display family. Font binaries are never bundled in the Skill.
