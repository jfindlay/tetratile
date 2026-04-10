The Mathematical Foundations of Tetratile
==========================================

.. contents:: Contents
   :depth: 2
   :local:

Tetratile is a polyomino tessellation game whose implementation is
*transparently mathematical by design*.  Every significant type and
operation maps directly to a named mathematical concept: the game board
is a finite sublattice, the pieces are elements of a free abelian group
of lattice-cell sets, every valid player or agent move is an element of
the group :math:`\mathbb{Z}^2 \rtimes C_4`, and the game as a whole is
a driven cellular automaton on the integer lattice :math:`\mathbb{Z}^2`.

This document is the authoritative mathematical reference for the
codebase.  All descriptions refer to the post-refactor target state of
the code (see ``AGENTS.md`` for the design-principles summary and the
implementation plan).


The Integer Lattice :math:`\mathbb{Z}^2`
-----------------------------------------

The game board is embedded in the two-dimensional integer lattice
:math:`\mathbb{Z}^2`.  We use **y-up Cartesian orientation** throughout:
the positive :math:`y`-axis points upward, matching the standard
mathematical convention rather than the screen convention (where
:math:`y` increases downward).

A **unit cell** (called a :class:`Square` in the code) at lattice
position :math:`(x, y) \in \mathbb{Z}^2` is the open unit square

.. math::

   (x,\; x+1) \times (y,\; y+1) \;\subset\; \mathbb{R}^2.

The cell is *identified* by the lattice point :math:`(x, y)` at its
lower-left corner.  This is the conventional identification in
combinatorial geometry: a cell and its lower-left corner are the same
object for indexing purposes.

The **game domain** (the board) is the finite rectangular sublattice

.. math::

   \mathcal{B} = \{0, \ldots, w-1\} \times \{0, \ldots, h-1\}
   \;\subset\; \mathbb{Z}^2,

where :math:`w` (``width``) is the number of columns and :math:`h`
(``height``) is the number of rows.  In the code, :class:`Grid` models
:math:`\mathcal{B}` together with an occupancy function (see
:ref:`occupancy`).  The cell :math:`(0,0)` is the bottom-left; the cell
:math:`(w-1, h-1)` is the top-right.

The Tkinter rendering layer uses screen coordinates :math:`(x, h-1-y)`,
flipping the :math:`y`-axis.  This transform is encapsulated in
:meth:`Board._transform_coord` and is invisible to all game-logic code,
which always works in the Cartesian :math:`y`-up frame.

.. _polyominoes:

Polyominoes
-----------

An *n-omino* (**polyomino of ordinal** :math:`n`) is a connected,
finite subset :math:`S \subset \mathbb{Z}^2` of :math:`n` unit cells,
where connectivity is by shared edges (not corners).  The sequence of
standard polyominoes by ordinal is:

==========  ======  =====================
Ordinal     Name    Count (one-sided)
==========  ======  =====================
1           monomino    1
2           domino      1
3           tromino     2
4           tetromino   7
5           pentomino   18
==========  ======  =====================

This game uses the seven **one-sided tetrominoes**: Z, S, I (``l``), T,
O (``o``), L, J.  The count *seven* (rather than the five *free*
tetrominoes) arises because reflections are not valid game moves: a
reflected piece is a physically distinct object.  Specifically,
:math:`\text{S} \ncong \text{Z}` and :math:`\text{L} \ncong \text{J}`
under pure rotation; identifying them would require a reflection, which
is not an element of the valid transform group (see
:ref:`transform-group`).

In the code, a :class:`Polyomino` stores:

* ``squares: frozenset[Square]`` — the set of cells (a ``frozenset``
  captures the set semantics: no ordering, no duplicates, immutable).
* ``origin: tuple[Decimal, Decimal]`` — the rotation pivot, stored with
  exact :class:`~decimal.Decimal` arithmetic to support half-integer
  centres (see :ref:`rotation-formula`).
* ``name``, ``colors`` — metadata.

The *ordinal* :math:`n = |\text{squares}|` is a computed property:
``piece.ordinal == 4`` is necessary and sufficient for the piece to be a
tetromino.

.. _half-integer-origin:

Half-Integer Origins
~~~~~~~~~~~~~~~~~~~~

The rotation pivot :math:`(o_x, o_y)` should be the geometric centre of
symmetry of the piece.  For most tetrominoes (T, L, J) this centre is an
integer lattice point and ``origin = (D(0), D(0))`` in local
coordinates.

For Z, S, I, and O, the geometric centre of symmetry is a *half-integer*
point — it falls between lattice nodes.  For example, the Z tetromino in
its spawn orientation

.. math::

   \{(-2,-1),\; (-1,-1),\; (-1,-2),\; (0,-2)\}

(after the standard half-integer coordinate shift) has centroid
:math:`(-\tfrac{3}{2}, -\tfrac{3}{2})`.  The correct rotation pivot is
at :math:`(-\tfrac{1}{2}, -\tfrac{1}{2})`, which lies between the four
central cells.

