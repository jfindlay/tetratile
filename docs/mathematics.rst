The Mathematical Foundations of Tetratile
==========================================

.. contents:: Contents
   :depth: 2
   :local:

Tetratile is a polyomino tessellation game whose implementation is
*transparently mathematical by design*.  Every significant type and
operation maps directly to a named mathematical concept: the game board
is a finite sublattice, the pieces are elements of a free abelian group
of lattice-cell sets, every valid player or agent move is a **discrete
versor** of a geometric algebra, and the game as a whole is a driven
cellular automaton on the integer lattice :math:`\mathbb{Z}^2`.

The organising algebraic framework is **discrete plane-based geometric
algebra** (discrete PGA): the even subalgebra of the projective Clifford
algebra :math:`Cl(2,0,1)`, restricted to the *lattice-stabilising*
versors.  This choice is **deliberate, not inherited**.  Geometric algebra
is the newer and more unifying foundation, and it is selected here for its
pedagogical and structural advantages: a single object — a **motor** —
encodes both translation and rotation; a single composition law (the
versor sandwich) governs every transform; and the construction generalises
uniformly to :math:`N` dimensions with no change of machinery.

The classical formulation as the semidirect product
:math:`\mathbb{Z}^2 \rtimes C_4`, together with the rotation *matrices*
:math:`R_k`, is **retained throughout as a bridge** — to the standard
group-theory literature and to the code's :class:`Translation` /
:class:`Rotation` type split — but it is no longer the conceptual home
base.  It is the same group, named in older language, and is
cross-referenced at every pillar so a reader fluent in either dialect can
follow.  Where the older matrix view reads more directly (most notably the
self-evident integer-exactness of a single quarter-turn), the document
says so plainly; conscious selection means naming the tradeoffs, not
evangelising.  See :ref:`geometric-algebra` for the foundation and
:ref:`n-dimensional` for the generalisation.

This document is the authoritative mathematical reference for the
codebase.  All descriptions reflect the current implementation
(see ``AGENTS.md`` for the design-principles summary).


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

The rotation pivot :math:`(o_x, o_y)` is the point about which the
rotation formula is applied.  For the integer-centre pieces (T, L, J)
the pivot is an integer lattice point and ``origin = (D(0), D(0))`` in
local coordinates.

For Z, S, I, and O the pivot is chosen as the **canonical half-integer
point** :math:`(-\tfrac{1}{2}, -\tfrac{1}{2})` in local coordinates
(``origin = (D('-0.5'), D('-0.5'))``).  This choice is motivated by
*arithmetic exactness*, not by a symmetry property of the piece shape:

.. math::

   x' = \underbrace{s \cdot (y - o_y)}_{\text{half-integer}}
        + \underbrace{o_x}_{\text{half-integer}}
        \;=\; \text{integer},

because :math:`y - (-\tfrac{1}{2}) = y + \tfrac{1}{2}` is a
half-integer for any integer coordinate :math:`y`, and
:math:`s \cdot (y + \tfrac{1}{2}) + (-\tfrac{1}{2})` is always an
integer (for :math:`s = \pm 1`).  The same argument applies to
:math:`y'`.  No :func:`int` truncation drift is possible because no
rounding ever occurs.

For example, the Z tetromino in its spawn orientation has local-frame
squares

.. math::

   \{(-1,1),\; (0,0),\; (0,1),\; (1,0)\},

centroid :math:`(0, \tfrac{1}{2})`.  The pivot
:math:`(-\tfrac{1}{2}, -\tfrac{1}{2})` is *not* the centroid (the O
piece is the only tetromino whose pivot equals the centroid); it is
instead the canonical half-integer point that guarantees all four
rotation states map integer coordinates to integer coordinates.

By storing the pivot with :class:`~decimal.Decimal` arithmetic, its
fractional part is preserved exactly through all translations and
rotations, giving *exact* rotation with no accumulated truncation drift,
and eliminating rotation-correcting kicks for these pieces in free
space.

.. _geometric-algebra:

Discrete Geometric Algebra: :math:`Cl(2,0,1)`
----------------------------------------------

