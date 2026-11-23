#!/bin/sh
# I create my virtual environment and I install the packages I pinned. I can run this again.
# I do not overwrite my .env when it already exists.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
cd "$ROOT"
if [ -d /opt/homebrew/opt/postgresql@16/bin ]; then
  PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"
  export PATH
fi
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
if [ -f requirements-dev.txt ]; then
  python -m pip install -r requirements-dev.txt
fi
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example. Set SECRET_KEY and DEMO_STUDENT_PASSWORD before seeding."
fi
echo "Setup finished in $ROOT"
