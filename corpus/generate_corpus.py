#!/usr/bin/env python3
"""Deterministic bug injector for the bug-finding benchmark corpus.

For each of the 30 hand-written, self-contained Python snippets defined in
SNIPPETS below, applies exactly one AST-located, text-spliced mutation from
the fixed bug taxonomy (assigned round-robin across the snippets), verifies
the mutation actually breaks the companion test (and that the untouched
snippet passes it), and writes:

  corpus/snippets/NN_clean.py   the original, correct reference version
  corpus/snippets/NN_buggy.py   the mutated version handed to the agent
  corpus/snippets/NN_test.py    the companion pytest file

...plus corpus/tasks.jsonl (one record per task) and corpus/task_order.json
(a seeded shuffle of task ids, shared by both runner conditions).

Mutations are located via `ast` (never regex) but applied as a single
source-text splice keyed off each target node's line/column span, so the
rest of the file's formatting is untouched and `bug_line` is exact.
"""
from __future__ import annotations

import argparse
import ast
import difflib
import json
import os
import random
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

HERE = Path(__file__).resolve().parent
SNIPPETS_DIR = HERE / "snippets"

BUG_TYPES = [
    "off_by_one",
    "wrong_comparison",
    "none_check",
    "wrong_variable",
    "type_coercion",
    "mutable_default",
    "index_slice",
]


class BugInjectionError(Exception):
    """Raised when a snippet's source doesn't match the shape its mutator expects."""


# --------------------------------------------------------------------------
# Mutators. Each takes the clean source text (+ mutator-specific kwargs) and
# returns (buggy_source_text, bug_line, description). Every mutator parses
# the source with `ast` to *locate* the single target node, then performs a
# precise text splice using that node's line/column span -- the rest of the
# file is byte-identical to the input.
# --------------------------------------------------------------------------

def _lines(source: str) -> list[str]:
    return source.splitlines(keepends=True)


def _splice_single_line(source: str, lineno: int, col: int, end_col: int, new_text: str) -> str:
    lines = _lines(source)
    line = lines[lineno - 1]
    lines[lineno - 1] = line[:col] + new_text + line[end_col:]
    return "".join(lines)


def _require_single(matches: list, what: str) -> Any:
    if len(matches) != 1:
        raise BugInjectionError(f"expected exactly one {what}, found {len(matches)}")
    return matches[0]


def inject_off_by_one(source: str) -> tuple[str, int, str]:
    tree = ast.parse(source)
    calls = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "range"
    ]
    call = _require_single(calls, "range(...) call")
    arg = call.args[-1]
    if arg.lineno != arg.end_lineno:
        raise BugInjectionError("range bound must be a single-line expression")
    line = _lines(source)[arg.lineno - 1]
    original_text = line[arg.col_offset:arg.end_col_offset]
    replacement = f"({original_text}) - 1"
    new_source = _splice_single_line(source, arg.lineno, arg.col_offset, arg.end_col_offset, replacement)
    return new_source, arg.lineno, f"range bound reduced by 1: `{original_text}` -> `{replacement}` (drops the final loop iteration)"


_COMPARE_FLIP = {
    ast.Lt: ast.LtE,
    ast.LtE: ast.Lt,
    ast.Gt: ast.GtE,
    ast.GtE: ast.Gt,
    ast.Eq: ast.NotEq,
    ast.NotEq: ast.Eq,
}
_OP_SYMBOL = {ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=", ast.Eq: "==", ast.NotEq: "!="}


def inject_wrong_comparison(source: str) -> tuple[str, int, str]:
    tree = ast.parse(source)
    compares = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Compare) and len(n.ops) == 1 and type(n.ops[0]) in _COMPARE_FLIP
    ]
    cmp = _require_single(compares, "simple two-operand comparison")
    left, right = cmp.left, cmp.comparators[0]
    if left.end_lineno != right.lineno:
        raise BugInjectionError("comparison must be a single-line expression")
    old_op, new_op = type(cmp.ops[0]), _COMPARE_FLIP[type(cmp.ops[0])]
    old_sym, new_sym = _OP_SYMBOL[old_op], _OP_SYMBOL[new_op]
    line = _lines(source)[left.end_lineno - 1]
    gap = line[left.end_col_offset:right.col_offset]
    if old_sym not in gap:
        raise BugInjectionError(f"could not locate operator {old_sym!r} between operands (gap={gap!r})")
    new_gap = gap.replace(old_sym, new_sym, 1)
    new_source = _splice_single_line(source, left.end_lineno, left.end_col_offset, right.col_offset, new_gap)
    return new_source, left.end_lineno, f"comparison operator changed from `{old_sym}` to `{new_sym}`"