The organising framework for the valid-move group is **discrete
plane-based geometric algebra**.  We work in the projective geometric
algebra (PGA) of the plane, the Clifford algebra :math:`Cl(2,0,1)`, and
restrict attention to the *discrete* versors that stabilise the integer
lattice :math:`\mathbb{Z}^2`.

The Algebra
~~~~~~~~~~~

:math:`Cl(2,0,1)` is generated by three basis vectors with the metric

.. math::

   e_1^2 = e_2^2 = 1, \qquad e_0^2 = 0.

The degenerate (null) generator :math:`e_0` is what makes translations
*native*: it is the algebraic ingredient absent from the vector algebra
:math:`Cl(2,0,0)`.  The even subalgebra
:math:`Cl^{+}(2,0,1) = \operatorname{span}\{1,\; e_{01},\; e_{02},\;
e_{12}\}` is four-dimensional, and its unit versors are the **motors** —
the rigid motions of the plane.

* :math:`e_{12}` is the unit bivector of the Euclidean plane.  It is the
  generator of rotation: :math:`e_{12}^2 = -1`, so the even Euclidean part
  :math:`\operatorname{span}\{1, e_{12}\}` is isomorphic to
  :math:`\mathbb{C}` and to :math:`\mathrm{Spin}(2)`.
* :math:`e_{01}` and :math:`e_{02}` are the null bivectors.  They generate
  translations along the two axes.

A geometric object (point, line) is transformed by the **sandwich
product** (the versor conjugation)

.. math::

   X \;\longmapsto\; V\, X\, \widetilde{V},

where :math:`\widetilde{V}` is the *reverse* of the versor :math:`V`.
Composition of transforms is the geometric product of versors:
:math:`V_2 (V_1 X \widetilde{V_1}) \widetilde{V_2}
= (V_2 V_1)\, X\, \widetilde{(V_2 V_1)}`.  This single composition law
subsumes both "translate then rotate" and "rotate then translate" — the
twisted multiplication of the semidirect product (see
:ref:`transform-group`) is *derived* from it rather than postulated.

.. _discrete-rotor:

The Discrete Rotor and Lattice Exactness
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The clockwise quarter-turn is the **rotor**

.. math::

   R = \exp\!\left(\tfrac{\pi}{4} e_{12}\right)
     = \cos\tfrac{\pi}{4} + e_{12}\sin\tfrac{\pi}{4}
     = \tfrac{1}{\sqrt 2}\bigl(1 + e_{12}\bigr).

The four rotors :math:`R^0, R^1, R^2, R^3` form the **discrete cyclic
group** :math:`C_4`, the lattice-stabilising rotation subgroup of the
continuous spin group :math:`\mathrm{Spin}(2)`.  As a spinor, :math:`R`
satisfies :math:`R^4 = -1` and :math:`R^8 = 1` (the double cover); the
sign is invisible in the sandwich because :math:`R^4` and
:math:`-R^4 = 1` act identically by conjugation.

**The** :math:`\sqrt 2` **is cosmetic — rotation is lattice-exact.**
Although :math:`R` carries an irrational normalisation, the sandwich
:math:`R\,P\,\widetilde R` of any integer point :math:`P \in \mathbb{Z}^2`
is again an integer point, with no rounding.  The proof is to work with
the **unnormalised rotor** :math:`U = 1 + e_{12}` (so :math:`R = U /
\lVert U \rVert` with :math:`\lVert U \rVert^2 = U\widetilde U = 2`).  For
a planar vector :math:`v = x\,e_1 + y\,e_2`,

.. math::

   U\, v\, \widetilde U
   = (1 + e_{12})(x e_1 + y e_2)(1 - e_{12})
   = 2\,(y\, e_1 - x\, e_2),

so

.. math::

   R\, v\, \widetilde R
   = \frac{U\, v\, \widetilde U}{\lVert U \rVert^2}
   = y\, e_1 - x\, e_2
   = (y, -x).