By storing ``origin = (D('-0.5'), D('-0.5'))`` and using
:class:`~decimal.Decimal` arithmetic in the rotation formula, the pivot
is preserved exactly through all four rotation states.  This gives
*exact* rotation with no accumulated integer-truncation drift, and
eliminates the need for rotation-correcting kicks for these pieces in
free space.

.. _transform-group:

The Transform Group :math:`\mathbb{Z}^2 \rtimes C_4`
-----------------------------------------------------

The set of valid piece moves forms the **semidirect product**

.. math::

   G = \mathbb{Z}^2 \rtimes C_4,

where:

* :math:`\mathbb{Z}^2` is the free abelian group of integer translations,
  generated by :math:`e_x = (1,0)` and :math:`e_y = (0,1)`.
* :math:`C_4 \cong \mathbb{Z}/4\mathbb{Z}` is the cyclic group of order
  4, generated by the clockwise quarter-turn :math:`r`.
* The semidirect product structure: :math:`C_4` acts on :math:`\mathbb{Z}^2`
  by rotation.  The CW generator acts as

  .. math::

     r \cdot (a, b) = (b, -a),

  the standard CW quarter-turn in Cartesian :math:`y`-up coordinates
  (verified: :math:`r \cdot (1,0) = (0,-1)`,
  :math:`r \cdot (0,1) = (1,0)`, :math:`r^4 = \mathrm{id}`).

An element of :math:`G` is a pair :math:`(t, r^k)` with
:math:`t \in \mathbb{Z}^2` and :math:`k \in \{0,1,2,3\}`.  Group
multiplication is

.. math::

   (t_1, r^{k_1}) \circ (t_2, r^{k_2})
   = \bigl(t_1 + r^{k_1}(t_2),\; r^{k_1+k_2 \bmod 4}\bigr).

In a single game step, a player applies one *atomic generator* of
:math:`G` to the active piece:

* :math:`e_x = (1,0)`: one step right.
* :math:`-e_x = (-1,0)`: one step left.
* :math:`-e_y = (0,-1)`: one step down (gravity direction; negative
  because gravity falls in the :math:`-y` direction).
* :math:`r`: one CW quarter-turn.
* :math:`r^{-1} = r^3`: one CCW quarter-turn.

The code calls these *eigentransformations* and encodes them as the type
alias ``type EigenTransformation = Translation | Rotation``, where
:class:`Translation` ``(dx, dy)`` represents any :math:`\mathbb{Z}^2`
vector and :class:`Rotation` ``(steps)`` represents any element of
:math:`C_4`.

**Why not** :math:`D_4`?  The dihedral group :math:`D_4` (order 8)
includes four reflections in addition to the four rotations of :math:`C_4`.
Reflections are excluded here because they would produce a physically
distinct piece: S is not a rotation of Z, and L is not a rotation of J.
The game therefore implements the *one-sided* (7-piece) rather than *free*
(5-piece) tetromino set.

Eigentransformations vs. Derived Operations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

An *eigentransformation* is an atomic generator of :math:`G` — an
irreducible group element from which all other valid moves are composed.
The operations ``move_left_max``, ``move_right_max``, and ``hard_drop``
are *not* eigentransformations: they are derived operations that compute
the supremum of the piece's orbit under repeated generator application
(see :ref:`extremal-translations`).  They belong in the
:class:`InputHandler` layer, not in the mathematical transform layer.

The term **multiple** (not *magnitude*) is used for the integral scale
factor on a generator.  This terminology emphasises that the scale must
be an integer: the lattice :math:`\mathbb{Z}^2` admits only integer
displacements.  Real-valued scaling (*magnitude* in the continuous sense)
is not a valid operation on :math:`\mathbb{Z}^2`.

.. _rotation-formula:

The Rotation Formula
--------------------

The CW quarter-turn :math:`r` in :math:`y`-up Cartesian coordinates maps

.. math::

   r:\; (dx, dy) \;\longmapsto\; (dy, -dx).

Verification: the four generators rotate in order
:math:`e_x \to -e_y \to -e_x \to e_y \to e_x`, tracing a CW cycle. ✓

For a piece with rotation pivot :math:`(o_x, o_y)` and squares
:math:`\{(x_i, y_i)\}`, applying :math:`r` (CW) maps each cell to

.. math::

   x_i' = (y_i - o_y) + o_x, \qquad y_i' = -(x_i - o_x) + o_y.

For :math:`k` applications of :math:`r`, the rotation tensors are

.. math::

   R_0 = I,\quad
   R_1 = \begin{pmatrix}0&1\\-1&0\end{pmatrix},\quad
   R_2 = -I,\quad
   R_3 = \begin{pmatrix}0&-1\\1&0\end{pmatrix}.

The CCW quarter-turn :math:`r^{-1} = r^3` maps
:math:`(dx,dy) \mapsto (-dy, dx)`, corresponding to ``Rotation(steps=-1)``.

In the code, the formula is implemented as::

    x_new = int(r.steps * (y - o_y) + o_x)
    y_new = int(-r.steps * (x - o_x) + o_y)

where ``r.steps = +1`` is CW and ``r.steps = -1`` is CCW.  The
:func:`int` truncation is exact for pieces with integer origins (T, L, J)
and exact for pieces with half-integer origins (Z, S, I, O) because
:class:`~decimal.Decimal` arithmetic preserves the half-integer values
through all four rotation states without rounding.

