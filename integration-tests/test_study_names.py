from studies import ota_pvt
from studies import ota_pvt_clean
from studies import ota_pvt_clean_nested
from studies import rc_corners


def test_runnable_studies_have_stable_operator_names() -> None:
    assert ota_pvt.pvt.name == "ota-pvt-study"
    assert ota_pvt_clean.pvt.name == "ota-pvt-clean"
    assert ota_pvt_clean_nested.pvt.name == "ota-pvt-clean-nested"
    assert (
        ota_pvt_clean_nested.corner_study.name
        == "ota-pvt-clean-nested-corners"
    )
    assert rc_corners.rc_corners.name == "rc-corners"
