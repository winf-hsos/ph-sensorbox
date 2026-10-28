import pytest

from phbox_server.calibration import NOMINAL, Calibration, fit, slope_percent, to_ph


def test_nominal_mapping_hits_the_datasheet_end_points():
    assert to_ph(3000, 25, NOMINAL) == pytest.approx(0)
    assert to_ph(265, 25, NOMINAL) == pytest.approx(14)
    assert to_ph(NOMINAL.offset_mv, None, NOMINAL) == pytest.approx(7)


def test_two_points_give_an_exact_line():
    cal = fit([(4.01, 2200.0, 22.0), (7.0, 1620.0, 22.0)])
    assert to_ph(2200, 22, cal) == pytest.approx(4.01)
    assert to_ph(1620, 22, cal) == pytest.approx(7.0)
    assert cal.temp_c == 22.0


def test_three_points_recover_a_known_line():
    line = lambda ph: 1620 - 193.3 * (ph - 7)  # noqa: E731
    cal = fit([(ph, line(ph), 25.0) for ph in (4.01, 7.0, 10.01)])
    assert cal.slope_mv_per_ph == pytest.approx(-193.3)
    assert cal.offset_mv == pytest.approx(1620)


def test_three_points_average_out_a_disturbed_middle_point():
    cal = fit([(4.0, 2200.0, 25.0), (7.0, 1606.0, 25.0), (10.0, 1000.0, 25.0)])
    assert cal.slope_mv_per_ph == pytest.approx(-200)
    assert cal.offset_mv == pytest.approx(1602)  # mean of the three voltages


def test_slope_scales_with_absolute_temperature():
    cal = Calibration(offset_mv=1600, slope_mv_per_ph=-200, temp_c=25)
    # at 50 °C the slope is 323.15 / 298.15 times steeper, so the same voltage means less pH change
    assert to_ph(1400, 25, cal) == pytest.approx(8)
    assert to_ph(1400, 50, cal) == pytest.approx(7 + 1 * 298.15 / 323.15)
    assert to_ph(1600, 50, cal) == pytest.approx(7)


def test_nominal_slope_is_one_hundred_percent():
    assert slope_percent(NOMINAL) == pytest.approx(100)


@pytest.mark.parametrize("points", [[(7.0, 1600.0, 25.0)], [(7.0, 1600.0, 25.0), (7.0, 1610.0, 25.0)]])
def test_unusable_points_are_refused(points):
    with pytest.raises(ValueError):
        fit(points)