.. _boundary-kicks:

Boundary Kicks: Covariant Rotation
-----------------------------------

When the freely-rotated piece :math:`P' = r(P)` violates the grid
boundary :math:`\mathcal{B}`, a corrective translation (a *kick*) is
needed.  Rather than precomputing kick tables for each piece and state
pair (the SRS approach), the functional approach derives the kick
algebraically from the rotated piece's bounding box.

Let :math:`P' = \{(x_i', y_i')\}`.  Define the boundary corrections:

.. math::

   \delta_x = \begin{cases}
     -\min_i x_i' & \text{if } \min_i x_i' < 0 \\
     (w-1) - \max_i x_i' & \text{if } \max_i x_i' \geq w \\
     0 & \text{otherwise}
   \end{cases},
   \qquad
   \delta_y = \begin{cases}
     -\min_i y_i' & \text{if } \min_i y_i' < 0 \\
     0 & \text{otherwise}
   \end{cases}.

Then the ``_boundary_kicks`` generator yields candidate corrections in
priority order:

1. :math:`(0, 0)` — no correction (try in place first)
2. :math:`(\delta_x, 0)` — horizontal correction only
3. :math:`(0, \delta_y)` — vertical correction only
4. :math:`(\delta_x, \delta_y)` — both corrections (corner case)

The first candidate :math:`(\delta_x', \delta_y')` for which
:math:`P' + (\delta_x', \delta_y')` satisfies the placement validity
predicate (in-bounds and not overlapping :math:`\mathcal{G}`) is
accepted.  If no candidate is valid (typically: the piece would embed in
the locked stack), rotation fails and the piece is unchanged.

**Covariant derivative analogy.**  In differential geometry, the covariant
derivative of a vector field :math:`V` along a curve corrects the ordinary
derivative by a *connection term* :math:`\Gamma` that accounts for the
curvature of the ambient space:
:math:`\nabla_u V = \partial_u V + \Gamma(u, V)`.

The boundary kick plays the same role here: the *free rotation*
:math:`r(P)` is the "ordinary derivative" — the rotation ignoring the
bounded domain.  The kick :math:`(\delta_x, \delta_y)` is the
"connection term" that corrects for the local constraints of the finite
board :math:`\mathcal{B}`, yielding a domain-valid result.  The complete
operation ``covariant_rotate(P, r, G)`` = free rotation + boundary
correction is the *covariant rotation* in this analogy.

This approach is preferable to precomputed tables because:

* It is *algebraically derived* from the geometry, not empirically
  tabulated.
* It generalises naturally to :math:`N` dimensions (see
  :ref:`n-dimensional`).
* It is transparent: the correction is computed from first principles
  and is immediately understandable.

.. _occupancy:

The Board as an Occupancy Map
------------------------------

The **locked-piece game state** is modelled as a partial function

.. math::

   \mathcal{G}:\; \mathcal{B} \;\rightharpoonup\; \text{PieceName},

where :math:`\text{PieceName} \in \{\text{Z}, \text{S}, \text{l},
\text{T}, \text{o}, \text{L}, \text{J}\}`.  In Python this is encoded
as ``dict[Square, str]``:

* **Presence** of a key :math:`s` in the dict means cell :math:`s` is
  occupied by a locked piece.
* **Absence** means the cell is empty.

This is the mathematically natural representation: the board is a
*finite set of coloured lattice points*, not a matrix with empty entries.

The **active piece** :math:`P` (the currently falling piece) is tracked
separately in ``TetraTile.piece`` and is *never written to*
:math:`\mathcal{G}`.  This eliminates the need for an ``is_active`` flag
in the grid.  The locked occupancy :math:`\mathcal{G}` contains only
committed (locked) piece cells.

**Placement validity** for a candidate piece :math:`P` in state
:math:`\mathcal{G}` is the predicate

.. math::

   \text{valid}(\mathcal{G}, P)
   \;\iff\;
   \forall s \in P:\; s \in \mathcal{B}
   \;\wedge\; s \notin \operatorname{dom}(\mathcal{G}).

This is implemented by :meth:`Grid.check`.

The :class:`Board` class is the Tkinter rendering layer.  It owns
separate render maps (``dict[Square, canvas_id]`` and
``dict[Square, Colors]``) but does not hold the occupancy
:math:`\mathcal{G}`; only :class:`TetraTile` (the game controller)
writes to and reads from :math:`\mathcal{G}`.

Row-Major Observation
~~~~~~~~~~~~~~~~~~~~~

The :class:`GameObservation` dataclass exposes the board state to
observers and agents as a row-major 2D list: ``board[y][x]``, where
``y = 0`` is the bottom row and ``y = height - 1`` is the top row.  This
matches the standard convention for numpy arrays and ML agent
consumption.  Note the transposition relative to Tkinter canvas
coordinates.

.. _row-removal:

Row Removal
-----------

A **full row** at height :math:`y` is identified when every cell in that
row is locked:

