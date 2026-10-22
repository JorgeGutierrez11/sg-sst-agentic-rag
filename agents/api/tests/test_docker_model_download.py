import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

with patch("dotenv.load_dotenv"):
    from agents.consulta_normativa.langchain_rag.config import (
        RERANKER_MODEL_NAME,
        RERANKER_MODEL_REVISION,
    )
from pipeline.chunking.config import (
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_EMBEDDING_MODEL_REVISION,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = PROJECT_ROOT / "docker" / "download_models.py"


def load_script():
    spec = importlib.util.spec_from_file_location("download_models", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PinnedModelsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.script = load_script()

    def test_reads_runtime_pinned_revisions_from_config_files_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            layer_root = Path(directory)
            for relative in (self.script.EMBEDDING_CONFIG, self.script.RERANKER_CONFIG):
                (layer_root / relative).parent.mkdir(parents=True)
                shutil.copy(PROJECT_ROOT / relative, layer_root / relative)

            models = self.script.pinned_models(layer_root)

        self.assertEqual(
            models,
            (
                (DEFAULT_EMBEDDING_MODEL, DEFAULT_EMBEDDING_MODEL_REVISION),
                (RERANKER_MODEL_NAME, RERANKER_MODEL_REVISION),
            ),
        )

    def test_missing_constant_names_constant_and_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.py"
            config_path.write_text('OTHER = "value"\n', encoding="utf-8")

            with self.assertRaises(self.script.PinnedModelError) as context:
                self.script.read_constant(config_path, "RERANKER_MODEL_REVISION")

        self.assertIn("RERANKER_MODEL_REVISION", str(context.exception))
        self.assertIn(str(config_path), str(context.exception))

    def test_non_string_constant_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.py"
            config_path.write_text("RERANKER_MODEL_REVISION = None\n", encoding="utf-8")

            with self.assertRaises(self.script.PinnedModelError) as context:
                self.script.read_constant(config_path, "RERANKER_MODEL_REVISION")

        self.assertIn("RERANKER_MODEL_REVISION", str(context.exception))

    def test_main_downloads_each_pinned_snapshot_and_returns_zero(self) -> None:
        downloads: list[tuple[str, str]] = []

        def fake_download(*, repo_id: str, revision: str) -> str:
            downloads.append((repo_id, revision))
            return f"/cache/{repo_id}"

        exit_code = self.script.main(root=PROJECT_ROOT, download=fake_download)

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            downloads,
            [
                (DEFAULT_EMBEDDING_MODEL, DEFAULT_EMBEDDING_MODEL_REVISION),
                (RERANKER_MODEL_NAME, RERANKER_MODEL_REVISION),
            ],
        )


if __name__ == "__main__":
    unittest.main()
