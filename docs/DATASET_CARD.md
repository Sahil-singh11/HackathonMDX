# Dataset Card — Lamer Konekte Species Images

## Composition (as of 2026-07-29)
- **60 licensed iNaturalist photos** (12 per species × 5 species), research-grade observations, licences restricted to CC0 / CC-BY / CC-BY-NC at fetch time.
- **8 hero demo images** (CC0/CC-BY only) copied to `data/demo/` and shipped in the repo with attribution.
- **6 synthetic quality-test images** + 1 non-image file (MIT, generated in-repo): sharp/blur/dark/overexposed/tiny/document-like.

## Species
Octopus cyanea, Lethrinus nebulosus, Siganus sutor, Epinephelus merra, Naso unicornis (P0 set; taxonomy of the octopus verified against GBIF/iNaturalist — see `research/VERIFIED_FACTS.md` F1).

## Licensing & redistribution
Per-file licence, creator, source URL, media URL and `redistribution_permission` in `data/manifests/species_images.csv`. CC-BY-NC files stay in gitignored `data/raw/` (evaluation-only, never redistributed). A pytest gate (`test_only_permitted_media_is_git_trackable`) enforces this.

## Splits & leakage control
Split assigned by `sha256(observation_id) % 10` → 70/10/20 train/validation/test; hero images excluded from evaluation splits; synthetic images in a separate `quality_test` split. Leakage tests assert no observation id or file hash crosses splits.

## Known limitations & biases
- Small volume (hackathon-scale); not representative of all Mauritian catch conditions (many photos are in-situ underwater, not catch-on-deck).
- Morisyen names provisional pending human review.
- Locality strings are truncated free text from observers; no precise private coordinates are stored.

## Reproduction
`backend/.venv/bin/python data/scripts/fetch_inaturalist_images.py 12 2` and `data/scripts/generate_synthetic_images.py`.
