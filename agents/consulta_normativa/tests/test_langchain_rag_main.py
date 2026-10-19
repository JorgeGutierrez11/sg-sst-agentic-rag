"""Tests for the direct experimental LangChain RAG entrypoint."""

from __future__ import annotations

import io
import tempfile
import types
import unittest
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import mock_open, patch

from agents.consulta_normativa.langchain_rag import main as cli
from agents.consulta_normativa.langchain_rag.config import CHROMA_WORKING_DIR_ENV, PROJECT_ROOT


class LangChainRagMainTest(unittest.TestCase):
    """Verify direct execution without real Chroma or DeepSeek calls."""

    def test_no_args_builds_runtime_and_runs_interactive_loop(self) -> None:
        runtime = self.build_runtime()

        with patch.object(cli, "build_runtime", return_value=runtime) as build_runtime, patch.object(
            cli, "run_interactive_loop", return_value=0
        ) as run_loop:
            exit_code = cli.main([])

        self.assertEqual(exit_code, 0)
        build_runtime.assert_called_once_with()
        run_loop.assert_called_once_with(runtime)

    def test_optional_positional_question_answers_once_without_subcommands(self) -> None:
        runtime = self.build_runtime()
        stdout = io.StringIO()

        with patch.object(cli, "build_runtime", return_value=runtime), redirect_stdout(stdout):
            exit_code = cli.main(["What does the employer need?"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(runtime.calls, ["What does the employer need?:graph:cli-test"])
        self.assertIn("Answer:\nGenerated answer.", stdout.getvalue())
        self.assertIn("References:\n- Decreto 1072", stdout.getvalue())

    def test_parser_rejects_extra_arguments_instead_of_subcommands(self) -> None:
        stderr = io.StringIO()

        with redirect_stderr(stderr), self.assertRaises(SystemExit) as context:
            cli.main(["ask", "What does the employer need?"])

        self.assertEqual(context.exception.code, 2)
        self.assertIn("unrecognized arguments", stderr.getvalue())

    def test_interactive_loop_ignores_blank_input_and_exits(self) -> None:
        runtime = self.build_runtime()

        with patch("builtins.input", side_effect=["", "   ", "exit"]):
            exit_code = cli.run_interactive_loop(runtime)

        self.assertEqual(exit_code, 0)
        self.assertEqual(runtime.calls, [])

    def test_interactive_question_prints_controlled_rag_error_and_continues(self) -> None:
        runtime = self.build_runtime(fail_first=True)
        stdout = io.StringIO()
        stderr = io.StringIO()

        with patch("builtins.input", side_effect=["fail", "recover", "quit"]), redirect_stdout(stdout), redirect_stderr(
            stderr
        ):
            exit_code = cli.run_interactive_loop(runtime)

        self.assertEqual(exit_code, 0)
        self.assertEqual(runtime.calls, ["fail:graph:cli-test", "recover:graph:cli-test"])
        self.assertIn("Error during RAG execution", stderr.getvalue())
        self.assertIn("fake RAG failure", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())
        self.assertIn("Answer:\nGenerated answer.", stdout.getvalue())

    def test_missing_deepseek_api_key_returns_controlled_error_without_traceback(self) -> None:
        stderr = io.StringIO()
        dependencies = self.build_dependencies(
            build_deepseek_llm=lambda: (_ for _ in ()).throw(ValueError("DEEPSEEK_API_KEY"))
        )

        with patch.object(cli, "load_dependencies", return_value=dependencies), redirect_stderr(stderr):
            exit_code = cli.main([])

        self.assertEqual(exit_code, 2)
        self.assertIn("Error during initialization", stderr.getvalue())
        self.assertIn("DEEPSEEK_API_KEY", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_missing_chroma_path_or_collection_returns_controlled_error_without_traceback(self) -> None:
        stderr = io.StringIO()
        dependencies = self.build_dependencies(
            open_existing_collection=lambda path, name, embedding_function: (_ for _ in ()).throw(
                ValueError("ChromaDB persist path does not exist")
            )
        )

        with patch.object(cli, "load_dependencies", return_value=dependencies), redirect_stderr(stderr):
            exit_code = cli.main([])

        self.assertEqual(exit_code, 2)
        self.assertIn("Error during initialization", stderr.getvalue())
        self.assertIn("ChromaDB persist path does not exist", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_missing_dependency_returns_controlled_error_without_traceback(self) -> None:
        stderr = io.StringIO()

        with patch.object(
            cli,
            "load_dependencies",
            side_effect=cli.OperationalError("Required runtime dependency is not installed: langchain_openai"),
        ), redirect_stderr(stderr):
            exit_code = cli.main([])

        self.assertEqual(exit_code, 2)
        self.assertIn("Error during initialization", stderr.getvalue())
        self.assertIn("langchain_openai", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_build_runtime_uses_deepseek_llm_builder(self) -> None:
        calls: list[str] = []
        graph = FakeDrawableGraph()
        dependencies = self.build_dependencies(
            build_deepseek_llm=lambda: calls.append("deepseek") or "llm",
            build_langgraph_rag=lambda llm, retriever, top_k, **kwargs: graph,
        )

        with self.runtime_support_patches(), patch.object(
            cli, "load_dependencies", return_value=dependencies
        ), patch("builtins.open", mock_open()):
            cli.build_runtime()

        self.assertEqual(calls, ["deepseek"])
        self.assertTrue(graph.draw_mermaid_png_called)

    def test_build_runtime_can_skip_graph_image_output(self) -> None:
        graph = FakeDrawableGraph()
        dependencies = self.build_dependencies(
            build_langgraph_rag=lambda llm, retriever, top_k, **kwargs: graph,
        )

        with self.runtime_support_patches(), patch.object(cli, "load_dependencies", return_value=dependencies):
            runtime = cli.build_runtime(write_graph_image=False)

        self.assertIs(runtime.graph, graph)
        self.assertFalse(graph.draw_mermaid_png_called)

    def test_build_runtime_opens_dense_and_sparse_indexes_and_uses_hybrid_retriever_boundary(self) -> None:
        calls: list[str] = []

        def fake_open_existing_collection(path: object, collection_name: str, embedding_function: object) -> str:
            calls.append(f"collection:{path}:{collection_name}:{embedding_function}")
            return "collection"

        def fake_open_existing_index() -> str:
            calls.append("index")
            return "index"

        def fake_hybrid_retriever(
            collection: object,
            sparse_index: object,
            *,
            candidate_top_k: int,
            rrf_k: int,
        ) -> object:
            calls.append(f"retriever:{collection}:{sparse_index}:{candidate_top_k}:{rrf_k}")
            return "hybrid-retriever"

        graph = FakeDrawableGraph()

        def fake_build_langgraph_rag(
            *,
            llm: object,
            retriever: object,
            top_k: int,
            **kwargs: object,
        ) -> FakeDrawableGraph:
            calls.append(
                "graph:"
                f"{llm}:{retriever}:{top_k}:"
                f"{kwargs['reranker']}:{kwargs['reranker_candidate_pool_size']}:"
                f"{kwargs['reranker_final_top_k']}:{kwargs['reranker_batch_size']}:"
                f"{kwargs['reranker_device']}:{kwargs['reranker_input_max_length']}:"
                f"{kwargs['parent_lookup']}:{kwargs['first_table_parts']}"
            )
            return graph

        working_copy = types.SimpleNamespace(path=Path("/working/chroma"))
        dependencies = self.build_dependencies(
            build_deepseek_llm=lambda: "llm",
            build_langgraph_rag=fake_build_langgraph_rag,
            load_parent_documents=lambda path: calls.append(f"parents:{path}") or {"parent-1": "parent"},
            validate_index_consistency=lambda collection, sparse_index, parent_lookup: calls.append(
                f"consistency:{collection}:{sparse_index}:{parent_lookup}"
            ),
            load_first_table_parts=lambda path: calls.append(f"tables:{path}") or {"source-a:0": "table"},
            open_existing_collection=fake_open_existing_collection,
            open_existing_bm25_index=fake_open_existing_index,
            hybrid_retriever=fake_hybrid_retriever,
            create_chroma_working_copy=lambda source, working_root: calls.append(
                f"working-copy:{source}:{working_root}"
            )
            or working_copy,
            get_reranker=lambda model_name, max_length, device, revision: calls.append(
                f"reranker:{model_name}:{max_length}:{device}:{revision}"
            )
            or "reranker",
            build_embedding_function=lambda: calls.append("embedding-function") or FakeEmbeddingFunction(),
        )

        with self.runtime_support_patches(), patch.object(
            cli, "load_dependencies", return_value=dependencies
        ), patch("builtins.open", mock_open()), patch.dict("os.environ", {CHROMA_WORKING_DIR_ENV: ""}):
            runtime = cli.build_runtime()

        self.assertEqual(
            calls,
            [
                f"working-copy:{cli.DEFAULT_CHROMA_PATH}:None",
                "embedding-function",
                "collection:/working/chroma:sg_sst_base_rag:qwen-embedding-function",
                "index",
                f"parents:{cli.DEFAULT_PARENT_CHUNKS_PATH}",
                "consistency:collection:index:{'parent-1': 'parent'}",
                f"retriever:collection:index:{cli.HYBRID_SOURCE_CANDIDATE_TOP_K}:{cli.HYBRID_RRF_K}",
                f"reranker:{cli.RERANKER_MODEL_NAME}:{cli.RERANKER_MAX_LENGTH}:{cli.RERANKER_DEVICE}:"
                f"{cli.RERANKER_MODEL_REVISION}",
                f"tables:{cli.DEFAULT_TABLE_DOCUMENTS_PATH}",
                "graph:llm:hybrid-retriever:"
                f"{cli.HYBRID_RRF_OUTPUT_TOP_K}:reranker:"
                f"{cli.RERANKER_CANDIDATE_POOL_SIZE}:{cli.RERANKER_FINAL_TOP_K}:"
                f"{cli.RERANKER_BATCH_SIZE}:{cli.RERANKER_DEVICE}:{cli.RERANKER_MAX_LENGTH}:"
                "{'parent-1': 'parent'}:{'source-a:0': 'table'}",
            ],
        )
        self.assertIs(runtime.graph, graph)
        self.assertIs(runtime.chroma_working_copy, working_copy)

    def test_build_runtime_creates_working_copy_under_configured_root(self) -> None:
        roots: list[object] = []
        dependencies = self.build_dependencies(
            create_chroma_working_copy=lambda source, working_root: roots.append(working_root)
            or types.SimpleNamespace(path=Path("/working/chroma")),
        )

        with self.runtime_support_patches(), patch.object(
            cli, "load_dependencies", return_value=dependencies
        ), patch.dict("os.environ", {CHROMA_WORKING_DIR_ENV: "/srv/chroma-work"}):
            cli.build_runtime(write_graph_image=False)

        self.assertEqual(roots, [Path("/srv/chroma-work")])

    def test_default_runtime_artifacts_cover_required_absolute_paths(self) -> None:
        bm25_path = cli.DEFAULT_BM25_PATH
        expected = {
            cli.DEFAULT_CHROMA_PATH / "chroma.sqlite3": False,
            bm25_path / "params.index.json": False,
            bm25_path / "vocab.index.json": False,
            bm25_path / "data.csc.index.npy": False,
            bm25_path / "indices.csc.index.npy": False,
            bm25_path / "indptr.csc.index.npy": False,
            bm25_path / "corpus.jsonl": False,
            cli.DEFAULT_PARENT_CHUNKS_PATH: False,
            cli.DEFAULT_TABLE_DOCUMENTS_PATH: True,
        }

        self.assertEqual(
            {artifact.path: artifact.allow_empty for artifact in cli.RUNTIME_ARTIFACTS},
            expected,
        )
        self.assertTrue(all(artifact.path.is_absolute() for artifact in cli.RUNTIME_ARTIFACTS))

    def test_missing_runtime_artifact_raises_error_naming_artifact_and_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifacts = self.create_artifacts(Path(directory))

            for artifact in artifacts:
                with self.subTest(artifact=artifact.label):
                    content = artifact.path.read_bytes()
                    artifact.path.unlink()
                    try:
                        with self.assertRaises(cli.OperationalError) as raised:
                            cli.validate_runtime_artifacts(artifacts)
                    finally:
                        artifact.path.write_bytes(content)

                    self.assertEqual(
                        str(raised.exception),
                        f"Missing runtime artifact: {artifact.label} ({artifact.path})",
                    )

    def test_empty_required_runtime_artifact_raises_error_naming_artifact_and_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifacts = self.create_artifacts(Path(directory))

            for artifact in artifacts:
                if artifact.allow_empty:
                    continue
                with self.subTest(artifact=artifact.label):
                    content = artifact.path.read_bytes()
                    artifact.path.write_bytes(b"")
                    try:
                        with self.assertRaises(cli.OperationalError) as raised:
                            cli.validate_runtime_artifacts(artifacts)
                    finally:
                        artifact.path.write_bytes(content)

                    self.assertEqual(
                        str(raised.exception),
                        f"Empty runtime artifact: {artifact.label} ({artifact.path})",
                    )

    def test_empty_table_documents_artifact_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifacts = self.create_artifacts(Path(directory))
            table_documents = next(artifact for artifact in artifacts if artifact.allow_empty)
            table_documents.path.write_bytes(b"")

            cli.validate_runtime_artifacts(artifacts)

    def test_empty_chroma_directory_fails_before_opening_indexes_or_creating_files(self) -> None:
        opened: list[str] = []

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifacts = self.create_artifacts(root)
            chroma_database = root / "chroma" / "chroma.sqlite3"
            chroma_database.unlink()
            dependencies = self.build_dependencies(
                validate_runtime_artifacts=lambda: cli.validate_runtime_artifacts(artifacts),
                open_existing_collection=lambda path, name, embedding_function: opened.append("chroma") or object(),
                open_existing_bm25_index=lambda: opened.append("bm25") or object(),
                create_chroma_working_copy=lambda source, working_root: opened.append("working-copy"),
            )

            with self.runtime_support_patches(), patch.object(
                cli, "load_dependencies", return_value=dependencies
            ), self.assertRaises(cli.OperationalError) as raised:
                cli.build_runtime(write_graph_image=False)

            self.assertEqual(list((root / "chroma").iterdir()), [])

        self.assertIn(f"Missing runtime artifact: Chroma database ({chroma_database})", str(raised.exception))
        self.assertEqual(opened, [])

    def test_build_runtime_error_names_original_exception_type_and_keeps_cause(self) -> None:
        original = ValueError("collection unavailable")

        def fail_open_existing_collection(path: object, collection_name: str, embedding_function: object) -> object:
            raise original

        dependencies = self.build_dependencies(open_existing_collection=fail_open_existing_collection)

        with self.runtime_support_patches(), patch.object(
            cli, "load_dependencies", return_value=dependencies
        ), self.assertRaises(cli.OperationalError) as raised:
            cli.build_runtime(write_graph_image=False)

        self.assertEqual(str(raised.exception), "ValueError: collection unavailable")
        self.assertIs(raised.exception.__cause__, original)

    def test_index_inconsistency_stops_startup_before_loading_reranker(self) -> None:
        loaded: list[str] = []

        def fail_index_consistency(collection: object, sparse_index: object, parent_lookup: object) -> None:
            raise cli.OperationalError("Index record count mismatch: Chroma has 3 records, BM25 has 2")

        dependencies = self.build_dependencies(
            validate_index_consistency=fail_index_consistency,
            get_reranker=lambda model_name, max_length, device, revision: loaded.append("reranker") or object(),
        )

        with self.runtime_support_patches(), patch.object(
            cli, "load_dependencies", return_value=dependencies
        ), self.assertRaises(cli.OperationalError) as raised:
            cli.build_runtime(write_graph_image=False)

        self.assertIn("Chroma has 3 records, BM25 has 2", str(raised.exception))
        self.assertEqual(loaded, [])

    def test_memory_reuses_chroma_embedding_model_with_normalized_vectors(self) -> None:
        embedding_function = FakeEmbeddingFunction()
        opened_with: list[object] = []
        dependencies = self.build_dependencies(
            build_embedding_function=lambda: embedding_function,
            open_existing_collection=lambda path, name, given: opened_with.append(given) or object(),
        )

        with self.runtime_support_patches(), patch(
            "chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction",
            side_effect=AssertionError("a second Qwen embedding function was built"),
        ), patch("langgraph.store.memory.InMemoryStore", return_value=object()) as memory_store, patch.object(
            cli, "load_dependencies", return_value=dependencies
        ):
            cli.build_runtime(write_graph_image=False)

        memory_embeddings = memory_store.call_args.kwargs["index"]["embed"]
        self.assertEqual(opened_with, [embedding_function])
        self.assertIs(memory_embeddings._model, embedding_function._model)
        self.assertTrue(memory_embeddings._normalize_embeddings)

    def test_coherent_indexes_pass_consistency_check(self) -> None:
        corpus = [child_record("child-1", "parent-1"), table_record("table-1")]

        cli.validate_index_consistency(
            FakeCollection(["child-1", "table-1"]),
            FakeBm25Index(corpus),
            {"parent-1": "parent"},
        )

    def test_different_record_counts_raise_error_with_both_counts(self) -> None:
        corpus = [child_record("child-1", "parent-1"), child_record("child-2", "parent-1")]

        with self.assertRaises(cli.OperationalError) as raised:
            cli.validate_index_consistency(
                FakeCollection(["child-1", "child-2", "stale-1"]),
                FakeBm25Index(corpus),
                {"parent-1": "parent"},
            )

        message = str(raised.exception)
        self.assertIn("Index record count mismatch: Chroma has 3 records, BM25 has 2", message)
        self.assertIn("1 only in Chroma (stale-1)", message)

    def test_same_count_with_different_ids_raises_error_naming_ids(self) -> None:
        corpus = [child_record("child-1", "parent-1"), child_record("child-new", "parent-1")]

        with self.assertRaises(cli.OperationalError) as raised:
            cli.validate_index_consistency(
                FakeCollection(["child-1", "child-old"]),
                FakeBm25Index(corpus),
                {"parent-1": "parent"},
            )

        message = str(raised.exception)
        self.assertNotIn("count mismatch", message)
        self.assertIn(
            "Index ID mismatch: 1 only in Chroma (child-old); 1 only in BM25 (child-new)",
            message,
        )

    def test_id_mismatch_lists_at_most_five_example_ids(self) -> None:
        stale_ids = [f"stale-{number}" for number in range(7)]

        with self.assertRaises(cli.OperationalError) as raised:
            cli.validate_index_consistency(
                FakeCollection(["child-1", *stale_ids]),
                FakeBm25Index([child_record("child-1", "parent-1")]),
                {"parent-1": "parent"},
            )

        message = str(raised.exception)
        self.assertIn("7 only in Chroma (stale-0, stale-1, stale-2, stale-3, stale-4, ...)", message)
        self.assertNotIn("stale-5", message)

    def test_child_with_missing_parent_raises_error(self) -> None:
        corpus = [child_record("child-1", "parent-1"), child_record("child-2", "parent-gone")]

        with self.assertRaises(cli.OperationalError) as raised:
            cli.validate_index_consistency(
                FakeCollection(["child-1", "child-2"]),
                FakeBm25Index(corpus),
                {"parent-1": "parent"},
            )

        self.assertIn(
            "Missing parent chunks: 1 of 2 child chunks reference a parent not found in parent chunks",
            str(raised.exception),
        )

    def test_table_documents_without_parent_id_are_not_orphans(self) -> None:
        corpus = [table_record("table-1"), table_record("table-2")]

        cli.validate_index_consistency(
            FakeCollection(["table-1", "table-2"]),
            FakeBm25Index(corpus),
            {},
        )

    def create_artifacts(self, root: Path) -> tuple[cli.RuntimeArtifact, ...]:
        """Create one non-empty file per default runtime artifact under a temporary root."""

        project_root = PROJECT_ROOT
        artifacts = tuple(
            cli.RuntimeArtifact(
                label=artifact.label,
                path=root / artifact.path.relative_to(project_root / "data" / "processed"),
                allow_empty=artifact.allow_empty,
            )
            for artifact in cli.RUNTIME_ARTIFACTS
        )
        for artifact in artifacts:
            artifact.path.parent.mkdir(parents=True, exist_ok=True)
            artifact.path.write_bytes(b"content")
        return artifacts

    def build_runtime(self, fail_first: bool = False) -> object:
        calls: list[str] = []

        def fake_answer_with_langgraph(question: str, graph: object, *, thread_id: str) -> object:
            calls.append(f"{question}:{graph}:{thread_id}")
            if fail_first and question == "fail":
                raise RuntimeError("fake RAG failure")
            return types.SimpleNamespace(
                answer="Generated answer.",
                references=["Decreto 1072"],
                prompt="Prompt sent to model.",
            )

        runtime = cli.RagRuntime(
            answer_with_langgraph=fake_answer_with_langgraph,
            graph=FakeRuntimeGraph(),
            thread_id="cli-test",
        )
        return types.SimpleNamespace(**runtime.__dict__, calls=calls)

    def build_dependencies(
        self,
        build_deepseek_llm: object | None = None,
        build_langgraph_rag: object | None = None,
        answer_with_langgraph: object | None = None,
        hybrid_retriever: object | None = None,
        load_parent_documents: object | None = None,
        load_first_table_parts: object | None = None,
        open_existing_collection: object | None = None,
        open_existing_bm25_index: object | None = None,
        get_reranker: object | None = None,
        validate_runtime_artifacts: object | None = None,
        create_chroma_working_copy: object | None = None,
        validate_index_consistency: object | None = None,
        build_embedding_function: object | None = None,
    ) -> cli.RuntimeDependencies:
        return cli.RuntimeDependencies(
            validate_runtime_artifacts=validate_runtime_artifacts or (lambda: None),
            build_deepseek_llm=build_deepseek_llm or (lambda: object()),
            build_langgraph_rag=build_langgraph_rag or (lambda llm, retriever, **kwargs: object()),
            answer_with_langgraph=answer_with_langgraph or (lambda question, graph: object()),
            hybrid_retriever=hybrid_retriever or (lambda collection, sparse_index, **kwargs: lambda question, top_k: {}),
            load_parent_documents=load_parent_documents or (lambda path: {}),
            load_first_table_parts=load_first_table_parts or (lambda path: {}),
            open_existing_collection=open_existing_collection
            or (lambda path, collection_name, embedding_function: object()),
            open_existing_bm25_index=open_existing_bm25_index or (lambda: object()),
            get_reranker=get_reranker or (lambda model_name, max_length, device, revision: object()),
            create_chroma_working_copy=create_chroma_working_copy
            or (lambda source, working_root: types.SimpleNamespace(path=source)),
            validate_index_consistency=validate_index_consistency
            or (lambda collection, sparse_index, parent_lookup: None),
            build_embedding_function=build_embedding_function or FakeEmbeddingFunction,
        )

    @contextmanager
    def runtime_support_patches(self) -> Iterator[None]:
        """Replace runtime memory infrastructure without loading model weights."""

        embedding_function = types.SimpleNamespace(
            _model=object(),
            normalize_embeddings=True,
        )
        with ExitStack() as stack:
            stack.enter_context(
                patch(
                    "chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction",
                    return_value=embedding_function,
                )
            )
            stack.enter_context(patch("langgraph.checkpoint.memory.InMemorySaver", return_value=object()))
            stack.enter_context(patch("langgraph.store.memory.InMemoryStore", return_value=object()))
            yield


class FakeEmbeddingFunction:
    """Chroma embedding function fake that exposes the loaded SentenceTransformer."""

    def __init__(self) -> None:
        self._model = object()
        self.normalize_embeddings = False

    def __str__(self) -> str:
        return "qwen-embedding-function"


class FakeCollection:
    """Chroma collection fake exposing only the calls used by the consistency check."""

    def __init__(self, ids: list[str]) -> None:
        self.ids = ids

    def count(self) -> int:
        return len(self.ids)

    def get(self, include: list[str]) -> dict[str, list[str]]:
        return {"ids": list(self.ids)}


class FakeBm25Index:
    """BM25 index fake with the corpus records loaded by bm25s."""

    def __init__(self, corpus: list[dict[str, object]]) -> None:
        self.corpus = corpus


def child_record(record_id: str, parent_id: str) -> dict[str, object]:
    return {"id": record_id, "document": "text", "metadata": {"document_type": "child_chunk", "parent_id": parent_id}}


def table_record(record_id: str) -> dict[str, object]:
    return {"id": record_id, "document": "table", "metadata": {"document_type": "table"}}


class FakeRuntimeGraph:
    """Compiled-graph fake exposing the state snapshot used by the CLI."""

    def __str__(self) -> str:
        return "graph"

    def get_state(self, config: object) -> object:
        return types.SimpleNamespace(values={})


class FakeDrawableGraph:
    """Small compiled-graph fake with drawing support for runtime construction tests."""

    def __init__(self) -> None:
        self.draw_mermaid_png_called = False

    def get_graph(self) -> object:
        return self

    def draw_mermaid_png(self) -> bytes:
        self.draw_mermaid_png_called = True
        return b"graph"


if __name__ == "__main__":
    unittest.main()