.. math::

   \forall x \in \{0, \ldots, w-1\}:\; (x, y) \in \operatorname{dom}(\mathcal{G}).

A row :math:`R_y = \{(x, y) : 0 \leq x < w\}` is a degenerate
polyomino — a :math:`1 \times w` horizontal strip of ordinal :math:`w`.
Row removal is the algebraic subtraction of this sub-polyomino from the
occupancy map, followed by a downward shift of the overburden.

When full rows :math:`y_1 < y_2 < \cdots < y_k` are identified
simultaneously, the updated occupancy is

.. math::

   \mathcal{G}' = \bigl\{
     \bigl(x,\; y - |\{j : y_j < y\}|\bigr) \mapsto v
     \;\big|\;
     (x, y) \mapsto v \in \mathcal{G},\; y \notin \{y_1, \ldots, y_k\}
   \bigr\}.

In words: each locked cell :math:`(x, y)` above the removed rows shifts
downward by the count of full rows strictly below it.

In group-theoretic terms, this is a conditional application of the
translation :math:`-j \cdot e_y` (downward by :math:`j` units) to the
sub-polyomino occupying the rows above the :math:`j`-th removed row.

The implementation in :meth:`Grid.remove_and_shift` iterates over
remaining locked cells in bottom-to-top order and moves each to its new
position, deleting the old canvas rendering and drawing a new one.

.. _extremal-translations:

Extremal Translations: Orbit Suprema
--------------------------------------

The operations ``move_left_max``, ``move_right_max``, and ``hard_drop``
compute the *supremum of the piece's orbit* under a unit generator:

.. math::

   \text{move\_left\_max}(P, \mathcal{G})
   &= \sup\{k \geq 0 : P - k e_x
   \;\text{is valid in}\; \mathcal{G}\}, \\
   \text{move\_right\_max}(P, \mathcal{G})
   &= \sup\{k \geq 0 : P + k e_x
   \;\text{is valid in}\; \mathcal{G}\}, \\
   \text{hard\_drop}(P, \mathcal{G})
   &= \sup\{k \geq 0 : P - k e_y
   \;\text{is valid in}\; \mathcal{G}\}.

The supremum is well-defined and finite because :math:`\mathcal{B}` is
finite.  It cannot be computed in closed form in general: the obstruction
depends jointly on the piece shape :math:`P` and the current stack
:math:`\mathcal{G}`, which varies during play.  (If the board were
empty, the supremum would equal the distance from the piece's minimum
coordinate to the nearest wall — a trivial closed form.  With a stack,
each row of the piece may be blocked at a different column, making a
closed form impossible without a full per-row scan.)

The **inductive implementation** is the unique correct approach:

.. code-block:: python

   while game.move_piece(Translation(-1, 0)):  # move_left_max
       pass

Each iteration applies the unit generator :math:`-e_x` and tests
validity.  The loop terminates at the supremum — the last valid position
before the next step would be blocked by the grid boundary or the stack.

These operations are *not* eigentransformations (atomic generators of
:math:`G`); they are derived operations.  They belong in the
:class:`InputHandler` layer, not in the :class:`EigenTransformation`
type alias.

.. _cellular-automata:

Relationship to Cellular Automata
-----------------------------------

The polyomino game is not merely *analogous* to a cellular automaton — in
several places the correspondence is exact and formal.  This section
develops the connections systematically, from the definitional link through
polyomino connectivity, to the formal driven-CA model, to empirical results
on statistical physics and computational complexity.

Polyomino Connectivity and the Von Neumann Neighbourhood
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A cellular automaton on :math:`\mathbb{Z}^2` is characterised by its
**neighbourhood**: the finite set :math:`\mathcal{N} \subset \mathbb{Z}^2`
of relative positions that influence a cell's next state.  The two canonical
choices are:

* **Von Neumann neighbourhood** :math:`\mathcal{N}_4 = \{(0,0), (\pm 1, 0),
  (0, \pm 1)\}` — the four edge-adjacent cells plus the cell itself.
* **Moore neighbourhood** :math:`\mathcal{N}_8` — all eight cells within
  Chebyshev distance 1.

The definition of a polyomino specifies connectivity by **shared edges**
(not corners).  Two cells are polyomino-connected iff they are
:math:`\mathcal{N}_4`-adjacent.  The von Neumann neighbourhood is therefore
not an incidental feature of the polyomino concept — it *is* the founding
topological structure.  A connected subset of :math:`\mathbb{Z}^2` using
Moore-neighbourhood connectivity would define a different family
(variously called *polyplets* or *polykings*), with different count
sequences.

This means that every result in polyomino theory implicitly assumes the von
Neumann neighbourhood, and every von-Neumann CA operates on the same
topological substrate as this game.

The Game as a Driven Cellular Automaton
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A standard (autonomous) CA is a tuple :math:`(\mathbb{Z}^d, Q, \mathcal{N},
\varphi)` where :math:`Q` is a finite alphabet, :math:`\mathcal{N}` is a
neighbourhood, and :math:`\varphi: Q^{\mathcal{N}} \to Q` is a local
transition rule, applied to every cell simultaneously.  The global map
:math:`\Phi: Q^{\mathbb{Z}^d} \to Q^{\mathbb{Z}^d}` is defined by
:math:`\Phi(C)(x) = \varphi\bigl(C\big|_{x + \mathcal{N}}\bigr)`.

