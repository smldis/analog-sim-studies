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


def test_saved_canonical_diagnostics_are_opt_in_for_comparison():
    from spice_canonical.canonical_netlist import from_canonical_text

    extracted = from_text('X1 a MISSING\n')
    ordinary = from_canonical_text(extracted.render())
    with_diagnostics = from_canonical_text(extracted.render(include_diagnostics=True))

    assert ordinary.diagnostics == ()
    assert with_diagnostics.diagnostics == extracted.diagnostics
    assert compare(ordinary, ordinary, top_a='TOP', top_b='TOP')['a']['diagnostics'] == []
    assert len(compare(with_diagnostics, with_diagnostics,
                       top_a='TOP', top_b='TOP')['a']['diagnostics']) == 1


def test_actual_calls_preserve_canonical_defaults_and_physical_binding():
    from netlist_comparison import compare_instances
    source = '.subckt C A B W=2u\nR1 A n W\nC1 n B 1p\n.ends\nX1 in 0 C W=3u\nX2 out 0 C W=4u'
    report = compare_instances(from_text(source), top='TOP', path_a='TOP/X1', path_b='TOP/X2')
    assert report['a']['selection']['defaults'] == [{'name': 'W', 'value': '2u'}]
    assert report['b']['selection']['overrides'] == [{'name': 'W', 'value': '4u'}]
    assert report['boundary']['a']['pins'][0]['resolved_parent_net'] == 'local:TOP:in'
    assert report['boundary']['b']['pins'][0]['resolved_parent_net'] == 'local:TOP:out'


def test_operator_batch_keeps_canonical_blackbox_scope_and_independent_reports():
    from netlist_comparison import InputScope, Options, compare_operator_scoped_batch
    from netlist_comparison.operator_scoped import validate_saved_extension

    data = from_text('.subckt BLOCK A B\nR1 A B 1k\n.ends\n'
                     'X1 in 0 BLOCK\nX2 out 0 BLOCK')
    windows = [
        {'paths_a': ('TOP/X1',), 'paths_b': ('TOP/X2',)},
        {'paths_a': ('TOP/X2',), 'paths_b': ('TOP/X1',)},
    ]
    scope = InputScope(global_nets=('0',), globals_complete=True)
    batch = compare_operator_scoped_batch(
        data, data, top_a='TOP', top_b='TOP', windows=windows,
        options=Options(matching_mode='operator_scoped', black_box_missing=True),
        scope_a=scope, scope_b=scope, same_full_netlist=True,
    )
    assert batch['kind'] == 'operator_scoped_batch_v1'
    assert not batch['resources']['incomplete']
    assert len(batch['results']) == len(windows)
    for index, report in enumerate(batch['results']):
        extension = report['operator_scoped']
        validate_saved_extension(extension)
        assert extension['resources']['batch_window_index'] == index
        assert extension['windows'][0]['supplied_scopes'] == {
            'a': list(windows[index]['paths_a']),
            'b': list(windows[index]['paths_b']),
        }
        assert report['scope']['global_net_declarations_complete']


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