The factor of :math:`\lVert U \rVert^2 = 2` divides out exactly, the
:math:`\sqrt 2` never appears, and the map :math:`(x,y) \mapsto (y,-x)` is
**identical** to the classical CW quarter-turn (see
:ref:`rotation-formula`).  The same cancellation sends half-integer points
to half-integer points exactly: :math:`(-\tfrac12,-\tfrac12) \mapsto
(-\tfrac12, \tfrac12)`.  Consequently the discrete-rotor formulation and
the :class:`~decimal.Decimal`-origin formulation (see
:ref:`half-integer-origin`) are **arithmetically equivalent**: both give
exact rotation with no truncation drift.  An implementation may compute
the rotor sandwich with the integer versor :math:`U` and a final integer
division by 2, requiring no floating point and no :class:`~decimal.Decimal`
for the rotation step itself.

.. _discrete-translator:

The Discrete Translator
~~~~~~~~~~~~~~~~~~~~~~~~

Translation by the integer vector :math:`t = (a, b)` is the **translator**

.. math::

   T_{(a,b)} = 1 + \tfrac{1}{2}\bigl(a\, e_{01} + b\, e_{02}\bigr).

Because the null bivectors square to zero (:math:`e_{01}^2 = e_{02}^2 =
0`), the exponential truncates after the linear term — the translator is
*exactly* its first-order expansion, and the half coefficient is absorbed
by the two-sided sandwich.  The unit translators :math:`T_{e_x} = T_{(1,0)}`
and :math:`T_{e_y} = T_{(0,1)}` generate the discrete translation group,
the realisation of :math:`\mathbb{Z}^2`.

Motors and the Eigentransformations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A general element of the discrete motor group is a product
:math:`M = T R^{k}` of a translator and a power of the rotor.  The
*eigentransformations* (atomic generators of valid play) are precisely the
generating versors of this group:

* the unit translators :math:`T_{e_x}, T_{e_y}` and their inverses
  (one-step moves; gravity is :math:`T_{(0,-1)}`),
* the rotor :math:`R` and its reverse :math:`\widetilde R = R^{-1}` (CW and
  CCW quarter-turns).

The code names these versors through the type alias
``type EigenTransformation = Translation | Rotation``.  The split into two
named types is deliberate and is *not* a failure to unify: although the
motor group fuses translation and rotation into one composition law, the
**game** treats the two generator families differently — a translation
either succeeds or is blocked, whereas a rotation may succeed via a
boundary kick (see :ref:`boundary-kicks`).  The type-level split records
this behavioural distinction; the motor view records the algebraic unity.
Both are true at once.

.. _transform-group:

The Semidirect-Product Bridge: :math:`\mathbb{Z}^2 \rtimes C_4`
----------------------------------------------------------------

The discrete motor group of :ref:`geometric-algebra` is isomorphic to the
**semidirect product**

.. math::

   G = \mathbb{Z}^2 \rtimes C_4.

This is the older, standard group-theoretic name for the same group, kept
here as a **bridge** to the literature and to the code's
:class:`Translation` and :class:`Rotation` types.  It is a faithful
coordinate picture, not the foundation: the foundation is the versor
group, and the semidirect structure is a *consequence* of motor
composition, as follows.  The isomorphism sends the translator :math:`T_t`
to :math:`(t, r^0)` and the rotor :math:`R` to :math:`(0, r)`.  Under it,
the versor product :math:`(T_{t_1} R^{k_1})(T_{t_2} R^{k_2})` *derives* the
twisted multiplication law below — the law need not be postulated.  In
this realisation:

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
The operations ``move_left_max``, ``move_right_max``, and ``full_drop``
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

Rotation is the rotor sandwich of :ref:`discrete-rotor`.  About pivot
:math:`(o_x, o_y)`, a cell is conjugated by the discrete rotor :math:`R`
after translating to the pivot frame:

.. math::

   P' = T_{o}\, R\, \bigl(T_{o}^{-1} P\, T_{o}\bigr)\, \widetilde R\, T_{o}^{-1},

which is the motor :math:`T_{o} R T_{o}^{-1}` (a rotation *about*
:math:`o`) applied by sandwich.  Carrying out the algebra reduces, for the
CW generator, to the coordinate map

.. math::

   x_i' = (y_i - o_y) + o_x, \qquad y_i' = -(x_i - o_x) + o_y.

