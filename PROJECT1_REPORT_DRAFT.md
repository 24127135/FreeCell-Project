# VIET NAM NATIONAL UNIVERSITY HO CHI MINH CITY

## UNIVERSITY OF SCIENCE  
## FACULTY OF INFORMATION TECHNOLOGY

# PROJECT 1 REPORT  
# FREECELL SOLVER

### COURSE: INTRODUCTION TO ARTIFICIAL INTELLIGENCE (CSC14003)

Performed by:  
Vo Truong Hai (24127032)  
Truong Minh Tri (24127135)  
Ma Duc Khai (24127407)

Under the guidance of:  
Mr. Nguyen Thanh Tinh

Ho Chi Minh City, April 1, 2026

<!-- SCREENSHOT PLACEHOLDER: Cover page screenshot if required by template -->

---

## Table of Contents

1. Project Planning and Task Distribution  
2. Algorithm Description  
2.1 Search Problem Formalization  
2.2 Search Algorithms  
2.2.1 Breadth-First Search (BFS)  
2.2.2 Depth-First Search (DFS)  
2.2.3 Uniform-Cost Search (UCS)  
2.2.4 A* Search (A*)  
3. Experiments  
3.1 Experimental Setup  
3.2 Result Table  
3.3 Charts and Plots  
3.4 Insights and Discussion  
4. References  
5. Appendix

---

## 1. Project Planning and Task Distribution

### 1.1 Planning

This project was planned in four phases:

1. Core game implementation: state representation, move validation, transition rules, and win condition.
2. Solver implementation: BFS, DFS, UCS, and A* with a shared solver interface.
3. Experiment pipeline: metric collection (time, memory, expanded nodes, solution length), report output, and graph generation.
4. Reporting and packaging: experiment comparison, discussion, and submission documents.

### 1.2 Task Distribution

| Member | Student ID | Main Responsibilities | Completion (%) |
|---|---|---|---:|
| Vo Truong Hai | 24127032 | UI/UX support, video production, report editing | 100 |
| Truong Minh Tri | 24127135 | BFS/DFS implementation, UX fixes, rule engine integration, move generation | 100 |
| Ma Duc Khai | 24127407 | Heuristic design, UCS and A* implementation, measurement tester, logging/report pipeline | 100 |

### 1.3 Notes on Collaboration

- We used one shared codebase with modular separation: game, solvers, GUI, utilities.
- We prioritized reproducibility by creating a fixed test-set mode in the tester.
- Team validation was performed through cross-review and manual run checks.

### 1.4 Implementation Timeline

- Week 1:
  - Implemented core game model, legal move checking, and state transitions.
  - Built initial playable GUI loop.
- Week 2:
  - Implemented BFS/DFS/UCS/A* solvers with unified output metrics.
  - Added solver controls and visualization hooks in GUI.
- Week 3:
  - Added measurement UI, report output, graph viewer, and fixed test-set runs.
  - Collected benchmark data and refined report discussion.

---

## 2. Algorithm Description

## 2.1 Search Problem Formalization

<!-- SCREENSHOT PLACEHOLDER: Overall system architecture diagram -->

### State Representation

A FreeCell state is represented by:

- 8 cascades (tableau columns), each as an ordered list of cards.
- 4 free cells, each containing either one card or empty.
- 4 foundations, represented by top rank per suit (H, D, C, S).

### Initial State

The system supports predefined experiment states and deterministic deals.

### Actions

Legal actions include:

1. Cascade to Cascade
2. Sequence Cascade to Cascade (supermove-constrained)
3. Cascade to Free Cell
4. Free Cell to Cascade
5. Cascade to Foundation
6. Free Cell to Foundation

### Transition Function

Each legal move creates a new GameState. Illegal moves are rejected.

Optional code snippet (state transition function call path):

```python
# Example snippet placeholder
new_state = FreeCell.move_cascade_to_foundation(state, cascade_index)
```

### Goal Test

Goal is reached when each foundation has top rank 13.

### Cost Model

