#!/usr/bin/env bash
# Monthly refresh of the publication links from published sources only (no preprints):
#   1. ORCID: newly published papers not yet in the CV  -> site-src/data/orcid-additions.json
#   2. PMLR / NeurIPS proceedings pages for papers without a DOI
#   3. Crossref BibTeX for any new DOIs
#   4. rebuild and run the site checks
# Then review `git diff`, commit and push. Run from the repository root: tools/monthly_update.sh
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== ORCID"
python3 tools/sync_orcid.py
echo "== Proceedings (PMLR, NeurIPS)"
timeout 900 python3 tools/find_proceedings.py | tail -5 || echo "proceedings search skipped (timeout or network)"
echo "== BibTeX"
python3 tools/fetch_bibtex.py
echo "== Build"
./build.sh
echo "== Checks"
python3 tools/check_site.py