**Matrix bridge.**  For readers and code working in coordinates, the
sandwich is equivalently the linear map :math:`(dx, dy) \mapsto (dy,
-dx)`, with the four rotation matrices

.. math::

   R_0 = I,\quad
   R_1 = \begin{pmatrix}0&1\\-1&0\end{pmatrix},\quad
   R_2 = -I,\quad
   R_3 = \begin{pmatrix}0&-1\\1&0\end{pmatrix}.

These are the matrix realisation of the rotor powers :math:`R^0, R^1, R^2,
R^3` and are kept as the bridge to standard linear algebra.  The CCW
quarter-turn :math:`R^{-1} = \widetilde R = R^3` maps :math:`(dx,dy)
\mapsto (-dy, dx)`, corresponding to ``Rotation(steps=-1)``.  Verification
that :math:`R^4 = \mathrm{id}` (as a rotation; :math:`R^4 = -1` as a
spinor): the four generators rotate in order :math:`e_x \to -e_y \to -e_x
\to e_y \to e_x`, tracing a CW cycle. ✓

**Where the matrix view reads more directly.**  The integer-exactness of a
quarter-turn is *self-evident* in the coordinate map :math:`(x,y) \mapsto
(y,-x)` — it visibly sends integers to integers.  In the rotor picture the
same fact requires the :math:`\sqrt 2`-cancellation argument of
:ref:`discrete-rotor`.  This is the one place the older formulation is the
more transparent of the two; the rotor picture repays the cost with uniform
:math:`N`-dimensional generalisation (see :ref:`n-dimensional`).

In the code, the formula is currently implemented in coordinate form::

    x_new = int(r.steps * (y - o_y) + o_x)
    y_new = int(-r.steps * (x - o_x) + o_y)

where ``r.steps = +1`` is CW and ``r.steps = -1`` is CCW.  The
:func:`int` truncation is exact for pieces with integer origins (T, L, J)
and exact for pieces with half-integer origins (Z, S, I, O) because
:class:`~decimal.Decimal` arithmetic preserves the half-integer values
through all four rotation states without rounding.  By the equivalence
established in :ref:`discrete-rotor`, an equivalent integer-exact
implementation may instead apply the unnormalised rotor :math:`U = 1 +
e_{12}` and divide by :math:`\lVert U \rVert^2 = 2`, requiring neither
floating point nor :class:`~decimal.Decimal` for the rotation step (see
``docs/PLAN.md`` for the refactor).

:meth:`Polyomino.rotate` accepts a ``kick: bool = True`` parameter.
When ``True`` (the default), boundary kicks are applied via
:func:`_boundary_kicks`.  When ``False``, only the in-place rotation is
attempted — the semantics used when kick correction is disabled in the
game configuration (``GameConfig.kick = False``).

.. _boundary-kicks:

Boundary Kicks: Covariant Rotation
-----------------------------------

When the freely-rotated piece :math:`P' = r(P)` violates the grid
boundary :math:`\mathcal{B}`, a corrective translation (a *kick*) is
needed.  Rather than precomputing kick tables for each piece and state
pair (the SRS approach), the functional approach derives the kick
algebraically from the rotated piece's bounding box.

**Scope of kicks.**  The ``_boundary_kicks`` generator derives
candidates solely from violations of the **board boundary** — wall and
floor/ceiling.  It does *not* generate candidates to escape overlap with
the locked stack :math:`\mathcal{G}`.  The validity predicate
:meth:`Grid.check` — which tests both boundary and stack — is applied to
each candidate: a candidate that is in-bounds but overlaps the stack
fails at that candidate, and the next is tried.  If all candidates fail,
rotation fails silently and the piece is unchanged.