The polyomino game is an instance of a **driven CA** (also called an *input
CA* or *nonautonomous CA*): a CA paired with an external input stream
:math:`\sigma: \mathbb{N} \to Q^{\mathbb{Z}^2}` that modifies the
configuration at each step.  The full update at tick :math:`t` is

.. math::

   C_{t+1}
   = \Phi_{\text{row-remove}}\bigl(
       \Phi_{\text{lock}}\bigl(
         C_t \,\oplus\, \sigma_t
       \bigr)
     \bigr),

where:

* :math:`\sigma_t` is the player's or agent's move — the
  :class:`EigenTransformation` applied to the active piece.  The player is
  literally the **external drive** of the CA.
* :math:`\oplus` denotes the injection of the moved piece into the
  configuration.
* :math:`\Phi_{\text{lock}}` transitions cells belonging to the active piece
  from *active* to *locked* state when the piece can no longer descend.
* :math:`\Phi_{\text{row-remove}}` applies the row-removal rule (see below).

The state alphabet is :math:`Q = \{\text{empty}, \text{Z}, \text{S},
\text{l}, \text{T}, \text{o}, \text{L}, \text{J}\}` — eight elements.

The code expresses this structure directly:

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - CA concept
     - Code location
   * - Configuration :math:`C_t`
     - :attr:`.GameObservation.board` — row-major ``board[y][x]``, alphabet :math:`Q`
   * - Global transition step
     - :meth:`.TetraTile.iterate` — one gravity + lock + row-remove cycle
   * - Row-removal rule :math:`\Phi_{\text{row-remove}}`
     - :meth:`.Grid.remove_and_shift` (or :meth:`.Board.remove_full_rows`)
   * - External drive :math:`\sigma_t`
     - :class:`.InputHandler` — player or agent sends the eigentransformation
   * - CA oracle / controller
     - :meth:`.Agent.select_action` — pure function :math:`C_t \to \text{Action}`
   * - Random drive (stochastic baseline)
     - :class:`.RandomAgent` — uniform random :math:`\sigma_t`; equivalent to the *random Tetris* model

Row Removal as a Threshold Totalistic Rule
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A **totalistic CA** is one where the next state of a cell depends only on
the *count* (not the arrangement) of neighbours in each state.  The row
removal rule is a totalistic threshold rule at the **row** scale:

.. math::

   \text{row } y \text{ fires}
   \;\iff\;
   \sum_{x=0}^{w-1}
   \mathbf{1}\bigl[\mathcal{G}(x, y) \neq \emptyset\bigr] = w.

When a row fires, it is erased and all locked cells above it shift down.
This is structurally identical to **bootstrap percolation** threshold rules
and to the firing condition in the Abelian Sandpile Model (see below): a
site fires when its local density reaches a critical value.

The key deviation from standard CA: row fullness is a **non-local**
condition (range :math:`w/2`, not a bounded neighbourhood).  A standard CA
with fixed finite neighbourhood :math:`\mathcal{N}_R` cannot detect row
fullness in a single step.  However, it *can* be computed purely locally in
:math:`O(w)` CA steps by propagating an accumulated count left-to-right
along the row — a carry-propagation CA.  The game's row removal is the
instantaneous, non-local equivalent of this :math:`O(w)`-step local
computation.

In the code, :meth:`.Grid.remove_and_shift` implements the instantaneous
version: it computes full rows in one pass and shifts remaining cells
down in a second pass, achieving the same result as the iterated local CA
in two linear scans rather than :math:`O(w)` CA steps.

Analogies with Conway's Game of Life
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Conway's Game of Life classifies every pattern into one of three types.
The polyomino game's dynamics map precisely onto this taxonomy:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Life concept
     - Polyomino game analog
   * - **Still life** — a configuration that is a fixed point of :math:`\Phi`
     - A locked piece in :math:`\mathcal{G}`.  Once written, it never changes
       (absent row removal).  Every locked cell is part of a still life.
   * - **Oscillator** — a configuration with period :math:`k > 0`
     - The rotating active piece.  Each application of :math:`r` returns the
       piece to the same shape after :math:`k = 4` steps (the :math:`C_4`
       orbit).  The piece is a period-4 oscillator in the extended
       configuration.
   * - **Glider** — a configuration that translates periodically
     - The falling piece.  Under gravity alone (no player input) the piece
       translates by :math:`-e_y` every tick, repeating its shape unchanged.
       It is a period-1 glider moving at speed 1 cell/tick.

The **lock event** is the game's analog of a **glider collision**: the
falling glider encounters the still-life layer (the stack), is absorbed into
it, and may trigger a **row-removal annihilation event** that erases part of
the still-life layer.  In Life, glider guns can fire gliders at eaters; in
the game, a well-aimed piece can trigger a cascade of row clearances — the
avalanche described in the next section.

