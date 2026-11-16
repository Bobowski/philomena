# `just` lists the targets. Install: uv tool install rust-just

set shell := ["bash", "-uo", "pipefail", "-c"]

# load secrets/config from .env (gitignored)
set dotenv-load := true

# run the app with hot reload
dev:
    # `python`, not `uv run python`: the app must be watchfiles' direct child.
    # A nested `uv run` wrapper swallows watchfiles' kill and leaves an orphan.
    uv run watchfiles 'python -m app.main' app/ static/

# run the app once, no reload
serve:
    uv run python -m app.main

# format, fix lint, typecheck, test - run before done; prints only problems
check:
    @uv run ruff format -q .
    @uv run ruff check -q --fix .
    @uv run pyrefly check 2>&1 | { grep -v ' INFO ' || true; }
    @uv run pytest -q --no-header

# the same checks without changes, for CI
ci:
    uv run ruff check .
    uv run ruff format --check .
    uv run pyrefly check
    uv run pytest -q

# run the tests
test *args:
    uv run pytest -q --no-header {{args}}

# refresh AGENTS.md, the skills, and the Cloud Agent files from the latest stario-create
sync:
    uvx stario-create@latest sync

# get the pinned Tailwind CLI; css and css-watch run this first
tailwind:
    #!/usr/bin/env sh
    set -eu
    v=v4.3.3
    bin="$HOME/.cache/tailwindcss/$v/tailwindcss"
    if [ "$(readlink tailwindcss 2>/dev/null)" = "$bin" ] && [ -x "$bin" ]; then exit 0; fi
    case "$(uname -s):$(uname -m)" in
      Darwin:arm64) a=macos-arm64 ;;
      Darwin:x86_64) a=macos-x64 ;;
      Linux:x86_64 | Linux:amd64) a=linux-x64 ;;
      Linux:aarch64 | Linux:arm64) a=linux-arm64 ;;
      *) echo "no Tailwind build for $(uname -s) $(uname -m)" >&2; exit 1 ;;
    esac
    if [ ! -x "$bin" ]; then
      mkdir -p "$(dirname "$bin")"
      curl -fL --retry 3 -o "$bin.part" "https://github.com/tailwindlabs/tailwindcss/releases/download/$v/tailwindcss-$a"
      chmod +x "$bin.part"
      mv "$bin.part" "$bin"
    fi
    ln -sfn "$bin" tailwindcss

# build the stylesheet once
css: tailwind
    ./tailwindcss -i frontend/src/input.css -o static/css/output.css --minify

# rebuild the stylesheet on change; run next to `just dev`
css-watch: tailwind
    ./tailwindcss -i frontend/src/input.css -o static/css/output.css --watch
