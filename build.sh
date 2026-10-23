#!/usr/bin/env bash
# Rebuild georgejpappas.org. Run from anywhere: ./build.sh  — then commit and push.
#
# If the CV source is present locally (cv/resume.tex, with its own cv/build.sh),
# the web CV and the publication list are refreshed from it first. The CV source
# and the full CV never leave this machine: .gitignore keeps everything in cv/
# out of the repository except resume_web.pdf.
set -euo pipefail
cd "$(dirname "$0")"

if [ -f cv/resume.tex ]; then
  if [ -x cv/build.sh ]; then
    echo "== CV: building resume.pdf and resume_web.pdf"
    (cd cv && ./build.sh)
  fi
  echo "== Publications: reading cv/resume.tex"
  python3 tools/allpubs.py cv/resume.tex site-src/data/publications.json
else
  echo "== cv/resume.tex not found: using the committed publication list and web CV"
fi

echo "== Site"
python3 tools/build_site.py

if [ -f cv/resume_web.pdf ] && command -v pdftotext >/dev/null 2>&1; then
  if pdftotext cv/resume_web.pdf - | grep -qi "bode"; then
    echo "STOP: cv/resume_web.pdf mentions the Bode Prize. Rebuild the web CV before pushing." >&2
    exit 1
  fi
fi
echo "Done. Review with: python3 -m http.server 8000  (then open http://localhost:8000)"