The analogy also highlights what the game *lacks* by comparison with Life:
there is no spontaneous pattern evolution in :math:`\mathcal{G}` between
lock events.  The locked cells are frozen; the only dynamics come from the
externally driven glider.  The game is *not* autonomous in the CA sense.

Sandpile Models and Self-Organised Criticality
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The **Abelian Sandpile Model** (Bak, Tang & Wiesenfeld 1987; Dhar 1990) is
a CA on :math:`\mathbb{Z}^2` in which each cell :math:`(x, y)` holds an
integer grain count :math:`h(x, y)`.  When :math:`h(x, y) \geq 4`, the
cell **topples**: it loses 4 grains and each of its four von Neumann
neighbours gains 1.  Grains may cascade through the lattice in an
*avalanche*.  Bak, Tang and Wiesenfeld showed that the stationary state
under random grain addition exhibits **self-organised criticality** (SOC):
avalanche sizes and durations follow power laws with no external tuning
parameter.

The polyomino game, in the *column-height representation*, is a modified
sandpile.  Let :math:`h(x)` be the height of the highest occupied cell in
column :math:`x`.  Pieces land on top of columns (grains fall on the sand
surface).  When the minimum height across a row reaches the row index —
equivalently, when row :math:`y` is completely filled — that row fires
(is removed) and the overburden falls by one unit.  This is a **non-local
sandpile** where the firing condition is row-completion rather than per-cell
grain overflow.

Aste and Sherrington (1999) showed that **random Tetris** — pieces selected
and placed uniformly at random — develops a *glassy* low-temperature phase:
long quiescent periods during which the stack grows, punctuated by sudden
cascades of row clearances.  The avalanche sizes (number of rows cleared in
a single cascade) follow a power law, the signature of SOC.  In their model
the game board is a driven, dissipative, threshold CA, and the emergence of
criticality requires no tuning — it arises from the geometry of the pieces
and the threshold row-removal rule alone.

For the agent-based analysis in this codebase, the random Tetris result is
the natural **baseline**: the :class:`.RandomAgent` produces exactly the
random-drive Aste–Sherrington model.  An agent that scores significantly
above the random baseline is navigating the SOC landscape non-trivially.

Tile Self-Assembly
~~~~~~~~~~~~~~~~~~~

Winfree (1998) introduced the **abstract Tile Assembly Model** (aTAM) in
the context of DNA computing.  Square tiles with coloured edges attach to a
growing assembly when the edge colours of adjacent tiles match and the total
binding strength exceeds a threshold :math:`\tau`.  The assembled structure
is a configuration in :math:`\mathbb{Z}^2` — exactly an occupancy map
:math:`\mathcal{G}`.  For :math:`\tau \geq 2`, the aTAM is Turing complete.

The locked occupancy :math:`\mathcal{G}` is a tile assembly configuration.
The polyomino game is a **controlled tile assembly** where:

* The player selects the next tile (tetromino) from the seven one-sided
  types.
* Gravity determines the attachment height (the tile falls until it rests
  on the existing assembly).
* Row removal is a **disassembly** rule unique to the game — tiles that
  complete a full row are removed, which has no direct aTAM analog.

The aTAM connection suggests that the locked stack can, in principle,
encode arbitrary computations via careful piece placement — consistent with
the computational hardness results described below.

Computational Hardness
~~~~~~~~~~~~~~~~~~~~~~~

Breukelaar, Demaine et al. (2004) proved that several natural decision
problems about Tetris are **NP-complete**:

* Given an initial board :math:`\mathcal{G}_0` and a sequence of :math:`k`
  incoming pieces, can the player survive (avoid a game-over)?
* Can all rows be cleared?
* Can a given target configuration be reached?

The proofs construct gadgets from piece sequences that implement logical
gates, wires, and memory — essentially building a circuit inside the game
board.  This is the Tetris analog of the classical CA result that Conway's
Life is Turing complete: in both cases, carefully engineered configurations
implement universal computation.

The NP-hardness tells us something precise about the :class:`.Agent`
interface: since computing the optimal action sequence is NP-hard, no
polynomial-time :class:`.Agent.select_action` implementation can be optimal
in the worst case (unless P = NP).  The :class:`.RandomAgent` baseline and
any trained agent are therefore operating in the space between random and
optimal, which is computationally intractable to bridge exactly.

Whether the **autonomous row-removal dynamics** (ignoring player input)
constitute a computationally universal CA is an open question — but the
NP-hardness of the strategy problem strongly suggests that the configuration
space contains significant computational structure.

.. _architecture:

The Architecture: Input / Output / State
-----------------------------------------

The game's algebraic state — the locked occupancy :math:`\mathcal{G}`,
the active piece :math:`P`, and the game-lifecycle state — is
encapsulated in :class:`TetraTile`.  Two orthogonal interfaces cross
this boundary.

**Input (** :class:`InputHandler` **)**

A human player or AI agent sends an :class:`EigenTransformation` to
:meth:`TetraTile.move_piece`.  The method:

1. Guards against non-running game state (returns ``False`` immediately).
2. Applies the transform to produce a candidate piece.
3. Checks validity via :meth:`Grid.check`.
4. On success: updates ``TetraTile.piece`` and redraws the board.
5. Logs the event.

