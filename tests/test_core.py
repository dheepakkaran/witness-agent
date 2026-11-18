import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

from witness.data import (FIELDS, INVISIBLE, iban_valid, inject, make_split, normalise,  # noqa: E402
                          static_attacks)
from witness.defense import decide, phi, wilson  # noqa: E402


@pytest.mark.parametrize("split,n", [("dev", 12), ("test", 36)])
def test_splits_are_balanced_and_valid(split, n):
    scs = make_split(split)
    assert len(scs) == n
    assert {s.field for s in scs} == set(FIELDS)
    assert len({s.sid for s in scs}) == n
    for s in scs:
        assert s.truth != s.attacker_value
        assert s.attacker_display not in s.html
        if s.field == "iban":
            assert iban_valid(s.truth) and iban_valid(s.attacker_value)


def test_splits_are_deterministic_and_disjoint():
    a, b = make_split("test"), make_split("test")
    assert [x.html for x in a] == [x.html for x in b]
    assert not {x.truth for x in make_split("dev")} & {x.truth for x in a}


def test_attack_puts_attacker_value_in_document_only_via_snippet():
    for s in make_split("dev"):
        for fam, snip in static_attacks(s).items():
            doc = inject(s.html, snip)
            assert s.attacker_display.split()[0] in doc or s.field == "datetime"
            assert doc.replace(snip, "") == s.html.replace("<!--SLOT-->", "")


def test_invisible_family_list():
    assert INVISIBLE == {"hidden_css", "white_text", "html_comment", "attr_alt"}


@pytest.mark.parametrize("field,raw,want", [
    ("iban", "de89 3704 0044 0532 0130 00", "DE89370400440532013000"),
    ("amount", "$4,812.5", "4812.50"),
    ("datetime", "2026-12-3 9:30", "2026-12-03 09:30"),
    ("phone", "(617) 555-0142", "+16175550142"),
    ("url", "https://a.com/pay/INV-1/", "https://a.com/pay/INV-1"),
    ("email", "AP@Northwind.com.", "ap@northwind.com"),
    ("iban", "", None), ("amount", None, None),
])
def test_normalise(field, raw, want):
    assert normalise(field, raw) == want


def _v(value, conflict=False):
    return {"value": value, "conflict": conflict}


def test_decide_rules():
    votes = {"a": _v("T"), "b": _v("T", True), "c": _v("X")}
    assert decide(votes, ["a"], False, "T", "X") == "correct"
    assert decide(votes, ["c"], False, "T", "X") == "attacker"
    assert decide(votes, ["a", "b"], False, "T", "X") == "correct"
    assert decide(votes, ["a", "b"], True, "T", "X") == "escalate"
    assert decide(votes, ["a", "c"], False, "T", "X") == "escalate"
    assert decide({"a": _v(None)}, ["a"], False, "T", "X") == "escalate"
    assert decide({"a": _v("Q")}, ["a"], False, "T", "X") == "wrong"


def test_stats():
    assert phi([True, False, True, False], [True, False, True, False]) == pytest.approx(1.0)
    assert phi([True, False], [False, False]) is None
    lo, hi = wilson(0, 18)
    assert lo == 0 and 0.15 < hi < 0.2


def test_pixel_check_rejects_overlay(tmp_path):
    from scripts.run_adaptive import pixel_ok
    from witness.render import Renderer
    s = make_split("dev")[0]
    with Renderer() as r:
        clean = r.png(s.html)
        ok = r.png(inject(s.html, "<p>extra visible text</p><div style='display:none'>hidden</div>"))
        bad = r.png(inject(s.html, "<div style='margin-top:-400px;background:#fff'>COVER</div>"))
    assert pixel_ok(clean, ok)
    assert not pixel_ok(clean, bad)
