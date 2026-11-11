# Oracle Expected - Tiny Workshop

---

## T1

Legend:
- y_# -> 1 if the activity # is going to be chosen or 0 if not

1. Activities:

A = y_0 \
B = y_1 \
C = y_2

2. Conflicts:

c_01 = -1 + y_0 + y_1  ≤ 0     (A-B)

B and C share the Room but are back-to-back ([30, 90) and [90, 120)), so there is no conflict between them.

---

## Atoms

conflict_0_1: \
    -1 -> when both (y_0 and y_1) are 0 \
    0  -> when exactly one of them (y_0 or y_1) is 1 \
    1  -> when both (y_0 and y_1) are 1 

When the atom conflict_0_1 has value 1 then it means there is a conflict.

---

## Detection of Conflicts

Given a conflict can have value [-1, 0, 1], we need at least 2 bits to represent these values, following two's complement.

For example: \
    00 -> 0 \
    01 -> 1 \
    10 -> -2 \
    11 -> -1

This approach causes a problem since the sign bit doesn't necessarily tell us whether there is a conflict or not.
Because of that, a domain transformation is required: \
    conflict' = conflict - 1

Meaning: \
conflict'_0_1: \
    -2 -> when both (y_0 and y_1) are 0 \
    -1 -> when exactly one of them (y_0 or y_1) is 1 \
    0  -> when both (y_0 and y_1) are 1 

This now allows us to only define: \
    10 -> -2 \
    11 -> -1 \
    00 -> 0

Which means that the sign bit is able to tell us whether there's a conflict or not.

In total: 3 (y) + 1 x 2 (atom) = 5 qubits.

---

## Marked Assignments

Qiskit reads bitstrings with q0 on the right, so each string is y_2 y_1 y_0.

Marked (no conflict): \
    000 -> {} \
    001 -> A \
    010 -> B \
    100 -> C \
    101 -> A, C \
    110 -> B, C

Not marked (at least one conflict): \
    011 -> A, B \
    111 -> A, B, C