:class:`HumanInputHandler` and :class:`AgentInputHandler` are coequal
named subclasses of :class:`InputHandler`.  They contain no overriding
logic; the subclass exists only as a named entry point for
``isinstance`` discrimination.  Swapping the handler (human ↔ agent)
transparently changes who controls the game without touching any other
code path.

**Output (** :class:`OutputHandler` **)**

After each gravity tick, :meth:`TetraTile._notify_observers` calls
:meth:`OutputHandler.on_observation` on all registered handlers, passing
a :class:`GameObservation` — a read-only snapshot of the game state.
Multiple handlers may be registered simultaneously: a human watching an
agent game can register a :class:`PrintObserver` alongside the running
game without any special mode.

**Agent (** :class:`Agent` **)**

An :class:`Agent` is a pure decision function:

.. math::

   f:\; \text{GameObservation} \;\longrightarrow\; \text{Action}.

It has no reference to the game object and produces no side effects.
The :class:`AgentRunner` owns both the game and the agent, wiring the
agent's output (:class:`Action`) to the game's input via an
:class:`AgentInputHandler`.

The :class:`Action` alphabet enumerates all valid game operations; each
value equals the corresponding :class:`InputHandler` method name,
enabling ``getattr(handler, action)()`` dispatch.

.. _n-dimensional:

N-Dimensional Generalization
-----------------------------

The design anticipates generalisation to :math:`N`-dimensional
polyhypercube games.

**Domain**
   The lattice :math:`\mathbb{Z}^N`; the domain is the :math:`N`-dimensional
   box :math:`\prod_{i=1}^N \{0, \ldots, w_i - 1\}`.  A cell is a
   unit :math:`N`-hypercube identified by its minimum-corner in
   :math:`\mathbb{Z}^N`.

**Pieces**
   :math:`N`-dimensional polyhypercubes: connected finite subsets of
   :math:`\mathbb{Z}^N`.  A ``Square`` becomes an :math:`N`-tuple.

**Translation group**
   :math:`\mathbb{Z}^N`, generated by the :math:`N` unit vectors
   :math:`e_1, \ldots, e_N`.  :class:`Translation` becomes an
   :math:`N`-vector ``tuple[int, ...]``.

**Rotation group**
   The proper rotation subgroup :math:`B_N^+` of the **hyperoctahedral
   group** :math:`B_N` (the group of signed permutation matrices, order
   :math:`2^N \cdot N!`).  The proper rotation subgroup has order
   :math:`2^{N-1} \cdot N!`.

   In :math:`N` dimensions, each rotation acts in a *coordinate plane*
   — a 2D subspace spanned by two basis vectors :math:`e_i, e_j`.
   There are :math:`\binom{N}{2}` distinct coordinate planes.
   :class:`Rotation` gains a field ``plane: tuple[int, int]`` selecting
   the rotation plane.

   For :math:`N = 2`: :math:`B_2^+ = C_4` (order 4), the single plane
   is :math:`(0, 1)`.  For :math:`N = 3`: :math:`|B_3^+| = 24`, with
   planes :math:`(0,1), (0,2), (1,2)`.

**Rotation formula**
   For rotation in coordinate plane :math:`(i, j)` by ``steps``
   quarter-turns:

   .. math::

      x_i' = \text{steps} \cdot (x_j - o_j) + o_i, \qquad
      x_j' = -\text{steps} \cdot (x_i - o_i) + o_j, \qquad
      x_k' = x_k \;\text{ for } k \notin \{i,j\}.

   The current 2D formula is this expression with :math:`i=0, j=1`
   hardcoded.  Generalisation requires adding a ``plane`` parameter.

**Gravity**
   One designated axis (conventionally axis :math:`N-1`, i.e.
   :math:`y` in 2D) is the gravity axis.  Each tick applies
   :math:`\text{Translation}(\ldots, -1)` along that axis.

**Full hyperslab**
   The generalisation of a full row is an :math:`(N-1)`-dimensional
   cross-section at a fixed value of the gravity axis coordinate.

**Boundary kicks**
   The ``_boundary_kicks`` generator extends naturally: for each axis
   :math:`k`, compute :math:`\delta_k` from boundary violations along
   that axis.  Yield all non-empty subsets of
   :math:`\{\delta_k : k = 1,\ldots,N\}` as correction vectors, in
   order of cardinality (single-axis corrections before multi-axis
   corner corrections).