def inject_none_check(source: str) -> tuple[str, int, str]:
    tree = ast.parse(source)

    class Finder(ast.NodeVisitor):
        def __init__(self) -> None:
            self.matches: list[ast.If] = []

        def visit_If(self, node: ast.If) -> None:
            t = node.test
            if (
                isinstance(t, ast.Compare) and len(t.ops) == 1 and isinstance(t.ops[0], ast.IsNot)
                and len(t.comparators) == 1 and isinstance(t.comparators[0], ast.Constant)
                and t.comparators[0].value is None and not node.orelse
            ):
                self.matches.append(node)
            self.generic_visit(node)

    finder = Finder()
    finder.visit(tree)
    target = _require_single(finder.matches, "`if x is not None:` guard with no else")

    lines = _lines(source)
    if_indent = target.col_offset
    body_indent = target.body[0].col_offset
    dedent = body_indent - if_indent
    guard_start, body_end = target.lineno, target.end_lineno
    body_start = target.body[0].lineno

    new_body_lines = []
    for lineno in range(body_start, body_end + 1):
        line = lines[lineno - 1]
        if len(line) >= dedent and line[:dedent].strip() == "":
            new_body_lines.append(line[dedent:])
        else:
            new_body_lines.append(line)

    new_lines = lines[:guard_start - 1] + new_body_lines + lines[body_end:]
    new_source = "".join(new_lines)
    return new_source, guard_start, f"removed `is not None` guard (was lines {guard_start}-{body_end}); body now runs unconditionally"


def inject_wrong_variable(source: str, correct_name: str, decoy_name: str) -> tuple[str, int, str]:
    tree = ast.parse(source)

    class Finder(ast.NodeVisitor):
        def __init__(self) -> None:
            self.matches: list[ast.Return] = []

        def visit_Return(self, node: ast.Return) -> None:
            if isinstance(node.value, ast.Name) and node.value.id == correct_name:
                self.matches.append(node)
            self.generic_visit(node)

    finder = Finder()
    finder.visit(tree)
    ret = _require_single(finder.matches, f"`return {correct_name}` statement")
    name_node = ret.value
    new_source = _splice_single_line(source, name_node.lineno, name_node.col_offset, name_node.end_col_offset, decoy_name)
    return new_source, name_node.lineno, f"return value changed from `{correct_name}` to shadowing/copy-paste variable `{decoy_name}`"


def inject_type_coercion(source: str) -> tuple[str, int, str]:
    tree = ast.parse(source)
    calls = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in ("int", "str", "float")
        and len(n.args) == 1 and not n.keywords
    ]
    call = _require_single(calls, "int()/str()/float() single-arg cast call")
    arg = call.args[0]
    if call.lineno != call.end_lineno:
        raise BugInjectionError("cast call must be a single-line expression")
    line = _lines(source)[call.lineno - 1]
    arg_text = line[arg.col_offset:arg.end_col_offset]
    new_source = _splice_single_line(source, call.lineno, call.col_offset, call.end_col_offset, arg_text)
    func_name = call.func.id
    return new_source, call.lineno, f"removed `{func_name}()` cast, leaving raw expression `{arg_text}`"