For UCS and A*, each move currently uses unit cost 1, minimizing number of moves.

### Repeated State Handling

Solvers track visited states (hashable state signature) to avoid cycles and repeated expansions.

### Mathematical Form

The search problem is defined as:

- State space: $S$
- Initial state: $s_0 \in S$
- Action function: $A(s)$ returns all legal moves at state $s$
- Transition model: $T(s, a) \rightarrow s'$
- Goal predicate: $G(s)$ is true if all suit foundations are complete
- Step cost: $c(s, a, s') = 1$

For A*, the evaluation function is [2]:

$$
f(n) = g(n) + h(n)
$$

where $g(n)$ is path cost and $h(n)$ estimates remaining effort.

### State Space Size Discussion

Although the practical reachable subset is much smaller due to move legality constraints,
the combinational state space is still very large. Even with all cards visible, the solver
must reason over a high-branching implicit graph where each node is a full board arrangement.
This motivates:

- strong duplicate detection,
- action ordering policies,
- and informed search (A*) instead of purely uninformed traversal.

### Correctness Conditions

The solver framework is correct when all three conditions hold:

1. Sound successor generation: every generated action is legal under FreeCell rules.
2. State transition fidelity: applying an action produces the exact expected next state.
3. Goal predicate fidelity: state is goal iff all foundations are complete (rank 13 each).

In this project, these conditions are enforced by explicit move validators and transition
functions in the game engine before any search expansion is accepted.

### Supermove Constraint

Sequence cascade moves are bounded by the available empty free cells and cascades [7][8].
For destination non-empty cascade, capacity is:

$$
C = (N + 1) \cdot 2^M
$$

where $N$ is the number of empty free cells and $M$ is the number of empty cascades (excluding the source).

---

## 2.2 Search Algorithms

## 2.2.1 Breadth-First Search (BFS)

<!-- SCREENSHOT PLACEHOLDER: BFS solver run output/log screenshot -->

### 1. Data Structure and Algorithm Properties

- Frontier: FIFO queue
- Visits states level-by-level
- Complete under finite branching
- Optimal for unit step cost

### 2. Pseudocode

```text
BFS(initial):
  queue <- [initial]
  visited <- {initial}
  parent <- map
  while queue not empty:
    s <- pop_front(queue)
    if goal(s): return reconstruct(parent, s)
    for each successor s2 of s:
      if s2 not in visited:
        visited.add(s2)
        parent[s2] <- s
        push_back(queue, s2)
  return failure
```

Optional code snippet (actual BFS loop from implementation):

```python
# Paste selected loop from solvers/bfs_solver.py here
```

### 3. Step-by-Step Trace (Conceptual)

1. Start from initial FreeCell layout.
2. Expand all depth-1 legal moves.
3. Expand all depth-2 states, and so on.
4. Stop when first goal is found.

### 4. Complexity Analysis

- Time: O(b^d)
- Space: O(b^d)

where b is branching factor, d is shallowest goal depth.

Technical note:
- BFS optimality in this project follows from unit step costs and first-goal-at-minimum-depth behavior.
- Practical cost is dominated by frontier memory because all nodes at depth $d$ may coexist.

### 5. Advantages and Disadvantages

Advantages:
- Guarantees shortest solution length with unit cost.
- Simple and robust.

Disadvantages:
- Very high memory consumption on larger search frontiers.

Observed in our experiments:
- BFS expanded 21,357 nodes on 10-card Priority ON and 49,898 nodes on 11-card Priority ON.
- With Priority OFF (11-card), BFS timed out at 120 seconds and reached very high peak memory.

---

## 2.2.2 Depth-First Search (DFS)

<!-- SCREENSHOT PLACEHOLDER: DFS solver run output/log screenshot -->

### 1. Data Structure and Algorithm Properties

- Frontier: stack / recursion depth
- Explores deep path first
- Uses visited-state checks and practical limits in implementation

### 2. Pseudocode

```text
DFS(initial):
  stack <- [initial]
  visited <- {}
  parent <- map
  while stack not empty:
    s <- pop(stack)
    if s in visited: continue
    visited.add(s)
    if goal(s): return reconstruct(parent, s)
    for each successor s2 of s:
      if s2 not in visited:
        parent[s2] <- s
        push(stack, s2)
  return failure
```

Optional code snippet (actual DFS loop from implementation):

```python
# Paste selected loop from solvers/dfs_solver.py here
```

### 3. Step-by-Step Trace (Conceptual)

1. Choose one legal move branch.
2. Keep descending until dead end, limit, or goal.
3. Backtrack and try next branch.

### 4. Complexity Analysis

- Time: O(b^m)
- Space: O(bm)

where m is maximum search depth.

Technical note:
- DFS is not optimal under unit costs.
- Completeness depends on finite-depth constraints and loop prevention strategy.
- In implicit cyclic spaces like FreeCell, visited-state control is essential.

### 5. Advantages and Disadvantages

Advantages:
- Low memory footprint relative to BFS/UCS.
- Can find solution quickly on favorable branch orders.

Disadvantages:
- Not optimal.
- Sensitive to branching order and may get trapped in deep unproductive paths.

Observed in our experiments:
- DFS solved both Priority ON testcases with only 13-14 expanded nodes in this dataset.
- This indicates favorable branch ordering on these specific cases, but this behavior is not guaranteed on harder layouts.

---

## 2.2.3 Uniform-Cost Search (UCS)

<!-- SCREENSHOT PLACEHOLDER: UCS solver run output/log screenshot -->

### 1. Data Structure and Algorithm Properties

- Frontier: priority queue ordered by path cost g(n)
- Complete and optimal for non-negative costs

### 2. Edge Cost Design

Cost model used in this project:

- Each legal move has cost 1.

Rationale:
- The objective is minimizing number of moves.
- This ensures consistent comparison with BFS shortest-move behavior.

Alternative model (not used in final runs):
- Weighted move costs (for example, penalizing temporary free-cell usage)
  can encode strategy preferences, but this changes the optimization objective
  from shortest path length to weighted effort.

### 3. Pseudocode

```text
UCS(initial):
  pq <- priority queue with (0, initial)
  best_cost[initial] <- 0
  parent <- map
  while pq not empty:
    g, s <- pop_min(pq)
    if goal(s): return reconstruct(parent, s)
    if g > best_cost[s]: continue
    for each successor s2 of s with edge cost c:
      g2 <- g + c
      if s2 not in best_cost or g2 < best_cost[s2]:
        best_cost[s2] <- g2
        parent[s2] <- s
        push(pq, (g2, s2))
  return failure
```

Optional code snippet (priority queue and cost update in UCS):

```python
# Paste selected block from solvers/ucs_solver.py here
```

### 4. Step-by-Step Trace (Conceptual)

1. Expand currently cheapest path.
2. Update frontier with improved path costs.
3. Continue until goal is popped from priority queue.

### 5. Complexity Analysis

- Time: O((V + E) log V) in graph-search form
- High practical overhead in large implicit spaces

Technical note:
- Under uniform edge costs, UCS often expands similarly to BFS but still pays
  heap operations for priority handling, which explains slower wall-clock time
  in our measurements.

### 6. Advantages and Disadvantages

Advantages:
- Optimal under non-negative costs.
- Flexible for weighted move designs.

Disadvantages:
- Often slower than BFS under uniform costs due to priority queue overhead.
- High memory usage from cost table and frontier.

Observed in our experiments:
- UCS took 2.6399s (10-card ON) and 5.2683s (11-card ON), slower than BFS on the same testcases.
- Expanded nodes were also higher than BFS in both ON cases.

---

## 2.2.4 A* Search (A*)

<!-- SCREENSHOT PLACEHOLDER: A* solver run output/log screenshot -->

### 1. Data Structure and Algorithm Properties

- Frontier: priority queue ordered by f(n) = g(n) + h(n)
- Uses heuristic guidance toward goal

### 2. Heuristic Design

Current heuristic combines:

1. Base term: number of cards not yet placed into foundations.
2. Deadlock-aware penalty: suit-order blocking patterns in cascades.

Intuition:
- Lower cards buried under same-suit higher cards can delay legal foundation progress.

Heuristic structure used in analysis terms:

$$
h(n) = h_0(n) + p(n)
$$

where:

- $h_0(n)$ = number of cards not yet placed into foundations,
- $p(n)$ = deadlock-aware penalty term for blocking patterns.

Interpretation:
- $h_0$ captures global distance-to-goal.
- $p$ adds local structural difficulty from cascade ordering.

### 3. Pseudocode

```text
AStar(initial):
  pq <- priority queue with (h(initial), 0, initial)
  best_g[initial] <- 0
  parent <- map
  while pq not empty:
    f, g, s <- pop_min(pq)
    if goal(s): return reconstruct(parent, s)
    if g > best_g[s]: continue
    for each successor s2 of s with edge cost c:
      g2 <- g + c
      if s2 not in best_g or g2 < best_g[s2]:
        best_g[s2] <- g2
        parent[s2] <- s
        push(pq, (g2 + h(s2), g2, s2))
  return failure
```

Optional code snippet (heuristic usage in A*):

```python
# Paste selected block from solvers/astar_solver.py here
```

### 4. Step-by-Step Trace (Conceptual)

1. Start with initial state scored by heuristic.
2. Expand state with smallest estimated total cost.
3. Prioritize promising branches while preserving best-g checks.

### 5. Complexity Analysis

Worst-case remains exponential, but heuristic can reduce explored states significantly in practice.

Technical note:
- A* is complete for finite branching with positive costs.
- Optimality depends on heuristic admissibility/consistency.
- Because $p(n)$ may overestimate in some states, strict optimality guarantee is not claimed for all cases.

### 7. Admissibility and Consistency Discussion

Base component:
- $h_0(n)$ is admissible under unit costs because at least one move is needed per
  card not yet in foundation in any valid completion sequence.

Penalty component:
- $p(n)$ improves guidance but can overestimate remaining true cost in some
  configurations, so the combined heuristic may be non-admissible.

Consistency:
- Consistency would require $h(n) \le c(n,n') + h(n')$ for every edge.
- This is not guaranteed with the added penalty term.

Engineering tradeoff:
- We prioritize practical search efficiency for this assignment benchmark setting,
  while documenting that strict A* optimality is not guaranteed under non-admissible penalties.

### 6. Advantages and Disadvantages

Advantages:
- Best empirical speed/memory tradeoff on tested cases.
- Strong reduction in expanded nodes compared to BFS/UCS.

Disadvantages:
- Quality depends on heuristic design.
- If heuristic is not strictly admissible, strict optimality guarantees may not hold.

Observed in our experiments:
- A* solved both Priority ON testcases within ~0.005s with only 13-14 expanded nodes.
- On 11-card Priority OFF, A* remained stable (0.0224s) while BFS timed out.

---

## 3. Experiments

## 3.1 Experimental Setup

- Environment: Python 3.14, desktop execution.
- Tester: measurement UI pipeline.
- Fixed test set: 10-card and 11-card configurations.
- Modes: Foundation Priority ON and OFF.
- Collected metrics:
  - Search time (seconds)
  - Peak memory usage (MB)
  - Expanded nodes
  - Solution length

<!-- SCREENSHOT PLACEHOLDER: Measurement UI with fixed test set controls -->

### Runtime Policy

- BFS limits in tester: maximum expansions and time cap to prevent GUI freeze.
- DFS limits in tester: depth cap and time cap.
- Batch mode executes all solver/case combinations in fixed order for fair comparison.

### Fairness Controls

- Same testcase definitions are reused across all algorithms.
- Each algorithm is run from the same initial state per testcase.
- Metrics are captured by one unified measurement pipeline.
- Priority ON/OFF modes are explicitly logged in result headers.

### Internal Validity Measures

- All solvers consume the same state representation and successor generator.
- Metrics are captured in one code path to avoid instrumentation mismatch.
- Batch mode applies a deterministic run order for comparable logs.

## 3.2 Result Table

The following values are taken from current run logs.

<!-- SCREENSHOT PLACEHOLDER: Raw results_ui.txt excerpt screenshot -->

### Priority ON

| Test Case | Algorithm | Search Time (s) | Peak Memory (MB) | Expanded Nodes | Solution Length | Status |
|---|---|---:|---:|---:|---:|---|
| 10 cards | A* | 0.0044 | 0.0628 | 13 | 12 | SUCCESS |
| 10 cards | BFS | 1.6250 | 29.8977 | 21357 | 12 | SUCCESS |
| 10 cards | DFS | 0.0052 | 0.0605 | 13 | 12 | SUCCESS |
| 10 cards | UCS | 2.6399 | 31.2238 | 24851 | 12 | SUCCESS |
| 11 cards | A* | 0.0053 | 0.0990 | 14 | 13 | SUCCESS |
| 11 cards | BFS | 3.8683 | 63.4102 | 49898 | 13 | SUCCESS |
| 11 cards | DFS | 0.0029 | 0.0718 | 14 | 13 | SUCCESS |
| 11 cards | UCS | 5.2683 | 64.7913 | 51777 | 13 | SUCCESS |

### Priority OFF

| Test Case | Algorithm | Search Time (s) | Peak Memory (MB) | Expanded Nodes | Solution Length | Status |
|---|---|---:|---:|---:|---:|---|
| 11 cards | A* | 0.0224 | 0.3778 | 14 | 13 | SUCCESS |
| 11 cards | BFS | 120.0006 | 587.8497 | 52027 | N/A | FAILED (Timeout) |
| 11 cards | DFS | 0.0269 | 0.3495 | 14 | 13 | SUCCESS |
| 11 cards | UCS | N/A | N/A | N/A | N/A | Not completed in current log |
| 10 cards | All | N/A | N/A | N/A | N/A | Not completed in current log |

### Aggregated Summary (Priority ON)

| Algorithm | Avg Search Time (s) | Avg Peak Memory (MB) | Avg Expanded Nodes | Avg Solution Length |
|---|---:|---:|---:|---:|
| A* | 0.0049 | 0.0809 | 13.5 | 12.5 |
| DFS | 0.0041 | 0.0662 | 13.5 | 12.5 |
| BFS | 2.7467 | 46.6540 | 35627.5 | 12.5 |
| UCS | 3.9541 | 48.0076 | 38314.0 | 12.5 |

### Relative Comparison Examples

- On 11-card Priority ON:
  - A* is approximately $3.8683 / 0.0053 \approx 730$x faster than BFS.
  - A* is approximately $5.2683 / 0.0053 \approx 994$x faster than UCS.
- Memory on 11-card Priority ON:
  - A* uses 0.0990 MB versus BFS 63.4102 MB and UCS 64.7913 MB.

### Theoretical Interpretation of Results

- BFS/UCS high memory aligns with frontier-dominant behavior predicted by their
  theoretical space complexity.
- DFS low memory aligns with depth-oriented traversal and limited active path storage.
- A* low expansions indicate heuristic effectively reduces the explored search envelope.

## 3.3 Charts and Plots

Use chart outputs generated from the report viewer/graph module. Include:

1. Average Search Time by algorithm
2. Average Expanded Nodes by algorithm
3. Average Peak Memory by algorithm

Suggested figure captions:
- Figure 1. Time comparison among BFS, DFS, UCS, A*.
- Figure 2. Expanded-node comparison among BFS, DFS, UCS, A*.
- Figure 3. Peak-memory comparison among BFS, DFS, UCS, A*.

Figure insertion placeholders:

- Figure 1 placeholder: insert chart screenshot (time comparison)
- Figure 2 placeholder: insert chart screenshot (expanded nodes)
- Figure 3 placeholder: insert chart screenshot (memory comparison)

Optional code snippet (graph data generation path):

```python
# Paste selected block from gui/interface.py:
# - generate_report_graph
# - _build_report_graph_data
```

## 3.4 Insights and Discussion

### Main observations

1. A* and DFS are consistently fastest on these small test cases.
2. BFS and UCS consume significantly more memory and time, especially on 11-card cases.
3. BFS with Priority OFF reached timeout at 120 seconds and high memory usage (~588 MB).
4. Priority ON appears to stabilize search behavior for BFS/UCS.

### Interpretation

- A* benefits from heuristic guidance and avoids broad frontier expansion.
- DFS performed very well in these cases due to favorable branch ordering and shallow solvable depth.
- UCS behaves similarly to BFS under unit-cost moves but with additional priority-queue overhead.

### Practical implication

For the tested scenarios, A* provides the strongest overall balance between speed and memory.

### Why Priority Mode Matters

When foundation-priority is enabled, the successor ordering tends to move safe cards upward to foundations earlier, which can reduce search branching in many positions. This effect is visible in our data where BFS/UCS are substantially more stable in Priority ON mode than in Priority OFF mode.

### Threats To Validity

1. Small benchmark size:
  - Current logs include a limited number of cases, so conclusions are strong for these cases but not yet universal.
2. Parameter sensitivity:
  - DFS/BFS/UCS behavior can change with depth limits, expansion caps, and timeout settings.
3. Heuristic dependence:
  - A* performance depends strongly on heuristic quality and may vary across unseen deal distributions.
4. Timeout-induced censoring:
  - Timeout cutoffs can truncate slower algorithms, which biases final observed
    metrics toward successful subsets unless clearly reported as failures.

### Recommended Next Experiment

- Expand fixed set to at least 10 deterministic deals.
- Run each deal under both Priority ON and OFF.
- Report confidence trends using averages and standard deviation per metric.

---

## 4. References

1. FreeCell - Wikipedia. https://en.wikipedia.org/wiki/FreeCell
2. Russell, S., Norvig, P. Artificial Intelligence: A Modern Approach.
3. Python documentation. https://docs.python.org/3/
4. Tkinter documentation. https://docs.python.org/3/library/tk.html
5. Project brief: CSC14003 Project 1 (course handout).
6. Cormen, T. H., et al. Introduction to Algorithms (for priority queue and complexity background).
7. Rosetta Code. Deal cards for FreeCell. https://rosettacode.org/wiki/Deal_cards_for_FreeCell
8. Solitaire Laboratory. FreeCell FAQ. http://www.solitairelaboratory.com/fcfaq.html
9. Solitaire Laboratory. Microsoft Shuffle Algorithm. http://www.solitairelaboratory.com/mshuffle.txt

---

## 5. Appendix

## 5.1 Reproducibility

Run commands:

```bash
python main.py
python main.py --self-test
python measure.py
```

Dependencies are listed in requirements.txt.

Data artifacts used in this report:
- results_ui.txt
- results_graph.json

Optional code snippet (tester batch run entry):

```python
# Paste selected block from measure.py:
# - start_batch_thread
# - run_fixed_test_set
```

## 5.2 AI Usage Statement

This project used LLM assistance for:
- code review suggestions,
- report drafting structure,
- UI/reporting robustness improvements.

All generated outputs were reviewed and validated by the team before inclusion.

Examples of assisted tasks:
- report structure drafting
- experiment table formatting
- robustness fixes for measurement batch execution and report view UI

Verification process:
- Every AI-assisted claim in algorithms/complexity sections was cross-checked
  against implemented behavior and measured logs before inclusion.

## 5.3 Final Packaging Checklist

- Source code folder included
- README with run instructions included
- requirements.txt included
- Report PDF includes video URL
- Archive name follows assignment format

<!-- SCREENSHOT PLACEHOLDER: Final application GUI (manual gameplay) -->
<!-- SCREENSHOT PLACEHOLDER: Solver animation or completion popup -->
<!-- SCREENSHOT PLACEHOLDER: Report viewer and graph viewer -->