**On Clifford Algebra**
   The Clifford algebra :math:`Cl(\mathbb{R}^N)` provides an elegant
   formulation of :math:`N`-dimensional rotations via *rotors*
   :math:`R = e^{-\theta B/2}`, where :math:`B` is a unit bivector in
   :math:`\bigwedge^2 \mathbb{R}^N`.  The rotor formulation has two
   attractive properties: it avoids gimbal lock and generalises
   uniformly to any :math:`N`.

   However, this game operates on :math:`\mathbb{Z}^N` (a discrete
   lattice), not :math:`\mathbb{R}^N` (the continuous plane).  The
   discrete constraint introduces two difficulties for GA:

   1. Rotors live in a continuous Lie group
      (:math:`\mathrm{Spin}(N) \subset Cl(\mathbb{R}^N)^+`), not a
      discrete one.  The game's rotations are quarter-turns in
      :math:`B_N^+`, a finite discrete group.
   2. Translations are not native to :math:`Cl(N)`.  Encoding them
      requires Projective Geometric Algebra (PGA) or Conformal
      Geometric Algebra (CGA), which embed the game in a space of
      :math:`N+1` or :math:`N+2` dimensions and add significant
      conceptual overhead.

   The group :math:`\mathbb{Z}^N \rtimes B_N^+` is therefore preferred
   as the direct algebraic structure.  GA would become relevant for a
   continuous-physics extension of the game (smooth animations, rigid-body
   dynamics, or particle effects), where the rotor formulation would be
   the natural tool.

.. _design-principles:

Design Principles
-----------------

The codebase embodies the following mathematical design principles.

1. **Transparent mathematical types.**
   Code types should make mathematical structure visible.
   ``Square(x, y)`` is clearer than ``[x, y]``; ``frozenset[Square]``
   captures set semantics; ``Translation(dx, dy)`` names a group element.
   The goal is that reading the code gives direct insight into the
   mathematics.

2. **Value semantics.**
   :meth:`Polyomino.translate` and :meth:`Polyomino.rotate` return new
   :class:`Polyomino` instances (or ``None`` if blocked); they do not
   mutate.  This reflects the group action: applying a group element to
   a piece yields a new state, not a modified version of the original.
   Value semantics also eliminates the need for ``copy.deepcopy``.

3. **Separation of state and rendering.**
   :class:`Grid` (the occupancy map :math:`\mathcal{G}`) is pure game
   state with no Tkinter dependency.  :class:`Board` (the Tkinter
   canvas) is a pure rendering surface with no game logic.  The active
   piece is never written to :math:`\mathcal{G}` while in play.

4. **``multiple`` is integral.**
   The scale factor on a generator is an integer — the word *multiple*
   is used precisely to emphasise this constraint.  Real-valued scaling
   (*magnitude* in the continuous sense) is not a valid operation on
   :math:`\mathbb{Z}^N`.

5. **Derived operations are not generators.**
   ``move_left_max``, ``move_right_max``, and ``hard_drop`` are orbit
   suprema — derived from generators by induction.  They live in
   :class:`InputHandler`, not in the :class:`EigenTransformation` type
   alias.

6. **Functional, algebraically-derived kicks.**
   Boundary kicks are computed from the rotated piece's bounding box,
   not from precomputed state-pair tables.  The derivation is explicit,
   general, and extensible.

7. **Half-integer origins for exact arithmetic.**
   Pieces whose geometric centre of symmetry is a half-integer point
   (Z, S, I, O) use :class:`~decimal.Decimal` pivot coordinates.  This
   preserves exact rotation across all four states without
   integer-truncation drift.

References
----------

* Aste, T. & Sherrington, D. (1999). Glassy behavior in a model for
  the game of Tetris. *Journal of Physics A: Mathematical and General*,
  32(42), 7049–7056.  (Self-organised criticality and the glassy phase
  in random Tetris; baseline for the :class:`.RandomAgent` analysis.)
* Bak, P., Tang, C. & Wiesenfeld, K. (1987). Self-organized criticality:
  An explanation of 1/f noise. *Physical Review Letters*, 59(4), 381–384.
  (Foundational sandpile model and self-organised criticality.)
* Breukelaar, R., Demaine, E. D., Hohenberger, S., Hoogeboom, H. J.,
  Kosters, W. A. & Liben-Nowell, D. (2004). Tetris is hard, even to
  approximate. *International Journal of Computational Geometry and
  Applications*, 14(1–2), 41–68.  (NP-completeness of Tetris decision
  problems; implications for agent optimality.)
* Dhar, D. (1990). Self-organized critical state of sandpile automaton
  models. *Physical Review Letters*, 64(14), 1613–1616.  (The abelian
  sandpile model and its connection to threshold CA.)
* Golomb, S. W. (1994). *Polyominoes: Puzzles, Patterns, Problems, and
  Packings* (2nd ed.). Princeton University Press.
* Hestenes, D. & Sobczyk, G. (1984). *Clifford Algebra to Geometric
  Calculus*. Reidel.  (Referenced in discussion of GA; not used in the
  implementation.)
* Humphreys, J. E. (1990). *Reflection Groups and Coxeter Groups*.
  Cambridge University Press.  (For the hyperoctahedral group
  :math:`B_N`.)
* The Tetris guideline (SRS): https://tetris.wiki/SRS (consulted for
  historical context; the functional kick system in this game is an
  independent algebraic derivation).
* Winfree, E. (1998). Algorithmic self-assembly of DNA: Theoretical
  motivations and connections to experiments. *Journal of Biomolecular
  Structure and Dynamics*, 11, 263–270.  (Tile Assembly Model; the locked
  occupancy map as a tile assembly configuration.)
* Wolfram, S. (2002). *A New Kind of Science*. Wolfram Media.
  (Foundational reference on cellular automata, totalistic rules, and
  computational universality.)