This is the correct design.  Kicks that escape stack overlap would
require finding the minimal translation such that the piece is both
in-bounds *and* not overlapping :math:`\mathcal{G}`.  This is an
NP-hard problem in general (the stack has arbitrary shape), the
analogous problem to the supremum-orbit computation for maximal
translations — which is also solved inductively, not in closed form.
Beyond computational hardness, such kicks would produce gameplay
anomalies: a piece could teleport upward or sideways out of a deep well,
departing significantly from the original game style.  The bounding-box
formula is O(1) and exact precisely because the board boundary is a
convex domain; the stack is not.

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
     (h-1) - \max_i y_i' & \text{if } \max_i y_i' \geq h \\
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
accepted.  If no candidate is valid — either because the boundary
correction itself is blocked by the stack, or because the freely-rotated
in-place position overlaps the stack with no boundary violation — rotation
fails and the piece is unchanged.  No additional candidates are generated
for stack-overlap cases (see the **Scope of kicks** note above).

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
separate render maps (``_canvas_ids: dict[Square, int]`` mapping squares
to Tkinter canvas item IDs, and ``_colors: dict[Square, Colors]``) but
does not hold the occupancy :math:`\mathcal{G}`; only
:class:`TetraTile` (the game controller) writes to and reads from
:math:`\mathcal{G}`.

:meth:`Board.render` uses a targeted delta strategy: only the squares
that changed between the previous and new active-piece positions are
erased or repainted (O(``piece.ordinal``) per tick).  Locked squares are
repainted only when the ``locked_dirty=True`` flag is passed — after a
lock event or row removal that modifies :math:`\mathcal{G}`.

Row-Major Observation
~~~~~~~~~~~~~~~~~~~~~

The :class:`GameObservation` dataclass exposes the board state to
observers and agents as a row-major nested tuple
``tuple[tuple[str | None, ...], ...]``: ``board[y][x]``, where
``y = 0`` is the bottom row and ``y = height - 1`` is the top row.  This
matches the standard convention for numpy arrays and ML agent
consumption.  Note the transposition relative to Tkinter canvas
coordinates.

The ``current_piece_rotation`` field holds the :math:`C_4` rotation
index in :math:`\{0,1,2,3\}` (0 = spawn orientation; each increment is
one additional CW quarter-turn).  It is ``-1`` when no piece is active.
The value is derived algebraically by :func:`_rotation_state` from the
current piece squares and the canonical spawn squares via the module-level
:data:`_ROTATION_TABLE`.

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

The implementation in :meth:`TetraTile.remove_full_rows` builds the
updated occupancy map in a single pass — skipping full rows and shifting
remaining cells down by the count of full rows below each — then calls
:meth:`Board.clear` and re-renders from scratch.

.. _extremal-translations:

Extremal Translations: Orbit Suprema
--------------------------------------

The operations ``move_left_max``, ``move_right_max``, and ``full_drop``
compute the *supremum of the piece's orbit* under a unit generator:

.. math::

   \text{move\_left\_max}(P, \mathcal{G})
   &= \sup\{k \geq 0 : P - k e_x
   \;\text{is valid in}\; \mathcal{G}\}, \\
   \text{move\_right\_max}(P, \mathcal{G})
   &= \sup\{k \geq 0 : P + k e_x
   \;\text{is valid in}\; \mathcal{G}\}, \\
   \text{full\_drop}(P, \mathcal{G})
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

The polyomino game is not merely *analogous* to a cellular automaton (CA) — in
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
     - :meth:`.TetraTile.remove_full_rows`
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

In the code, :meth:`.TetraTile.remove_full_rows` implements the
instantaneous version: it computes full rows in one pass and shifts
remaining cells down in a second pass, achieving the same result as the
iterated local CA in two linear scans rather than :math:`O(w)` CA
steps.

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
logic; the subclasses exist as named types so that caller code can
optionally use ``isinstance`` to identify the active frontend without
needing a separate flag.  Swapping the handler (human ↔ agent)
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
polyhypercube games.  This is the pillar where the discrete-PGA choice
pays off most directly: the framework is the algebra :math:`Cl(N,0,1)`,
and *no machinery changes* — the same motors, the same sandwich product,
the same generators — only the dimension of the algebra grows.  The older
:math:`\mathbb{Z}^N \rtimes B_N^+` names are retained below as the bridge.

**Algebra**
   :math:`Cl(N, 0, 1)`: :math:`N` Euclidean generators :math:`e_1, \ldots,
   e_N` (:math:`e_i^2 = 1`) and one null generator :math:`e_0`
   (:math:`e_0^2 = 0`).  Points, translations, and rotations are all
   versors in the even subalgebra, exactly as in the 2D case.

