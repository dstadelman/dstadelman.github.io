import datetime as dt
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.post_importer import (
    RemoteConfig,
    build_post_content,
    filename_date_prefix,
    format_front_matter_date,
    import_post,
    resolve_remote_source_path,
    slug_from_source,
    title_from_slug,
)


class PostImporterTests(unittest.TestCase):
    def test_maps_container_data_path_to_remote_host_path(self):
        resolved = resolve_remote_source_path(
            "/container/data/content-legal-architect-paradigm.md",
            container_prefix="/container/data",
            remote_prefix="/remote/data",
        )

        self.assertEqual(
            resolved,
            "/remote/data/content-legal-architect-paradigm.md",
        )

    def test_relative_source_uses_remote_data_prefix(self):
        resolved = resolve_remote_source_path(
            "content-ai-cost-efficiency-2026.md",
            container_prefix="/container/data",
            remote_prefix="/remote/data",
        )

        self.assertEqual(
            resolved,
            "/remote/data/content-ai-cost-efficiency-2026.md",
        )

    def test_slug_strips_content_prefix(self):
        self.assertEqual(
            slug_from_source("/opt/data/content-legal-architect-paradigm.md"),
            "legal-architect-paradigm",
        )

    def test_title_from_slug_preserves_common_acronyms(self):
        self.assertEqual(
            title_from_slug("ai-cost-efficiency-gpu"),
            "AI Cost Efficiency GPU",
        )

    def test_build_post_uses_leading_h1_as_title_and_removes_duplicate_heading(self):
        content, title, slug = build_post_content(
            "# The Legal Architect Paradigm\n\nBody text.\n",
            source_path="/opt/data/content-legal-architect-paradigm.md",
            post_date=dt.date(2026, 5, 18),
        )

        self.assertEqual(title, "The Legal Architect Paradigm")
        self.assertEqual(slug, "legal-architect-paradigm")
        self.assertIn('title: "The Legal Architect Paradigm"', content)
        self.assertIn("date: 2026-05-18", content)
        self.assertNotIn("# The Legal Architect Paradigm", content)
        self.assertTrue(content.endswith("Body text.\n"))

    def test_formats_datetime_for_jekyll_front_matter_and_filename(self):
        timestamp = dt.datetime(2026, 5, 18, 14, 30, 5, tzinfo=dt.timezone(dt.timedelta(hours=-6)))

        self.assertEqual(format_front_matter_date(timestamp), "2026-05-18 14:30:05 -0600")
        self.assertEqual(filename_date_prefix(timestamp), "2026-05-18")

    def test_build_post_preserves_extra_front_matter(self):
        content, title, _ = build_post_content(
            "---\ntitle: Existing Title\ntags: ai law\n---\n\nBody.\n",
            source_path="content-legal-industry-ai-impact.md",
            post_date=dt.date(2026, 5, 18),
        )

        self.assertEqual(title, "Existing Title")
        self.assertIn('title: "Existing Title"', content)
        self.assertIn('tags: "ai law"', content)

    def test_build_draft_includes_date_front_matter(self):
        content, _, _ = build_post_content(
            "Draft body.\n",
            source_path="content-fast-publishing.md",
            post_date=dt.datetime(2026, 5, 18, 14, 30, 5, tzinfo=dt.timezone(dt.timedelta(hours=-6))),
        )

        self.assertIn('layout: "post"', content)
        self.assertIn("date: 2026-05-18 14:30:05 -0600", content)

    def test_import_defaults_to_drafts_directory(self):
        remote_config = RemoteConfig(
            remote="writer@example",
            container_prefix="/container/data",
            remote_prefix="/remote/data",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            with patch(
                "scripts.post_importer.read_remote_file",
                return_value=("Draft body.\n", "/remote/data/content-fast-publishing.md"),
            ):
                result = import_post(
                    "/container/data/content-fast-publishing.md",
                    repo_root=repo_root,
                    remote_config=remote_config,
                    post_date=dt.datetime(2026, 5, 18, 14, 30, 5),
                )

            self.assertEqual(result.destination, "draft")
            self.assertEqual(result.output_path, repo_root / "_drafts" / "2026-05-18-fast-publishing.md")
            self.assertTrue(result.output_path.exists())

    def test_import_can_create_dated_posts_for_manual_override(self):
        remote_config = RemoteConfig(
            remote="writer@example",
            container_prefix="/container/data",
            remote_prefix="/remote/data",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            with patch(
                "scripts.post_importer.read_remote_file",
                return_value=("Post body.\n", "/remote/data/content-first-post.md"),
            ):
                result = import_post(
                    "/container/data/content-first-post.md",
                    repo_root=repo_root,
                    remote_config=remote_config,
                    destination="post",
                    post_date=dt.datetime(2026, 5, 18, 14, 30, 5),
                )

            self.assertEqual(result.output_path, repo_root / "_posts" / "2026-05-18-first-post.md")
            self.assertTrue(result.output_path.exists())


if __name__ == "__main__":
    unittest.main()
