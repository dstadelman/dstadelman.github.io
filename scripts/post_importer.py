from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shlex
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable


DEFAULT_CONTAINER_PREFIX = "/opt/data"
ENV_REMOTE = "ARTICLE_REMOTE"
ENV_REMOTE_USER = "ARTICLE_REMOTE_USER"
ENV_REMOTE_HOST = "ARTICLE_REMOTE_HOST"
ENV_REMOTE_DATA_DIR = "ARTICLE_REMOTE_DATA_DIR"
ENV_CONTAINER_DATA_DIR = "ARTICLE_CONTAINER_DATA_DIR"


@dataclass(frozen=True)
class RemoteConfig:
    remote: str
    container_prefix: str
    remote_prefix: str


@dataclass(frozen=True)
class ImportResult:
    output_path: Path
    title: str
    destination: str
    published: bool = False


def load_environment(repo_root: Path) -> None:
    try:
        from dotenv import load_dotenv
    except ImportError as exc:
        raise RuntimeError("python-dotenv is required; run python -m pip install -r requirements.txt") from exc

    load_dotenv(repo_root / ".env")


def resolve_remote_config(args: argparse.Namespace) -> RemoteConfig:
    remote = args.remote or os.getenv(ENV_REMOTE)
    remote_user = args.remote_user or os.getenv(ENV_REMOTE_USER)
    remote_host = args.remote_host or os.getenv(ENV_REMOTE_HOST)
    remote_prefix = args.remote_prefix or os.getenv(ENV_REMOTE_DATA_DIR)
    container_prefix = args.container_prefix or os.getenv(ENV_CONTAINER_DATA_DIR) or DEFAULT_CONTAINER_PREFIX

    missing: list[str] = []
    if not remote:
        if not remote_user:
            missing.append(ENV_REMOTE_USER)
        if not remote_host:
            missing.append(ENV_REMOTE_HOST)
        if remote_user and remote_host:
            remote = f"{remote_user}@{remote_host}"
    if not remote_prefix:
        missing.append(ENV_REMOTE_DATA_DIR)

    if missing:
        names = ", ".join(missing)
        raise RuntimeError(f"missing required .env setting(s): {names}")

    return RemoteConfig(
        remote=remote,
        container_prefix=container_prefix,
        remote_prefix=remote_prefix,
    )


def resolve_remote_source_path(
    source_path: str,
    *,
    container_prefix: str,
    remote_prefix: str,
) -> str:
    """Translate Hermes container paths to the host path visible over SSH."""
    source = source_path.strip()
    if not source:
        raise ValueError("source path is empty")

    container_prefix = container_prefix.rstrip("/")
    remote_prefix = remote_prefix.rstrip("/")

    if source == container_prefix:
        return remote_prefix
    if source.startswith(container_prefix + "/"):
        return remote_prefix + source[len(container_prefix) :]
    if source.startswith(remote_prefix + "/") or source == remote_prefix:
        return source
    if source.startswith("/"):
        return source
    return remote_prefix + "/" + source.lstrip("/")


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_value = ascii_value.lower().replace("'", "")
    ascii_value = re.sub(r"[^a-z0-9]+", "-", ascii_value)
    return ascii_value.strip("-")


def slug_from_source(source_path: str) -> str:
    stem = PurePosixPath(source_path).name
    if stem.lower().endswith(".md"):
        stem = stem[:-3]
    if stem.startswith("content-"):
        stem = stem[len("content-") :]
    slug = slugify(stem)
    if not slug:
        raise ValueError(f"could not derive a slug from {source_path!r}")
    return slug


def title_from_slug(slug: str) -> str:
    acronyms = {
        "ai": "AI",
        "api": "API",
        "gpu": "GPU",
        "llm": "LLM",
        "llms": "LLMs",
        "seo": "SEO",
        "ui": "UI",
        "ux": "UX",
    }
    words = []
    for word in slug.split("-"):
        words.append(acronyms.get(word, word.capitalize()))
    return " ".join(words)