def inject_mutable_default(source: str, container: str = "list") -> tuple[str, int, str]:
    tree = ast.parse(source)
    targets: list[tuple[ast.FunctionDef, ast.Constant, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            n_positional = len(node.args.args)
            n_defaults = len(node.args.defaults)
            offset = n_positional - n_defaults
            for i, default in enumerate(node.args.defaults):
                if isinstance(default, ast.Constant) and default.value is None:
                    param_name = node.args.args[offset + i].arg
                    targets.append((node, default, param_name))
    fn, default_node, param_name = _require_single(targets, "function with a `None`-defaulted parameter")
    new_text = "[]" if container == "list" else "{}"
    new_source = _splice_single_line(source, default_node.lineno, default_node.col_offset, default_node.end_col_offset, new_text)
    return new_source, default_node.lineno, f"default for `{param_name}` changed from `None` to shared mutable `{new_text}`"


def inject_index_slice(source: str, bound: str = "lower", delta: int = -1) -> tuple[str, int, str]:
    tree = ast.parse(source)
    subs = [n for n in ast.walk(tree) if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Slice)]
    sub = _require_single(subs, "subscript with a slice")
    sl = sub.slice
    node = getattr(sl, bound)
    if node is None or not isinstance(node, ast.Constant) or not isinstance(node.value, int):
        raise BugInjectionError(f"slice `{bound}` bound is not an int constant")
    new_val = node.value + delta
    new_source = _splice_single_line(source, node.lineno, node.col_offset, node.end_col_offset, str(new_val))
    return new_source, node.lineno, f"slice `{bound}` bound changed from `{node.value}` to `{new_val}`"


MUTATORS: dict[str, Callable[..., tuple[str, int, str]]] = {
    "off_by_one": inject_off_by_one,
    "wrong_comparison": inject_wrong_comparison,
    "none_check": inject_none_check,
    "wrong_variable": inject_wrong_variable,
    "type_coercion": inject_type_coercion,
    "mutable_default": inject_mutable_default,
    "index_slice": inject_index_slice,
}


def _loader_boilerplate(module_identifier: str, filename: str) -> str:
    return (
        "import importlib.util\n"
        "from pathlib import Path\n\n"
        f'_spec = importlib.util.spec_from_file_location("{module_identifier}", Path(__file__).parent / "{filename}")\n'
        f"{module_identifier} = importlib.util.module_from_spec(_spec)\n"
        f"_spec.loader.exec_module({module_identifier})\n\n"
        f"globals().update({{k: v for k, v in vars({module_identifier}).items() if not k.startswith('_')}})\n\n"
    )


@dataclass
class Snippet:
    slug: str
    clean_source: str
    test_body: str  # test functions only; loader boilerplate is prepended at write time
    mutator_kwargs: dict = field(default_factory=dict)


# --------------------------------------------------------------------------
# The 30 snippets, grouped by the bug type they'll receive. Placement into
# the final round-robin task order happens in build_tasks().
# --------------------------------------------------------------------------

OFF_BY_ONE: list[Snippet] = [
    Snippet(
        "sum_first_n",
        '''def sum_first_n(nums, n):
    """Sum the first n elements of nums."""
    total = 0
    for i in range(n):
        total += nums[i]
    return total
''',
        '''def test_sum_first_n_partial():
    assert sum_first_n([1, 2, 3, 4], 3) == 6


def test_sum_first_n_full_list():
    assert sum_first_n([5, 5, 5], 3) == 15
''',
    ),
    Snippet(
        "vowel_count_prefix",
        '''def vowel_count_prefix(s, k):
    """Count vowels in the first k characters of s."""
    vowels = set("aeiouAEIOU")
    count = 0
    for i in range(k):
        if s[i] in vowels:
            count += 1
    return count
''',
        '''def test_vowel_count_prefix_full_word():
    assert vowel_count_prefix("hello", 5) == 2


def test_vowel_count_prefix_no_vowels():
    assert vowel_count_prefix("rhythm", 6) == 0
''',
    ),
    Snippet(
        "reverse_prefix",
        '''def reverse_prefix(s, n):
    """Return the first n characters of s, reversed."""
    result = ""
    for i in range(n):
        result = s[i] + result
    return result
''',
        '''def test_reverse_prefix_basic():
    assert reverse_prefix("abcdef", 4) == "dcba"


def test_reverse_prefix_whole_string():
    assert reverse_prefix("hi", 2) == "ih"
''',
    ),
    Snippet(
        "count_positive_in_first_n",
        '''def count_positive_in_first_n(nums, n):
    """Count how many of the first n numbers are positive."""
    count = 0
    for i in range(n):
        if nums[i] > 0:
            count += 1
    return count
''',
        '''def test_count_positive_in_first_n_basic():
    assert count_positive_in_first_n([1, -2, 3, -4, 5], 5) == 3


def test_count_positive_in_first_n_prefix():
    assert count_positive_in_first_n([1, 2, -3, 4], 2) == 2
''',
    ),
    Snippet(
        "multiples_of_k_up_to",
        '''def multiples_of_k_up_to(n, k):
    """Count multiples of k in the inclusive range 1..n."""
    count = 0
    for i in range(1, n + 1):
        if i % k == 0:
            count += 1
    return count
''',
        '''def test_multiples_of_k_up_to_inclusive_boundary():
    assert multiples_of_k_up_to(9, 3) == 3


def test_multiples_of_k_up_to_no_multiples():
    assert multiples_of_k_up_to(5, 7) == 0
''',
    ),
]

WRONG_COMPARISON: list[Snippet] = [
    Snippet(
        "is_eligible_voter",
        '''def is_eligible_voter(age):
    """Return True if someone of this age is eligible to vote."""
    minimum_voting_age = 18
    return age >= minimum_voting_age
''',
        '''def test_is_eligible_voter_at_boundary():
    assert is_eligible_voter(18) is True


def test_is_eligible_voter_below_boundary():
    assert is_eligible_voter(17) is False
''',
    ),
    Snippet(
        "is_below_freezing",
        '''def is_below_freezing(temp_celsius):
    """Return True if the temperature (Celsius) is below the freezing point of water."""
    freezing_point = 0
    return temp_celsius < freezing_point
''',
        '''def test_is_below_freezing_at_boundary():
    assert is_below_freezing(0) is False


def test_is_below_freezing_negative():
    assert is_below_freezing(-5) is True
''',
    ),
    Snippet(
        "is_within_budget",
        '''def is_within_budget(spent, budget):
    """Return True if the amount spent does not exceed the budget."""
    return spent <= budget
''',
        '''def test_is_within_budget_at_boundary():
    assert is_within_budget(100, 100) is True


def test_is_within_budget_over():
    assert is_within_budget(150, 100) is False
''',
    ),
    Snippet(
        "exceeds_speed_limit",
        '''def exceeds_speed_limit(speed, limit):
    """Return True if the given speed is over the posted limit."""
    return speed > limit
''',
        '''def test_exceeds_speed_limit_at_boundary():
    assert exceeds_speed_limit(60, 60) is False


def test_exceeds_speed_limit_over():
    assert exceeds_speed_limit(65, 60) is True
''',
    ),
    Snippet(
        "passwords_differ",
        '''def passwords_differ(entered, expected):
    """Return True if the entered password does not match the expected one."""
    return entered != expected
''',
        '''def test_passwords_differ_when_matching():
    assert passwords_differ("secret", "secret") is False


def test_passwords_differ_when_mismatched():
    assert passwords_differ("secret", "wrong") is True
''',
    ),
]

NONE_CHECK: list[Snippet] = [
    Snippet(
        "format_full_name",
        '''def format_full_name(first, last, middle=None):
    """Combine first, optional middle, and last names into one string."""
    parts = [first]
    if middle is not None:
        parts.append(middle.strip())
    parts.append(last)
    return " ".join(parts)
''',
        '''def test_format_full_name_without_middle():
    assert format_full_name("Ada", "Lovelace") == "Ada Lovelace"


def test_format_full_name_with_middle():
    assert format_full_name("Ada", "Lovelace", " Marie ") == "Ada Marie Lovelace"
''',
    ),
    Snippet(
        "total_extra_items",
        '''def total_extra_items(base_items, extra_items=None):
    """Return the combined count of base_items plus any extra_items provided."""
    count = len(base_items)
    if extra_items is not None:
        count += len(extra_items)
    return count
''',
        '''def test_total_extra_items_without_extra():
    assert total_extra_items(["a", "b"]) == 2


def test_total_extra_items_with_extra():
    assert total_extra_items(["a", "b"], ["c", "d", "e"]) == 5
''',
    ),
    Snippet(
        "discounted_price",
        '''def discounted_price(price, coupon=None):
    """Apply a coupon's discount to price if a coupon is provided."""
    final_price = price
    if coupon is not None:
        final_price = price - coupon.amount
    return round(final_price, 2)
''',
        '''from types import SimpleNamespace


def test_discounted_price_without_coupon():
    assert discounted_price(100) == 100


def test_discounted_price_with_coupon():
    coupon = SimpleNamespace(amount=15)
    assert discounted_price(100, coupon) == 85
''',
    ),
    Snippet(
        "merge_tags",
        '''def merge_tags(existing_tags, new_tags=None):
    """Merge new_tags into existing_tags, avoiding duplicates, if new_tags is given."""
    merged = list(existing_tags)
    if new_tags is not None:
        for tag in new_tags:
            if tag not in merged:
                merged.append(tag)
    return merged
''',
        '''def test_merge_tags_without_new_tags():
    assert merge_tags(["a", "b"]) == ["a", "b"]


def test_merge_tags_with_new_tags():
    assert merge_tags(["a"], ["b", "a"]) == ["a", "b"]
''',
    ),
]

WRONG_VARIABLE: list[Snippet] = [
    Snippet(
        "average",
        '''def average(nums):
    """Return the arithmetic mean of a list of numbers."""
    total = sum(nums)
    count = len(nums)
    mean = total / count
    return mean
''',
        '''def test_average_basic():
    assert average([2, 4, 6]) == 4.0


def test_average_single_value():
    assert average([10]) == 10.0
''',
        {"correct_name": "mean", "decoy_name": "total"},
    ),
    Snippet(
        "apply_discount",
        '''def apply_discount(price, discount_rate):
    """Apply a percentage discount to a price and return the discounted price."""
    discount_amount = price * discount_rate
    discounted_price = price - discount_amount
    return discounted_price
''',
        '''def test_apply_discount_basic():
    assert apply_discount(100, 0.2) == 80


def test_apply_discount_no_discount():
    assert apply_discount(50, 0.0) == 50
''',
        {"correct_name": "discounted_price", "decoy_name": "discount_amount"},
    ),
    Snippet(
        "normalize_score",
        '''def normalize_score(raw_score, max_score):
    """Scale raw_score to a 0-100 range given the maximum possible score."""
    ratio = raw_score / max_score
    percentage = ratio * 100
    return percentage
''',
        '''def test_normalize_score_basic():
    assert normalize_score(50, 200) == 25.0


def test_normalize_score_full_marks():
    assert normalize_score(80, 80) == 100.0
''',
        {"correct_name": "percentage", "decoy_name": "ratio"},
    ),
    Snippet(
        "full_address",
        '''def full_address(street, city, zip_code):
    """Build a formatted one-line mailing address string."""
    partial_address = f"{street}, {city}"
    complete_address = f"{partial_address} {zip_code}"
    return complete_address
''',
        '''def test_full_address_basic():
    assert full_address("1 Main St", "Springfield", "12345") == "1 Main St, Springfield 12345"


def test_full_address_other_city():
    assert full_address("42 Oak Ave", "Metropolis", "99999") == "42 Oak Ave, Metropolis 99999"
''',
        {"correct_name": "complete_address", "decoy_name": "partial_address"},
    ),
]

TYPE_COERCION: list[Snippet] = [
    Snippet(
        "format_countdown",
        '''def format_countdown(seconds_left):
    """Return a countdown message like 'T-minus 5' from a numeric value."""
    return "T-minus " + str(seconds_left)
''',
        '''def test_format_countdown_basic():
    assert format_countdown(5) == "T-minus 5"


def test_format_countdown_zero():
    assert format_countdown(0) == "T-minus 0"
''',
    ),
    Snippet(
        "parse_quantity",
        '''def parse_quantity(raw_value):
    """Parse a quantity string like ' 42 ' from user input into an integer."""
    return int(raw_value.strip())
''',
        '''def test_parse_quantity_basic():
    assert parse_quantity(" 42 ") == 42


def test_parse_quantity_arithmetic():
    assert parse_quantity("4") + 1 == 5
''',
    ),
    Snippet(
        "total_price_display",
        '''def total_price_display(cents):
    """Convert a price in cents (int) to a dollar-formatted string, e.g. 1050 -> '$10.5'."""
    dollars = cents / 100
    return "$" + str(round(dollars, 2))
''',
        '''def test_total_price_display_basic():
    assert total_price_display(1050) == "$10.5"


def test_total_price_display_whole_dollars():
    assert total_price_display(500) == "$5.0"
''',
    ),
    Snippet(
        "average_age_label",
        '''def average_age_label(ages):
    """Compute the rounded average age and return it as a whole-number string label."""
    avg = sum(ages) / len(ages)
    rounded = round(avg)
    return "Average age: " + str(rounded)
''',
        '''def test_average_age_label_basic():
    assert average_age_label([10, 20, 30]) == "Average age: 20"


def test_average_age_label_single():
    assert average_age_label([25]) == "Average age: 25"
''',
    ),
]

MUTABLE_DEFAULT: list[Snippet] = [
    Snippet(
        "add_item_to_cart",
        '''def add_item_to_cart(item, cart=None):
    """Add an item to a shopping cart list, creating a new cart if none is given."""
    if cart is None:
        cart = []
    cart.append(item)
    return cart
''',
        '''def test_add_item_to_cart_basic():
    assert add_item_to_cart("apple") == ["apple"]


def test_add_item_to_cart_independent_calls():
    add_item_to_cart("apple")
    assert add_item_to_cart("banana") == ["banana"]
''',
        {"container": "list"},
    ),
    Snippet(
        "increment_counter",
        '''def increment_counter(key, counters=None):
    """Increment the count for `key` in a counters dict, creating a new dict if none is given."""
    if counters is None:
        counters = {}
    counters[key] = counters.get(key, 0) + 1
    return counters
''',
        '''def test_increment_counter_basic():
    assert increment_counter("a") == {"a": 1}


def test_increment_counter_independent_calls():
    increment_counter("a")
    assert increment_counter("b") == {"b": 1}
''',
        {"container": "dict"},
    ),
    Snippet(
        "tag_document",
        '''def tag_document(doc_id, tags=None):
    """Return a dict mapping doc_id to a list of tags, using a fresh list by default."""
    if tags is None:
        tags = []
    tags.append("reviewed")
    return {"doc_id": doc_id, "tags": tags}
''',
        '''def test_tag_document_basic():
    assert tag_document("doc1") == {"doc_id": "doc1", "tags": ["reviewed"]}


def test_tag_document_independent_calls():
    tag_document("doc1")
    result = tag_document("doc2")
    assert result["tags"] == ["reviewed"]
''',
        {"container": "list"},
    ),
    Snippet(
        "unique_visitors",
        '''def unique_visitors(session_id, seen=None):
    """Track and return the list of unique session_ids seen so far."""
    if seen is None:
        seen = []
    if session_id not in seen:
        seen.append(session_id)
    return seen
''',
        '''def test_unique_visitors_basic():
    assert unique_visitors("s1") == ["s1"]


def test_unique_visitors_independent_calls():
    unique_visitors("s1")
    assert unique_visitors("s2") == ["s2"]
''',
        {"container": "list"},
    ),
]

INDEX_SLICE: list[Snippet] = [
    Snippet(
        "strip_outer_chars",
        '''def strip_outer_chars(s):
    """Remove the first and last character of a string of at least 2 characters."""
    return s[1:len(s) - 1]
''',
        '''def test_strip_outer_chars_basic():
    assert strip_outer_chars("[hello]") == "hello"


def test_strip_outer_chars_quotes():
    assert strip_outer_chars('"hi"') == "hi"
''',
        {"bound": "lower", "delta": -1},
    ),
    Snippet(
        "drop_header_rows",
        '''def drop_header_rows(rows):
    """Return all data rows after skipping the first 2 header rows."""
    return rows[2:]
''',
        '''def test_drop_header_rows_basic():
    assert drop_header_rows(["h1", "h2", "d1", "d2"]) == ["d1", "d2"]


def test_drop_header_rows_extra_data():
    assert drop_header_rows(["h1", "h2", "d1", "d2", "d3"]) == ["d1", "d2", "d3"]
''',
        {"bound": "lower", "delta": -1},
    ),
    Snippet(
        "recent_top_scores",
        '''def recent_top_scores(scores):
    """Return the top 3 highest scores from the given scores list."""
    return sorted(scores, reverse=True)[:3]
''',
        '''def test_recent_top_scores_basic():
    assert recent_top_scores([50, 90, 10, 70, 30]) == [90, 70, 50]


def test_recent_top_scores_few_scores():
    assert recent_top_scores([5, 1]) == [5, 1]
''',
        {"bound": "upper", "delta": -1},
    ),
    Snippet(
        "skip_first_and_last_pair",
        '''def skip_first_and_last_pair(items):
    """Return items with the first two and last two elements removed."""
    return items[2:-2]
''',
        '''def test_skip_first_and_last_pair_basic():
    assert skip_first_and_last_pair([1, 2, 3, 4, 5, 6, 7, 8]) == [3, 4, 5, 6]


def test_skip_first_and_last_pair_min_size():
    assert skip_first_and_last_pair([1, 2, 3, 4, 5]) == [3]
''',
        {"bound": "lower", "delta": -1},
    ),
]

BUCKETS: dict[str, list[Snippet]] = {
    "off_by_one": OFF_BY_ONE,
    "wrong_comparison": WRONG_COMPARISON,
    "none_check": NONE_CHECK,
    "wrong_variable": WRONG_VARIABLE,
    "type_coercion": TYPE_COERCION,
    "mutable_default": MUTABLE_DEFAULT,
    "index_slice": INDEX_SLICE,
}


def build_tasks() -> list[dict]:
    """Assign snippets to 30 task slots round-robin over BUG_TYPES."""
    cursors = {bt: 0 for bt in BUG_TYPES}
    tasks = []
    for i in range(30):
        bug_type = BUG_TYPES[i % len(BUG_TYPES)]
        bucket = BUCKETS[bug_type]
        snippet = bucket[cursors[bug_type]]
        cursors[bug_type] += 1
        tasks.append({"task_id": i + 1, "bug_type": bug_type, "snippet": snippet})
    for bt, cursor in cursors.items():
        assert cursor == len(BUCKETS[bt]), f"{bt}: used {cursor} of {len(BUCKETS[bt])} snippets"
    return tasks


def run_pytest(test_path: Path) -> tuple[bool, str]:
    # Bytecode caching keyed on mtime can go stale within the same second
    # when clean/buggy source is rewritten in quick succession -- disable it
    # and clear any existing cache so each run reflects the file on disk.
    cache_dir = test_path.parent / "__pycache__"
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
    result = subprocess.run(
        [sys.executable, "-B", "-m", "pytest", str(test_path), "-q", "-p", "no:cacheprovider"],
        capture_output=True, text=True, cwd=str(test_path.parent),
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    return result.returncode == 0, (result.stdout + result.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=1337, help="seed for the shared task-order shuffle")
    parser.add_argument("--out-dir", type=Path, default=HERE, help="corpus/ output directory")
    args = parser.parse_args()

    snippets_dir = args.out_dir / "snippets"
    snippets_dir.mkdir(parents=True, exist_ok=True)

    tasks = build_tasks()
    records = []

    for task in tasks:
        task_id = task["task_id"]
        bug_type = task["bug_type"]
        snippet: Snippet = task["snippet"]
        stem = f"{task_id:02d}"
        module_identifier = f"task{stem}_buggy"
        buggy_filename = f"{stem}_buggy.py"

        clean_path = snippets_dir / f"{stem}_clean.py"
        buggy_path = snippets_dir / buggy_filename
        test_path = snippets_dir / f"{stem}_test.py"

        mutator = MUTATORS[bug_type]
        buggy_source, bug_line, description = mutator(snippet.clean_source, **snippet.mutator_kwargs)

        test_source = _loader_boilerplate(module_identifier, buggy_filename) + snippet.test_body

        clean_path.write_text(snippet.clean_source)
        test_path.write_text(test_source)

        # Verify the clean/golden version passes the test.
        buggy_path.write_text(snippet.clean_source)
        ok, output = run_pytest(test_path)
        if not ok:
            raise BugInjectionError(f"task {task_id} ({snippet.slug}): golden version failed its own test:\n{output}")

        # Verify the mutated version fails the same test.
        buggy_path.write_text(buggy_source)
        ok, output = run_pytest(test_path)
        if ok:
            raise BugInjectionError(f"task {task_id} ({snippet.slug}): buggy version unexpectedly passed its test:\n{output}")

        golden_fix_diff = "".join(difflib.unified_diff(
            buggy_source.splitlines(keepends=True),
            snippet.clean_source.splitlines(keepends=True),
            fromfile=f"{stem}_buggy.py (as given)",
            tofile=f"{stem}_buggy.py (golden fix)",
        ))

        checker_cmd = f"pytest corpus/snippets/{stem}_test.py -q"

        records.append({
            "id": task_id,
            "slug": snippet.slug,
            "snippet_path": f"corpus/snippets/{stem}_buggy.py",
            "test_path": f"corpus/snippets/{stem}_test.py",
            "bug_type": bug_type,
            "bug_line": bug_line,
            "bug_description": description,
            "golden_fix_diff": golden_fix_diff,
            "checker_cmd": checker_cmd,
        })
        print(f"task {task_id:2d}  [{bug_type:<17s}]  {snippet.slug:<28s}  bug_line={bug_line:<3d}  OK")

    tasks_path = args.out_dir / "tasks.jsonl"
    with tasks_path.open("w") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")

    rng = random.Random(args.seed)
    order = list(range(1, 31))
    rng.shuffle(order)
    order_path = args.out_dir / "task_order.json"
    order_path.write_text(json.dumps({"seed": args.seed, "order": order}, indent=2) + "\n")

    counts: dict[str, int] = {}
    for r in records:
        counts[r["bug_type"]] = counts.get(r["bug_type"], 0) + 1
    print("\nbug_type distribution:", counts)
    print(f"wrote {len(records)} tasks -> {tasks_path}")
    print(f"wrote shuffled task order (seed={args.seed}) -> {order_path}")


if __name__ == "__main__":
    main()
