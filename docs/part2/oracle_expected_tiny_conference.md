# Oracle Expected - Tiny Conference

---

## T1

Legend:
- y_# -> 1 if the activity # is going to be chosen or 0 if not

1. Activities:

A = y_0 \
B = y_1 \
C = y_2 \
D = y_3

2. Conflicts:

c_01 = -1 + y_0 + y_1  ≤ 0     (A-B) \
c_12 = -1 + y_1 + y_2  ≤ 0     (B-C) \
c_23 = -1 + y_2 + y_3  ≤ 0     (C-D)

---

## Atoms

conflict_0_1: \
    -1 -> when both (y_0 and y_1) are 0 \
    0  -> when exactly one of them (y_0 or y_1) is 1 \
    1  -> when both (y_0 and y_1) are 1 

conflict_1_2: \
    -1 -> when both (y_1 and y_2) are 0 \
    0  -> when exactly one of them (y_1 or y_2) is 1 \
    1  -> when both (y_1 and y_2) are 1 

conflict_2_3: \
    -1 -> when both (y_2 and y_3) are 0 \
    0  -> when exactly one of them (y_2 or y_3) is 1 \
    1  -> when both (y_2 and y_3) are 1 

When an atom (conflict_0_1, conflict_1_2 or conflict_2_3) has value 1 then it means there is a conflict.

---

## Detection of Conflicts

Given a conflict can have value [-1, 0, 1], we need at least 2 bits to represent these values, following two's complement.

For example: \
    00 -> 0 \
    01 -> 1 \
    10 -> -2 \
    11 -> -1

This approach causes a problem since the sign bit doesn't necesssarily tell us whether there is a conflict or not.
Because of that, a domain transformation is required: \
    conflict' = conflict - 1

Meaning: \
conflict'_0_1: \
    -2 -> when both (y_0 and y_1) are 0 \
    -1 -> when exactly one of them (y_0 or y_1) is 1 \
    0  -> when both (y_0 and y_1) are 1 

conflict'_1_2: \
    -2 -> when both (y_1 and y_2) are 0 \
    -1 -> when exactly one of them (y_1 or y_2) is 1 \
    0  -> when both (y_1 and y_2) are 1 

conflict'_2_3: \
    -2 -> when both (y_2 and y_3) are 0 \
    -1 -> when exactly one of them (y_2 or y_3) is 1 \
    0  -> when both (y_2 and y_3) are 1 

This now allow us to only define: \
    10 -> -2 \
    11 -> -1 \
    00 -> 0

Which means that the sign bit is able to tell us whether there's a conflic or not.

---

## Marked Assignments

Qiskit reads bitstrings with q0 on the right, so each string is y_3 y_2 y_1 y_0.

Marked (no conflict): \
    0000 -> {} \
    0001 -> A \
    0010 -> B \
    0100 -> C \
    1000 -> D \
    0101 -> A, C \
    1001 -> A, D \
    1010 -> B, D

Not marked (at least one conflict): \
    0011 -> A, B \
    0110 -> B, C \
    0111 -> A, B, C \
    1011 -> A, B, D \
    1100 -> C, D \
    1101 -> A, C, D \
    1110 -> B, C, D \
    1111 -> A, B, C, D
