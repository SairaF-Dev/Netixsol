"""Concept graph tests: the real graph is valid, and the validator catches bad graphs."""
from __future__ import annotations

import copy

import networkx as nx
import pytest

from ilm.content.download import all_lessons
from ilm.graph.concept_graph import (build_graph, depth_levels, layered_positions,
                                     learning_order, load_concepts, validate)

LESSONS = {l["id"]: l["order"] for l in all_lessons()}


@pytest.fixture
def concepts():
    return load_concepts()


# ---- the real graph -------------------------------------------------------------
def test_real_graph_meets_the_brief(concepts):
    g = build_graph(concepts)
    assert g.number_of_nodes() >= 40          # brief: 40+ Python concepts
    assert nx.is_directed_acyclic_graph(g)    # brief: check it has no cycles


def test_real_graph_has_no_errors_and_no_redundant_edges(concepts):
    v = validate(concepts, set(LESSONS))
    assert v.errors == []
    assert not [w for w in v.warnings if w.startswith("redundant")]


def test_every_concept_is_taught_somewhere(concepts):
    # Recursion was the one gap (CS50P never teaches it); MIT 6.0001 lecture 6 closed it.
    # If a new gap appears, someone must decide on purpose; this test makes it visible.
    gaps = [c["id"] for c in concepts if not c.get("taught_in")]
    assert gaps == []


def test_learning_order_puts_every_prereq_first(concepts):
    g = build_graph(concepts)
    order = learning_order(g, LESSONS)
    at = {n: i for i, n in enumerate(order)}
    assert len(order) == g.number_of_nodes()
    for a, b in g.edges:
        assert at[a] < at[b], f"{a} must come before {b}"


def test_depth_levels_start_at_zero_for_the_root(concepts):
    level = depth_levels(build_graph(concepts))
    assert level["program_basics"] == 0
    assert level["for_loops"] > level["variables"]


def test_layout_is_deterministic(concepts):
    g = build_graph(concepts)
    assert layered_positions(g) == layered_positions(g)


# ---- the validator catches broken graphs (testing the tester) -------------------
def _find(concepts, cid):
    return next(c for c in concepts if c["id"] == cid)


def test_validator_catches_a_cycle(concepts):
    bad = copy.deepcopy(concepts)
    _find(bad, "variables")["prereqs"].append("for_loops")  # for_loops already needs variables
    v = validate(bad, set(LESSONS))
    assert any(e.startswith("cycle:") for e in v.errors)


def test_validator_catches_unknown_reference_and_unknown_lesson(concepts):
    bad = copy.deepcopy(concepts)
    _find(bad, "lists")["prereqs"].append("arrays")          # typo-style id
    _find(bad, "lists")["taught_in"].append("cs50p-l42")
    errors = " ".join(validate(bad, set(LESSONS)).errors)
    assert "unknown concept 'arrays'" in errors and "unknown lesson 'cs50p-l42'" in errors


def test_validator_catches_self_loop_duplicate_and_prereq_also_related(concepts):
    bad = copy.deepcopy(concepts)
    _find(bad, "sets")["prereqs"].append("sets")
    _find(bad, "slicing")["related"] = ["lists"]            # lists is already its prereq
    bad.append(dict(_find(bad, "comments")))
    errors = " ".join(validate(bad, set(LESSONS)).errors)
    assert "lists itself" in errors and "duplicate" in errors and "both prereq and related" in errors


def test_validator_warns_on_redundant_edge(concepts):
    bad = copy.deepcopy(concepts)
    _find(bad, "for_loops")["prereqs"].append("variables")  # implied via range_function
    v = validate(bad, set(LESSONS))
    assert v.ok  # redundant is a warning, not an error
    assert any("for_loops <- variables" in w for w in v.warnings)
