"""Canonical's defaults remain visible through the comparison boundary."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for unit in ("spice-canonical", "netlist-comparison"):
    sys.path.insert(0, str(ROOT / unit / "src"))

from spice_canonical.canonical_netlist import from_text
from netlist_comparison import compare


def test_current_canonical_objects_preserve_default_and_override_scopes():
    source = ".subckt C A B W=2u\nR1 A B W\nC1 A B 1p\n.ends\nX1 in 0 C W=3u"
    a = from_text(source)
    b = from_text(source.replace("W=2u", "W=5u"))
    result = compare(a, b, top_a="TOP", top_b="TOP")
    row = next(x for x in result["hierarchy"]["definition_options"] if x["a"] == x["b"] == "C")
    assert row["raw_differences"] == [{"field": "defaults.W", "a": ["2u"], "b": ["5u"]}]
    occurrence = next(o for o in result["a"]["occurrences"] if o["path"] == "TOP/X1")
    assert occurrence["overrides"] == [{"name": "W", "value": "3u"}]
    assert result["scope"]["comparison"] == "represented_structure"


def test_actual_calls_preserve_canonical_defaults_and_physical_binding():
    from netlist_comparison import compare_instances
    source = '.subckt C A B W=2u\nR1 A n W\nC1 n B 1p\n.ends\nX1 in 0 C W=3u\nX2 out 0 C W=4u'
    report = compare_instances(from_text(source), top='TOP', path_a='TOP/X1', path_b='TOP/X2')
    assert report['a']['selection']['defaults'] == [{'name': 'W', 'value': '2u'}]
    assert report['b']['selection']['overrides'] == [{'name': 'W', 'value': '4u'}]
    assert report['boundary']['a']['pins'][0]['resolved_parent_net'] == 'local:TOP:in'
    assert report['boundary']['b']['pins'][0]['resolved_parent_net'] == 'local:TOP:out'
