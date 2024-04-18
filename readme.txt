The triangle_solitaire.py program (in SEMIAUTOPLAY mode) implements an n^3 algorithm for putting an arbitrary program in normal form in the triangle solitaire process.

Merging uses a different algorithm than our article, namely it uses super(affine lines) which need not be horizontal. The merging process is not confluent if you simply click on triangles at random. Normalization uses the same O(n^3) algorithm as the paper.


There are three modes:
 1) SOLITAIRE (press the number 1 to activate)
 2) EDITING (press the number 2 to activate)
 3) SEMIAUTOPLAY (press the number 3 to activate)
 
In the SEMIAUTOPLAY mode, when you left click on a triangle, and then another triangle, they are merged. If you right click on a triangle, then its contents are normalized.

In the EDITING and SOLITAIRE modes, pressing "r" toggles randomization. This means the solitaire rule is applied consecutively in random positions at regular intervals.

In the SOLITAIRE mode, if you press j or k, the triangle shaper under the mouse pointer is rotated.

In the EDITING mode, a left click adds points, and a right click removes them.

The arrow keys move the view. The "a" and "z" keys zoom. The "s" and "x" keys change the simulation speed.