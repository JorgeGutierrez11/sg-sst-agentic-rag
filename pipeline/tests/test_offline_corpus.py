import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pipeline import offline_corpus
from pipeline.artifact_validation import ArtifactValidationError
from pipeline.offline_orchestration import STAGE_ORDER, OfflineBuildError, StageEvent, StageName


class OfflineCorpusCliTest(unittest.TestCase):
    def run_main(self, argv: list[str], build_side_effect=None, validate_result=None) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            patch.object(offline_corpus, "build_offline_corpus") as build,
            patch.object(offline_corpus, "default_stage_operations", return_value="operations"),
            patch.object(offline_corpus, "validate_published_corpus") as validate,
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            build.side_effect = build_side_effect
            if isinstance(validate_result, BaseException):
                validate.side_effect = validate_result
            else:
                validate.return_value = validate_result
            exit_code = offline_corpus.main(argv)
        self.build = build
        self.validate = validate
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def assert_parser_exit(self, argv: list[str], message: str) -> None:
        stderr = io.StringIO()
        with redirect_stderr(stderr), self.assertRaises(SystemExit) as context:
            offline_corpus.main(argv)
        self.assertEqual(context.exception.code, 2)
        self.assertIn(message, stderr.getvalue())

    def test_rejects_non_positive_batch_size_before_build(self) -> None:
        self.assert_parser_exit(["build", "--batch-size", "0"], "greater than 0")

    def test_requires_a_subcommand(self) -> None:
        self.assert_parser_exit([], "required")

    def test_rejects_unknown_options(self) -> None:
        self.assert_parser_exit(["build", "--force"], "unrecognized arguments: --force")

    def test_build_passes_the_real_project_root_and_operations(self) -> None:
        exit_code, _stdout, stderr = self.run_main(["build", "--batch-size", "4", "--keep-workdir"])

        self.assertEqual(exit_code, 0)
        kwargs = self.build.call_args.kwargs
        self.assertEqual(kwargs["project_root"], offline_corpus.PROJECT_ROOT)
        self.assertEqual(kwargs["operations"], "operations")
        self.assertEqual((kwargs["batch_size"], kwargs["keep_workdir"]), (4, True))
        self.assertTrue(stderr.endswith("Offline corpus build published successfully\n"))

    def test_human_progress_renders_every_stage_and_lifecycle_phase(self) -> None:
        def emit(**kwargs):
            callback = kwargs["progress_callback"]
            for number, stage in enumerate(STAGE_ORDER, start=1):
                callback(StageEvent(stage, number, "completed", "ok"))
            callback(StageEvent(StageName.PUBLICATION, None, "completed"))

        _exit_code, stdout, stderr = self.run_main(["build"], emit)

        self.assertEqual(stdout, "")
        self.assertEqual(
            stderr.splitlines(),
            [
                "[1/10] DOCX ingestion completed — ok",
                "[2/10] Markdown cleanup completed — ok",
                "[3/10] Parent chunking completed — ok",
                "[4/10] Regex child chunking completed — ok",
                "[5/10] Table reference audit completed — ok",
                "[6/10] Table Markdown conversion completed — ok",
                "[7/10] Table document build completed — ok",
                "[8/10] Chroma indexing completed — ok",
                "[9/10] BM25 indexing completed — ok",
                "[10/10] Corpus validation completed — ok",
                "Publication completed",
                "Offline corpus build published successfully",
            ],
        )

    def test_stage_failure_names_the_stage_once_with_its_cause(self) -> None:
        cause = ValueError("Failed to convert table HTML to Markdown: norma/table_3.html")

        def fail(**kwargs):
            kwargs["progress_callback"](StageEvent(StageName.TABLE_MARKDOWN_CONVERSION, 6, "failed", str(cause)))
            raise OfflineBuildError(StageName.TABLE_MARKDOWN_CONVERSION, cause)

        exit_code, _stdout, stderr = self.run_main(["build"], fail)

        self.assertEqual(exit_code, 2)
        self.assertEqual(
            stderr.splitlines(),
            [
                "[6/10] Table Markdown conversion failed",
                f"Cause: {cause}",
                "The published corpus was not modified.",
            ],
        )

    def test_publication_failure_reports_the_restored_or_retained_corpus(self) -> None:
        cases = (
            (None, "The previous published corpus was restored."),
            (Path("/data/.pipeline-backup/run"), "backup retained at /data/.pipeline-backup/run"),
        )
        for backup_path, expected in cases:
            with self.subTest(backup_path=backup_path):
                error = OfflineBuildError(StageName.PUBLICATION, OSError("disk full"), backup_path)
                exit_code, _stdout, stderr = self.run_main(["build"], error)

                self.assertEqual(exit_code, 2)
                self.assertIn("Cause: disk full", stderr)
                self.assertIn(expected, stderr.splitlines()[-1])

    def test_unexpected_error_exits_one_with_its_type(self) -> None:
        exit_code, _stdout, stderr = self.run_main(["build"], RuntimeError("boom"))

        self.assertEqual(exit_code, 1)
        self.assertIn("RuntimeError: boom", stderr)

    def test_json_stage_events_use_stdout(self) -> None:
        def emit(**kwargs):
            kwargs["progress_callback"](StageEvent(StageName.DOCX_INGESTION, 1, "completed", "1 document"))
            kwargs["progress_callback"](StageEvent(StageName.PUBLICATION, None, "completed"))

        exit_code, stdout, stderr = self.run_main(["build", "--json"], emit)

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            [json.loads(line) for line in stdout.splitlines()],
            [
                {"stage": "docx_ingestion", "number": 1, "status": "completed", "detail": "1 document"},
                {"stage": "publication", "number": None, "status": "completed", "detail": ""},
            ],
        )
        self.assertEqual(stderr, "")

    def test_validate_only_invokes_the_read_only_validator_and_reports_counts(self) -> None:
        result = SimpleNamespace(parent_count=412, source_record_count=1245)

        exit_code, _stdout, stderr = self.run_main(["validate"], validate_result=result)

        self.assertEqual(exit_code, 0)
        self.validate.assert_called_once_with(offline_corpus.PROJECT_ROOT)
        self.build.assert_not_called()
        self.assertEqual(
            stderr,
            "Offline corpus validation completed — 412 parents, 1,245 records; Chroma and BM25 agree\n",
        )

    def test_validate_failure_exits_two(self) -> None:
        error = ArtifactValidationError("Index ID mismatch: 1 only in Chroma")

        exit_code, _stdout, stderr = self.run_main(["validate"], validate_result=error)

        self.assertEqual(exit_code, 2)
        self.assertEqual(
            stderr.splitlines(),
            ["Offline corpus validation failed", "Cause: Index ID mismatch: 1 only in Chroma"],
        )


if __name__ == "__main__":
    unittest.main()