**Domain**
   The lattice :math:`\mathbb{Z}^N`; the domain is the :math:`N`-dimensional
   box :math:`\prod_{i=1}^N \{0, \ldots, w_i - 1\}`.  A cell is a
   unit :math:`N`-hypercube identified by its minimum-corner in
   :math:`\mathbb{Z}^N`.

**Pieces**
   :math:`N`-dimensional polyhypercubes: connected finite subsets of
   :math:`\mathbb{Z}^N`.  A ``Square`` becomes an :math:`N`-tuple.

**Translation group**
   Generated by the :math:`N` unit translators :math:`T_{e_i} = 1 +
   \tfrac12 e_{0i}`, one per null bivector.  *Bridge:* this is
   :math:`\mathbb{Z}^N`, generated by the unit vectors :math:`e_1, \ldots,
   e_N`; :class:`Translation` becomes an :math:`N`-vector
   ``tuple[int, ...]``.

**Rotation group**
   Generated by the quarter-turn rotors :math:`R_{ij} = \exp(\tfrac{\pi}{4}
   e_{ij}) = \tfrac{1}{\sqrt 2}(1 + e_{ij})`, one per Euclidean bivector
   :math:`e_{ij}`.  There are exactly :math:`\binom{N}{2}` such bivectors —
   the rotation *planes* — and the discrete subgroup they generate is the
   lattice-stabilising rotation group.

   *Bridge:* this discrete group is the proper rotation subgroup
   :math:`B_N^+` of the **hyperoctahedral group** :math:`B_N` (the signed
   permutation matrices, order :math:`2^N \cdot N!`); :math:`B_N^+` has
   order :math:`2^{N-1} \cdot N!`.  The code's ``plane: tuple[int, int]``
   field on :class:`Rotation` *is* the index pair :math:`(i, j)` selecting
   the bivector :math:`e_{ij}` — the type literally names which bivector to
   rotate by.  For :math:`N = 2`: a single bivector :math:`e_{12}`, one
   plane :math:`(0,1)`, and :math:`B_2^+ = C_4` (order 4).  For
   :math:`N = 3`: three bivectors, planes :math:`(0,1), (0,2), (1,2)`, and
   :math:`|B_3^+| = 24`.

**Rotation formula**
   The sandwich :math:`R_{ij}\, X\, \widetilde{R_{ij}}` reduces, in
   coordinates, to

   .. math::

      x_i' = \text{steps} \cdot (x_j - o_j) + o_i, \qquad
      x_j' = -\text{steps} \cdot (x_i - o_i) + o_j, \qquad
      x_k' = x_k \;\text{ for } k \notin \{i,j\}.

   The :math:`\sqrt 2`-cancellation of :ref:`discrete-rotor` holds
   verbatim per plane, so the :math:`N`-dimensional rotor sandwich is
   lattice-exact for every plane.  The current 2D formula is this
   expression with the single bivector :math:`e_{12}`, i.e. :math:`i=0,
   j=1`, hardcoded; generalisation selects the bivector via the ``plane``
   field.

**Gravity**
   One designated axis (conventionally axis :math:`N-1`, i.e.
   :math:`y` in 2D) is the gravity axis.  Each tick applies the translator
   :math:`T_{(\ldots, -1)}` along that axis.

**Full hyperslab**
   The generalisation of a full row is an :math:`(N-1)`-dimensional
   cross-section at a fixed value of the gravity axis coordinate.

**Boundary kicks**
   The ``_boundary_kicks`` generator extends naturally: for each axis
   :math:`k`, compute :math:`\delta_k` from boundary violations along
   that axis.  Yield all non-empty subsets of
   :math:`\{\delta_k : k = 1,\ldots,N\}` as correction translators, in
   order of cardinality (single-axis corrections before multi-axis
   corner corrections).

.. _why-discrete-pga:

