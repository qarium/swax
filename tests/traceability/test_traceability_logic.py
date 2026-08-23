"""Logic tests for the swax.traceability cell.

Covers TraceabilityGraph.add_edge accumulation, deduplicate idempotency and
self-loop removal (design-doc verbatim case), remove_paths pruning of removed
endpoints and their dangling edges, and the storage round-trip: deterministic
sorted YAML, empty-file handling, scalar-to-list normalization, and save ->
load equality. All filesystem operations use tmp_path.
"""

from swax.traceability import TraceabilityGraph, load_traceability, save_traceability


class TestTraceabilityGraphLogic:
    def test_add_edge_appends_to_adjacency(self):
        graph = TraceabilityGraph(edges={})

        graph.add_edge("/a", "/b")
        graph.add_edge("/a", "/b")

        # Duplicates are permitted at insert time — resolved by deduplicate.
        assert graph.edges["/a"] == ["/b", "/b"]

    def test_deduplicate_removes_duplicates_and_self_loops(self):
        graph = TraceabilityGraph(edges={"/a": ["/b", "/b", "/a"], "/b": ["/a"]})

        graph.deduplicate()

        assert graph.edges == {"/a": ["/b"], "/b": ["/a"]}

        # Idempotent — a second call produces no change.
        graph.deduplicate()
        assert graph.edges == {"/a": ["/b"], "/b": ["/a"]}

    def test_deduplicate_preserves_sources_without_targets(self):
        # A source whose only edges were self-loops collapses to an empty
        # adjacency list, but the source is preserved as a graph node — a path
        # without dependencies still appears in the saved graph.
        graph = TraceabilityGraph(edges={"/a": ["/a", "/a"]})

        graph.deduplicate()

        assert graph.edges == {"/a": []}

        graph.deduplicate()
        assert graph.edges == {"/a": []}

    def test_remove_paths_drops_keys_and_adjacency_references(self):
        graph = TraceabilityGraph(
            edges={"/users": ["/orders", "/billing"], "/orders": ["/users"], "/billing": ["/orders"]}
        )

        graph.remove_paths(["/orders"])

        # Key dropped and dangling references scrubbed — a surviving edge to a
        # removed endpoint would corrupt swax plan results.
        assert graph.edges == {"/users": ["/billing"], "/billing": []}

    def test_remove_paths_ignores_absent_endpoints_and_preserves_order(self):
        graph = TraceabilityGraph(edges={"/a": ["/x", "/b", "/y"], "/ghost": []})

        graph.remove_paths(["/b", "/not-there"])

        # Absent endpoint ignored, survivor order kept, empty-list node
        # preserved — order stability keeps serialized graphs diff-stable.
        assert graph.edges == {"/a": ["/x", "/y"], "/ghost": []}


class TestStorageLogic:
    def test_save_traceability_writes_sorted_yaml(self, tmp_path):
        graph = TraceabilityGraph(edges={"/b": ["/a"], "/a": ["/b", "/a"]})
        graph.deduplicate()
        path = tmp_path / ".swax" / "traceability.yml"

        save_traceability(graph, path)

        assert path.exists()
        assert path.parent == tmp_path / ".swax"
        content = path.read_text(encoding="utf-8")
        # Sorted by key: /a before /b.
        assert content.index("/a:") < content.index("/b:")
        # Deterministic: re-writing yields a byte-identical file.
        save_traceability(graph, path)
        assert path.read_text(encoding="utf-8") == content

    def test_load_traceability_handles_empty_file(self, tmp_path):
        path = tmp_path / "traceability.yml"
        path.write_text("", encoding="utf-8")

        graph = load_traceability(path)

        assert graph.edges == {}

    def test_load_traceability_treats_non_mapping_content_as_empty(self, tmp_path):
        # A corrupt file holding a bare scalar (not a mapping) must not crash
        # on .items(); it is treated like an empty graph, matching the docstring.
        path = tmp_path / "traceability.yml"
        path.write_text("just a scalar string\n", encoding="utf-8")

        graph = load_traceability(path)

        assert graph.edges == {}

    def test_load_traceability_normalizes_values_to_list(self, tmp_path):
        path = tmp_path / "traceability.yml"
        path.write_text("/a: /b\n", encoding="utf-8")

        graph = load_traceability(path)

        # A scalar value is wrapped as a single-element list.
        assert graph.edges["/a"] == ["/b"]

    def test_load_traceability_preserves_list_values(self, tmp_path):
        path = tmp_path / "traceability.yml"
        path.write_text(
            "/a:\n- /b\n- /c\n",
            encoding="utf-8",
        )

        graph = load_traceability(path)

        assert graph.edges["/a"] == ["/b", "/c"]

    def test_save_load_round_trip(self, tmp_path):
        path = tmp_path / "traceability.yml"
        original = TraceabilityGraph(edges={"/a": ["/b", "/c"], "/b": ["/a"]})
        original.deduplicate()

        save_traceability(original, path)
        loaded = load_traceability(path)

        assert loaded.edges == original.edges
