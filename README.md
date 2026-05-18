# dstadelman.github.io

Jekyll/GitHub Pages article publishing repo.

## Setup

Install the Python helper dependency:

```powershell
python -m pip install -r requirements.txt
```

Create a local `.env` file from `.env.example` and fill in the SSH username, host, and remote article directory. `.env` is ignored by git.

## Quick Import

Run this from the repo root in bash:

```bash
bash ./create_post.sh "/opt/data/content-legal-architect-paradigm.md"
```

Or run the Python entrypoint directly:

```powershell
python ./create_post.py "/opt/data/content-legal-architect-paradigm.md"
```

That command uses the SSH settings from `.env` and creates a draft:

```text
_drafts/YYYY-MM-DD-legal-architect-paradigm.md
```

You can also pass just the filename:

```powershell
python ./create_post.py content-ai-cost-efficiency-2026.md
```

Use `--post` only if you want the helper to create a post directly:

```powershell
python ./create_post.py "/opt/data/content-legal-architect-paradigm.md" --post
```

Useful options:

```text
--post                  Create in _posts instead of _drafts
--date YYYY-MM-DD       Override today's date
--title "Post Title"    Override the detected title
--slug custom-slug      Override the filename slug
--force                 Overwrite an existing draft/post with the same slug
--dry-run               Show what would happen without writing
--keep-heading          Keep a leading # H1 in the post body
```

## Site Setup

GitHub Pages builds this repo with Jekyll and the `minima` theme. Drafts live in `_drafts/` and do not publish. To publish one manually, move it to `_posts/` without changing the filename:

```text
YYYY-MM-DD-post-slug.md
```

More than one post on the same day is fine. Jekyll uses the whole filename, so the slugs just need to be different:

```text
_posts/2026-05-18-first-article.md
_posts/2026-05-18-second-article.md
```

## Tests

Tests use Python's built-in `unittest` framework:

```powershell
python -m unittest
```