Why Discrete PGA, and What the Earlier Objection Got Right
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Earlier versions of this document considered geometric algebra and *set it
aside* in favour of :math:`\mathbb{Z}^N \rtimes B_N^+`.  That decision has
been reversed deliberately, and it is worth recording precisely which part
of the earlier reasoning was sound and which was not.

**What the objection got right.**  The earlier concern was that rotors live
in the *continuous* Lie group :math:`\mathrm{Spin}(N) \subset
Cl(\mathbb{R}^N)^+`, whereas the game's rotations are a finite set of
quarter-turns.  This is correct, and it is exactly why the framework here is
**discrete** geometric algebra: we use only the finite, lattice-stabilising
subgroup of versors — the rotors :math:`R_{ij}` of order 4 and the integer
translators — not the full continuous spin group.  The word *discrete* is
load-bearing; it is the answer to the continuity objection, not a side-step
of it.

**What the objection got wrong.**  The earlier reasoning also held that
"translations are not native to :math:`Cl(N)`" and that encoding them
demands a heavy embedding (PGA or CGA) adding ":math:`N+1` or :math:`N+2`
dimensions" of "significant conceptual overhead."  This overstated the cost
for the plane-based case actually used here.  Plane-based PGA adds a
*single* null generator :math:`e_0` (one dimension, of *degenerate* metric),
and with it translations become genuinely native — they are versors of the
same even subalgebra as the rotations, composed by the same product.  The
"+2 dimensions" figure refers to *conformal* GA, which this construction
does not use.  Weighed correctly, the overhead is one null basis vector,
and the return is a unified composition law and a uniform :math:`N`-d
generalisation.

**Net.**  Discrete PGA is selected as the primary framework on its merits:
it unifies the two generator families under one product, derives the
semidirect-product twist rather than postulating it, and names the rotation
planes as the bivectors they are.  The semidirect product
:math:`\mathbb{Z}^N \rtimes B_N^+` and the rotation matrices are retained as
faithful bridges to the standard literature and to the code's existing type
names.  Conformal GA remains genuinely unnecessary here and would be
relevant only for a continuous-physics extension (smooth animation,
rigid-body dynamics), where the continuous rotor exponential — not the
discrete subgroup — would be the right tool.

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
   ``move_left_max``, ``move_right_max``, and ``full_drop`` are orbit
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
   integer-truncation drift.  This is *arithmetically equivalent* to the
   integer rotor sandwich (see principle 8 and :ref:`discrete-rotor`):
   both achieve exact rotation, by different routes.

8. **Discrete geometric algebra is the chosen foundation.**
   The valid-move group is presented primarily as the discrete
   lattice-stabilising versor subgroup of :math:`Cl(N,0,1)` (motors), with
   :math:`\mathbb{Z}^N \rtimes B_N^+` and the rotation matrices retained as
   bridges to the standard literature and the code's types.  The choice is
   deliberate — GA unifies translation and rotation under one composition
   law and generalises uniformly to :math:`N` dimensions.  The integer
   rotor :math:`U = 1 + e_{ij}` (with division by :math:`\lVert U \rVert^2
   = 2`) is lattice-exact: the :math:`\sqrt 2` cancels in every sandwich,
   so no floating point or :class:`~decimal.Decimal` is needed for
   rotation.

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
* Dorst, L., Fontijne, D. & Mann, S. (2007). *Geometric Algebra for
  Computer Science: An Object-Oriented Approach to Geometry*. Morgan
  Kaufmann.  (Versors, the sandwich product, and the conformal/projective
  models.)
* Gunn, C. & De Keninck, S. (2019). *Geometric Algebra for Computer
  Graphics* (SIGGRAPH course); see also bivector.net.  (Plane-based PGA
  :math:`Cl(n,0,1)`, motors, and the null-generator encoding of
  translations used as the primary framework here.)
* Hestenes, D. & Sobczyk, G. (1984). *Clifford Algebra to Geometric
  Calculus*. Reidel.  (Foundational geometric-algebra reference.)
* Humphreys, J. E. (1990). *Reflection Groups and Coxeter Groups*.
  Cambridge University Press.  (For the hyperoctahedral group :math:`B_N`,
  the bridge realisation of the discrete rotation versors.)
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
