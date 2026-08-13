"""What one invocation asks LSF for, resolved per invocation.

The Plan already decided that this corner needs a large-memory queue and that
one needs a simulator licence. These tests are where that decision becomes
`bsub` arguments on that job and no other.

What they can establish is the request: which flags are built, which options
refuse, and that retuning any of them never invalidates a result. What they
cannot establish is whether LSF *accepts* what we build — no farm is contacted,
and `examples/lsf_preflight.py` is where that question is answered.
"""

import pytest

from hedloom_exec.durability import Durability, execute
from hedloom_exec.lsf import CommandResult, LSFInteractiveTransport
from hedloom_exec.transport import SubmissionRefused

COMMAND = ["simulate", "--corner", "tt"]


class FakeRunner:
    """Records argv and replays canned results, newest command first."""

    def __init__(self, result=None):
        self.calls = []
        self.result = result or CommandResult(returncode=0, stdout="done")

    def __call__(self, argv, *, cwd=None, env=None, timeout=None):
        self.calls.append(list(argv))
        if argv[0] == "bjobs":
            return CommandResult(returncode=255, stderr="Job <x> is not found")
        return self.result


def transport(**kwargs):
    runner = kwargs.pop("runner", None) or FakeRunner()
    walltime = kwargs.pop("walltime", "30")
    lsf = LSFInteractiveTransport(walltime=walltime, runner=runner, **kwargs)
    return lsf, runner


def bundle(**options):
    """A bundle as the driver hands it over, carrying its resolved placement."""

    return {
        "command": COMMAND,
        "placement": {
            "requested": {"name": "lsf-direct", "options": options},
            "resolved": {"placement": "lsf-direct", "transport": "lsf-interactive"},
        },
    }


def flag(argv, name):
    return argv[argv.index(name) + 1] if name in argv else None


def test_one_transport_serves_invocations_with_different_needs():
    """The whole point: the request belongs to the invocation, not the run."""

    lsf, runner = transport(queue="normal")
    lsf.submit("hedloom-cheap", bundle())
    lsf.submit("hedloom-heavy", bundle(queue="bigmem", cores=16))

    cheap, heavy = runner.calls
    assert flag(cheap, "-q") == "normal" and "-n" not in cheap
    assert flag(heavy, "-q") == "bigmem"
    assert flag(heavy, "-n") == "16"


def test_a_declared_licence_becomes_a_request_on_that_job():
    """LSF knows how many licences exist; we only state that this job needs one."""

    lsf, runner = transport()
    lsf.submit("hedloom-abc", bundle(licences={"spectre": 1}))

    assert flag(runner.calls[0], "-R") == "rusage[spectre=1]"


def test_memory_and_licences_compose_into_one_request():
    lsf, runner = transport()
    lsf.submit("hedloom-abc", bundle(memory_mb=8000, licences={"spectre": 2, "ams": 1}))

    assert flag(runner.calls[0], "-R") == "rusage[mem=8000,ams=1,spectre=2]"


def test_a_site_requirement_keeps_its_own_sections():
    """A requirement string is space-separated sections, so both survive."""

    lsf, runner = transport(resources="span[hosts=1]")
    lsf.submit("hedloom-abc", bundle(licences={"spectre": 1}))

    assert flag(runner.calls[0], "-R") == "span[hosts=1] rusage[spectre=1]"


def test_two_rusage_sections_refuse_rather_than_guess():
    """Merging them means inventing semantics; the licence must not be dropped."""

    lsf, runner = transport(resources="rusage[mem=100]")
    with pytest.raises(SubmissionRefused):
        lsf.submit("hedloom-abc", bundle(licences={"spectre": 1}))
    assert runner.calls == []


def test_an_option_this_transport_cannot_express_is_refused():
    lsf, runner = transport()
    with pytest.raises(SubmissionRefused) as raised:
        lsf.submit("hedloom-abc", bundle(gpus=2))

    assert "gpus" in str(raised.value)
    assert runner.calls == [], "nothing may be submitted after a refusal"


def test_a_misspelled_option_does_not_silently_run_anywhere():
    """The failure this vocabulary is closed to prevent."""

    lsf, _ = transport()
    with pytest.raises(SubmissionRefused):
        lsf.submit("hedloom-abc", bundle(queeu="bigmem"))


def test_a_licence_name_that_would_corrupt_the_request_is_refused():
    lsf, runner = transport()
    with pytest.raises(SubmissionRefused):
        lsf.submit("hedloom-abc", bundle(licences={"spectre] rusage[mem": 1}))
    assert runner.calls == []


@pytest.mark.parametrize(
    "options",
    [
        {"cores": 0},
        {"cores": "many"},
        {"memory_mb": -1},
        {"licences": {"spectre": 0}},
        {"licences": ["spectre"]},
        {"walltime": ""},
        {"queue": ""},
    ],
)
def test_an_unusable_request_is_refused_before_anything_is_submitted(options):
    lsf, runner = transport()
    with pytest.raises(SubmissionRefused):
        lsf.submit("hedloom-abc", bundle(**options))
    assert runner.calls == []


def test_walltime_may_be_retuned_per_invocation_but_never_removed():
    lsf, runner = transport(walltime="30")
    lsf.submit("hedloom-abc", bundle(walltime=240))

    assert flag(runner.calls[0], "-W") == "240"


def test_an_invocation_that_declares_nothing_still_gets_the_site_defaults():
    lsf, runner = transport(queue="normal", cores=4, resources="span[hosts=1]")
    lsf.submit("hedloom-abc", {"command": COMMAND})

    argv = runner.calls[0]
    assert flag(argv, "-q") == "normal"
    assert flag(argv, "-n") == "4"
    assert flag(argv, "-R") == "span[hosts=1]"
    assert flag(argv, "-W") == "30"


def test_retuning_the_resource_request_still_reuses_the_result(tmp_path):
    """Placement is not identity, now that placement actually reaches the job.

    A corner that turned out to need more memory is the same experiment. If
    this reruns, every resource tweak silently invalidates a study.
    """

    lsf, runner = transport()
    common = {
        "durability": Durability.RECORDED,
        "root": str(tmp_path),
        "plan_id": "plan-1",
        "invocation_id": "inv-a",
    }

    first = execute(lsf, bundle(queue="normal", memory_mb=2000), **common)
    second = execute(lsf, bundle(queue="bigmem", memory_mb=64000), **common)

    assert first.outcome == "succeeded"
    assert second.disposition == "completed", "moving work must not rerun it"
    assert sum(1 for call in runner.calls if call[0] == "bsub") == 1


def test_what_the_job_asked_for_is_published_with_the_result(tmp_path):
    """A licence-starved or misplaced run is only explainable if this is kept."""

    lsf, _ = transport()
    result = execute(
        lsf,
        bundle(queue="bigmem", cores=8, licences={"spectre": 1}),
        durability=Durability.RECORDED,
        root=str(tmp_path),
        plan_id="plan-1",
        invocation_id="inv-a",
    )

    placement = result.journal.read_manifest()["result"]["placement"]
    settings = placement["observed"]["handle"]["settings"]

    assert placement["requested"]["options"]["licences"] == {"spectre": 1}
    assert settings["queue"] == "bigmem"
    assert settings["cores"] == 8
    assert settings["licences"] == {"spectre": 1}
