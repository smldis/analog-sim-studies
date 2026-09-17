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


def test_saved_canonical_boundaries_compose_with_architecture_inspection(tmp_path):
    from spice_canonical.canonical_netlist import from_canonical_file, from_file
    from netlist_comparison import Options, project_saved_report

    source = '.subckt AMP I O SCALE=2\nXM O I 0 0 nmos_lvt W=1u\n.ends\nXamp in out AMP SCALE=3\n'
    interfaces = {'nmos_lvt': ['d', 'g', 's', 'b']}
    artifacts = []
    for side, text in [('a', source), ('b', source.replace('W=1u', 'W=3u'))]:
        deck = tmp_path / f'{side}.sp'
        deck.write_text(text)
        extracted = from_file(deck, external_subcircuits=interfaces)
        path = tmp_path / f'{side}.canonical'
        path.write_text(extracted.render())
        deck.unlink()
        artifacts.append(from_canonical_file(path))
    report = compare(*artifacts, top_a='TOP', top_b='TOP',
                     options=Options(black_box_missing=True, matching_mode='regional'))
    assert report['a']['black_box_leaf_count'] == 1
    assert report['a']['coverage']['opaque'] == 0
    assert len(report['representative_pair_ids']) == 1
    ordinary = project_saved_report(report)
    focused = project_saved_report(report, omit_parameters=True, group_depth=1)
    assert ordinary['findings']['raw_pairs'][0]['raw_differences'] == [
        {'field': 'parameters.W', 'a': ['1u'], 'b': ['3u']}]
    assert focused['findings']['raw_pairs'] == []
    assert focused['source_scope'] == ordinary['source_scope']
    assert focused['context']['hierarchy'] == report['hierarchy']
    assert focused['hierarchy_groups']