def split_front_matter(text: str) -> tuple[dict[str, str], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text

    end_index = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_index = index
            break

    if end_index is None:
        return {}, text

    metadata: dict[str, str] = {}
    for line in lines[1:end_index]:
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key or re.search(r"\s", key):
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        metadata[key] = value

    body = "\n".join(lines[end_index + 1 :])
    if text.endswith(("\n", "\r\n")):
        body += "\n"
    return metadata, body


def first_markdown_h1(body: str) -> str | None:
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("# ") and not stripped.startswith("## "):
            title = stripped[2:].strip()
            return title or None
        return None
    return None


def strip_leading_h1(body: str) -> str:
    lines = body.splitlines()
    index = 0
    while index < len(lines) and not lines[index].strip():
        index += 1
    if index < len(lines) and lines[index].strip().startswith("# "):
        del lines[index]
        if index < len(lines) and not lines[index].strip():
            del lines[index]
    stripped = "\n".join(lines).strip()
    return stripped + "\n" if stripped else ""


def current_timestamp() -> dt.datetime:
    return dt.datetime.now().astimezone().replace(microsecond=0)


def format_front_matter_date(value: dt.date | dt.datetime) -> str:
    if isinstance(value, dt.datetime):
        if value.tzinfo is None:
            value = value.astimezone()
        return value.strftime("%Y-%m-%d %H:%M:%S %z").strip()
    return value.isoformat()


def filename_date_prefix(value: dt.date | dt.datetime) -> str:
    if isinstance(value, dt.datetime):
        return value.strftime("%Y-%m-%d")
    return value.isoformat()


def build_post_content(
    source_text: str,
    *,
    source_path: str,
    post_date: dt.date | dt.datetime,
    title: str | None = None,
    keep_heading: bool = False,
) -> tuple[str, str, str]:
    metadata, body = split_front_matter(source_text)
    h1_title = first_markdown_h1(body)
    slug = slug_from_source(source_path)
    post_title = title or metadata.get("title") or h1_title or title_from_slug(slug)

    if not keep_heading and title is None and metadata.get("title") is None and h1_title:
        body = strip_leading_h1(body)

    body = body.strip()
    if body:
        body += "\n"

    ordered_metadata: list[tuple[str, str]] = [
        ("layout", "post"),
        ("title", post_title),
        ("date", format_front_matter_date(post_date)),
    ]

    for key, value in metadata.items():
        if key not in {"layout", "title", "date"}:
            ordered_metadata.append((key, value))

    front_matter = ["---"]
    for key, value in ordered_metadata:
        if key == "date":
            rendered_value = value
        else:
            rendered_value = json.dumps(value)
        front_matter.append(f"{key}: {rendered_value}")
    front_matter.extend(["---", ""])

    return "\n".join(front_matter) + body, post_title, slug


def run_command(command: list[str], *, cwd: Path | None = None, timeout: int | None = None) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(command, cwd=cwd, timeout=timeout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def read_remote_file(
    remote: str,
    remote_path: str,
    *,
    remote_prefix: str,
    timeout: int = 30,
) -> tuple[str, str]:
    """Read a remote file over SSH, falling back to a basename search."""
    result = _remote_cat(remote, remote_path, timeout=timeout)
    if result.returncode == 0:
        return result.stdout.decode("utf-8-sig"), remote_path

    basename = PurePosixPath(remote_path).name
    find_command = (
        f"find {shlex.quote(remote_prefix)} -maxdepth 3 -type f "
        f"-name {shlex.quote(basename)} -print -quit"
    )
    find_result = run_command(["ssh", remote, find_command], timeout=timeout)
    found_path = find_result.stdout.decode("utf-8", errors="replace").strip().splitlines()
    if find_result.returncode == 0 and found_path:
        fallback_path = found_path[0]
        fallback_result = _remote_cat(remote, fallback_path, timeout=timeout)
        if fallback_result.returncode == 0:
            return fallback_result.stdout.decode("utf-8-sig"), fallback_path

    stderr = result.stderr.decode("utf-8", errors="replace").strip()
    if find_result.stderr:
        stderr = (stderr + "\n" + find_result.stderr.decode("utf-8", errors="replace").strip()).strip()
    raise RuntimeError(f"could not read {remote_path} from {remote}: {stderr}")


def _remote_cat(remote: str, remote_path: str, *, timeout: int) -> subprocess.CompletedProcess[bytes]:
    command = f"cat -- {shlex.quote(remote_path)}"
    return run_command(["ssh", remote, command], timeout=timeout)


def publish_post(repo_root: Path, post_path: Path, title: str) -> None:
    relative_post = post_path.relative_to(repo_root).as_posix()
    run_checked(["git", "add", relative_post], cwd=repo_root)
    run_checked(["git", "commit", "-m", f"Publish {title}"], cwd=repo_root)
    run_checked(["git", "push"], cwd=repo_root)


def run_checked(command: list[str], *, cwd: Path) -> None:
    result = subprocess.run(command, cwd=cwd)
    if result.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(command)}")


def import_post(
    source_path: str,
    *,
    repo_root: Path,
    remote_config: RemoteConfig,
    destination: str = "draft",
    post_date: dt.date | dt.datetime | None = None,
    title: str | None = None,
    slug: str | None = None,
    force: bool = False,
    dry_run: bool = False,
    publish: bool = False,
    keep_heading: bool = False,
    timeout: int = 30,
) -> ImportResult:
    if destination not in {"draft", "post"}:
        raise ValueError("destination must be 'draft' or 'post'")
    post_date = post_date or current_timestamp()

    remote_path = resolve_remote_source_path(
        source_path,
        container_prefix=remote_config.container_prefix,
        remote_prefix=remote_config.remote_prefix,
    )
    source_text, _ = read_remote_file(
        remote_config.remote,
        remote_path,
        remote_prefix=remote_config.remote_prefix,
        timeout=timeout,
    )

    post_content, post_title, derived_slug = build_post_content(
        source_text,
        source_path=source_path,
        post_date=post_date,
        title=title,
        keep_heading=keep_heading,
    )
    final_slug = slugify(slug) if slug else derived_slug
    if not final_slug:
        raise ValueError("slug is empty")

    output_dir = repo_root / ("_posts" if destination == "post" else "_drafts")
    filename = f"{filename_date_prefix(post_date)}-{final_slug}.md"
    output_path = output_dir / filename

    if output_path.exists() and not force:
        raise FileExistsError(f"{output_path} already exists; pass --force to overwrite it")

    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path.write_text(post_content, encoding="utf-8", newline="\n")
        if publish:
            publish_post(repo_root, output_path, post_title)

    return ImportResult(output_path=output_path, title=post_title, destination=destination, published=publish and not dry_run)


def parse_date(value: str) -> dt.date | dt.datetime:
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return dt.date.fromisoformat(value)
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("date must be YYYY-MM-DD or an ISO datetime") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import a Markdown file from the configured remote machine into _drafts.",
    )
    parser.add_argument("source_path", help="Remote, container, or basename path to the Markdown article")
    parser.add_argument("--remote", help=f"SSH target; overrides {ENV_REMOTE_USER}/{ENV_REMOTE_HOST}")
    parser.add_argument("--remote-user", help=f"SSH username; default from {ENV_REMOTE_USER}")
    parser.add_argument("--remote-host", help=f"SSH host; default from {ENV_REMOTE_HOST}")
    parser.add_argument("--container-prefix", help=f"Container data prefix; default from {ENV_CONTAINER_DATA_DIR} or {DEFAULT_CONTAINER_PREFIX}")
    parser.add_argument("--remote-prefix", help=f"Remote data directory; default from {ENV_REMOTE_DATA_DIR}")
    parser.add_argument("--post", action="store_true", help="Create in _posts instead of _drafts")
    parser.add_argument("--date", type=parse_date, help="Override the YAML date and filename prefix with YYYY-MM-DD or ISO datetime")
    parser.add_argument("--title", help="Override the post title")
    parser.add_argument("--slug", help="Override the post slug")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing draft/post with the same slug")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be created without writing files")
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Commit and push the created file; drafts still are not live until moved to _posts",
    )
    parser.add_argument("--keep-heading", action="store_true", help="Keep a leading H1 in the Markdown body")
    parser.add_argument("--timeout", type=int, default=30, help="SSH timeout in seconds")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    repo_root = Path(__file__).resolve().parents[1]

    try:
        load_environment(repo_root)
        remote_config = resolve_remote_config(args)
        destination = "post" if args.post else "draft"
        result = import_post(
            args.source_path,
            repo_root=repo_root,
            remote_config=remote_config,
            destination=destination,
            post_date=args.date,
            title=args.title,
            slug=args.slug,
            force=args.force,
            dry_run=args.dry_run,
            publish=args.publish,
            keep_heading=args.keep_heading,
            timeout=args.timeout,
        )
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    action = "Would create" if args.dry_run else "Created"
    print(f"{action}: {result.output_path.relative_to(repo_root).as_posix()}")
    print(f"Title: {result.title}")
    if args.publish:
        print("Published: committed and pushed to GitHub" if result.published else "Publish skipped by dry run")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
