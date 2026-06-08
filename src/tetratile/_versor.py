"""Integer-rotor versor sandwich for discrete plane-based geometric algebra.

Implements the lattice-exact CW quarter-turn rotation via the unnormalised
even-subalgebra rotor

    U = 1 + e₁₂  ∈  Cl(2,0,1)

whose reverse is Ũ = 1 − e₁₂.  For a planar vector v = x·e₁ + y·e₂:

    U v Ũ = 2·(y·e₁ − x·e₂)       (CW quarter-turn, steps = +1)

Dividing by |U|² = 2 gives the normalised result (y, −x), which is
identical to the classical coordinate formula.  The √2 that would appear
from normalising U individually cancels in the sandwich, making the
operation lattice-exact: integer inputs produce integer outputs, and
half-integer inputs (Decimal('-0.5')) produce half-integer outputs without
rounding.

See ``docs/mathematics.rst`` section ``.. _discrete-rotor:`` for the full
√2-cancellation proof and the half-integer-centre treatment.
"""

from decimal import Decimal as D


def rotate_point(
    x: int | D,
    y: int | D,
    steps: int,
    plane: tuple[int, int] = (0, 1),
) -> tuple[int | D, int | D]:
    """Apply ``steps`` CW quarter-turns to point ``(x, y)`` via the integer rotor.

    Computes the versor sandwich

        R v R̃ = (U v Ũ)^{steps} / |U|^{2·steps}

    with the unnormalised rotor ``U = 1 + e_{plane[0],plane[1]}``.  Each
    application maps ``(x, y) ↦ (y, −x)`` (CW) without any floating-point
    arithmetic: integer inputs produce integer outputs; :class:`~decimal.Decimal`
    half-integers produce half-integers.

    ``steps`` is taken modulo 4 so that any integer step count is valid.
    CCW rotation is ``steps = -1`` (equivalently ``steps = 3`` mod 4).

    Currently only ``plane = (0, 1)`` is supported, corresponding to the
    unique rotation plane in 2-D.  The parameter is exposed as the N-d
    readiness hook described in ``docs/mathematics.rst``; passing any other
    value raises :class:`NotImplementedError`.

    :param x: x-coordinate; integer or half-integer :class:`~decimal.Decimal`.
    :param y: y-coordinate; integer or half-integer :class:`~decimal.Decimal`.
    :param steps: Number of CW quarter-turns (positive = CW, negative = CCW).
    :param plane: Euclidean bivector index pair selecting the rotation plane.
    :returns: Rotated ``(x', y')`` with the same numeric type as the inputs.
    :raises NotImplementedError: If ``plane != (0, 1)``.
    """
    if plane != (0, 1):
        raise NotImplementedError(
            f"plane {plane!r} is not yet supported; only (0, 1) is implemented"
        )

    # Normalise to {0, 1, 2, 3}; negative steps map to CCW equivalents.
    n = steps % 4
    cx, cy = x, y
    for _ in range(n):
        # One application of U v Ũ / |U|²: (x, y) ↦ (y, −x)
        cx, cy = cy, -cx
    return cx, cy
