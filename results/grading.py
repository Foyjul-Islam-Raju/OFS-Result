"""Single source of truth for every percentage, grade and GPA calculation.

Nothing else in the project re-implements these rules.

Two presentation modes:

* Regular / class exams — marks, total, percentage, pass or fail. No letter
  grades, no GPA. This is the default.
* Semester examinations — the same, plus a credit-weighted GPA for the semester
  and a cumulative CGPA across the student's semesters.
"""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

TWO_PLACES = Decimal("0.01")

ABSENT_LABEL = "Absent"
FAIL_GRADE = "F"


@dataclass(frozen=True)
class GradeBand:
    minimum: Decimal  # inclusive lower bound of the percentage band
    letter: str
    point: Decimal


# Only used where letter grades or GPA are switched on. Ordered high to low.
GRADE_SCALE: tuple[GradeBand, ...] = (
    GradeBand(Decimal("80"), "A+", Decimal("5.00")),
    GradeBand(Decimal("70"), "A", Decimal("4.00")),
    GradeBand(Decimal("60"), "A-", Decimal("3.50")),
    GradeBand(Decimal("50"), "B", Decimal("3.00")),
    GradeBand(Decimal("40"), "C", Decimal("2.00")),
    GradeBand(Decimal("33"), "D", Decimal("1.00")),
    GradeBand(Decimal("0"), FAIL_GRADE, Decimal("0.00")),
)

MAX_GPA = GRADE_SCALE[0].point


def to_decimal(value) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def quantize(value) -> Decimal:
    return to_decimal(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def calculate_percentage(obtained, full_mark) -> Decimal:
    """(obtained / full) * 100, rounded to two decimal places."""
    full = to_decimal(full_mark)
    if full <= 0:
        return Decimal("0.00")
    return quantize(to_decimal(obtained) / full * Decimal("100"))


def _band_for(percentage) -> GradeBand:
    pct = to_decimal(percentage)
    for band in GRADE_SCALE:
        if pct >= band.minimum:
            return band
    return GRADE_SCALE[-1]


def grade_for_percentage(percentage) -> str:
    return _band_for(percentage).letter


def point_for_percentage(percentage) -> Decimal:
    return _band_for(percentage).point


def grade_for_marks(obtained, full_mark, is_absent: bool = False) -> str:
    """Grade always derives from percentage, never from the raw mark."""
    if is_absent:
        return ABSENT_LABEL
    return grade_for_percentage(calculate_percentage(obtained, full_mark))


def point_for_marks(obtained, full_mark, is_absent: bool = False) -> Decimal:
    if is_absent:
        return Decimal("0.00")
    return point_for_percentage(calculate_percentage(obtained, full_mark))


def is_subject_passed(
    obtained, full_mark, is_absent: bool, pass_percentage, pass_mark=None
) -> bool:
    """A subject passes on an explicit pass mark when one is configured,
    otherwise on the percentage-based passing criteria."""
    if is_absent:
        return False
    if pass_mark is not None:
        return to_decimal(obtained) >= to_decimal(pass_mark)
    return calculate_percentage(obtained, full_mark) >= to_decimal(pass_percentage)


def calculate_gpa(entries, any_subject_failed: bool = False, fail_zeroes: bool = True) -> Decimal:
    """Credit-weighted GPA.

    `entries` is an iterable of (grade_point, credit) pairs. Under the common
    rule a failed subject drops the whole GPA to zero; set `fail_zeroes` to
    False in Settings if your institution averages instead.
    """
    if any_subject_failed and fail_zeroes:
        return Decimal("0.00")
    total_credit = Decimal("0")
    weighted = Decimal("0")
    for point, credit in entries:
        credit = to_decimal(credit)
        if credit <= 0:
            continue
        total_credit += credit
        weighted += to_decimal(point) * credit
    if total_credit <= 0:
        return Decimal("0.00")
    return quantize(weighted / total_credit)
