"""Conversion of the board voltage to pH, with temperature compensation.

Model: the board voltage is linear in pH, V = V7 + S(T) * (pH - 7), where V7 is the
voltage at pH 7 (the isopotential point of a typical combination electrode, an
assumption) and S(T) is the slope, which scales with the absolute temperature
(Nernst). A calibration measures V7 and S at the calibration temperature.

Without a calibration the nominal mapping of the Atlas analog pH board is used:
3000 mV at pH 0 and 265 mV at pH 14 (datasheet end points), taken as valid at 25 °C.
"""
from dataclasses import dataclass

KELVIN = 273.15


@dataclass(frozen=True)
class Calibration:
    offset_mv: float  # board voltage at pH 7
    slope_mv_per_ph: float  # at temp_c, negative for the Atlas board
    temp_c: float
    id: int | None = None


NOMINAL = Calibration(
    offset_mv=3000 - 7 * (3000 - 265) / 14,
    slope_mv_per_ph=-(3000 - 265) / 14,
    temp_c=25.0,
)


def fit(points: list[tuple[float, float, float]]) -> Calibration:
    """Fit a calibration to (buffer pH, board mV, temperature in °C) points.

    Two points give an exact line, three or more a least-squares line. The slope is
    referred to the mean temperature of the points.
    """
    if len(points) < 2:
        raise ValueError("a calibration needs at least two buffer points")
    phs = [p[0] for p in points]
    mvs = [p[1] for p in points]
    mean_ph = sum(phs) / len(phs)
    mean_mv = sum(mvs) / len(mvs)
    spread = sum((ph - mean_ph) ** 2 for ph in phs)
    if spread == 0:
        raise ValueError("the buffer points must have different pH values")
    slope = sum((ph - mean_ph) * (mv - mean_mv) for ph, mv in zip(phs, mvs)) / spread
    offset = mean_mv + slope * (7 - mean_ph)
    temp_c = sum(p[2] for p in points) / len(points)
    return Calibration(offset_mv=offset, slope_mv_per_ph=slope, temp_c=temp_c)


def slope_at(cal: Calibration, temp_c: float | None) -> float:
    if temp_c is None:
        return cal.slope_mv_per_ph
    return cal.slope_mv_per_ph * (temp_c + KELVIN) / (cal.temp_c + KELVIN)


def to_ph(mv: float, temp_c: float | None, cal: Calibration = NOMINAL) -> float:
    return 7 + (mv - cal.offset_mv) / slope_at(cal, temp_c)


def slope_percent(cal: Calibration) -> float:
    """Slope relative to the nominal board slope at the same temperature.

    Only meaningful for the Atlas board, whose gain the nominal mapping reflects.
    """
    return 100 * cal.slope_mv_per_ph / slope_at(NOMINAL, cal.temp_c)
