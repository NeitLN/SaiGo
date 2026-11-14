# SaiGo: Delivery Route Planning on Ho Chi Minh City Street Networks Using Heuristic Search

**Introduction to AI (261_72ITSE30303_01) · Lecturer: Dr. Huy T. Nguyen · Group 4**

| Member | Student ID |
|---|---|
| Võ Việt Tiến | [student ID] |
| Bùi Duy Anh | [student ID] |
| Đỗ Quốc Bảo | [student ID] |
| Võ Hoàng Minh | [student ID] |

*(Cover page. The essay body below is about 10 double-spaced pages; every number comes from `docs/EXPERIMENTS.md` and is traceable to a `run_id` in `results/`.)*

---

## 1. Introduction

A courier leaves a depot with a handful of orders in District 1. Three questions follow: which road to take between two stops, in which order to visit the stops, and what to do when a road on the way is closed. Ho Chi Minh City adds a fourth complication: many streets are one-way, so the cost from A to B is often different from B to A.

SaiGo answers these questions on the real street network of central Ho Chi Minh City. It is a search problem in the sense of the course's "Pathfinding in Complex Environments" project: a city map with simulated traffic and dynamic obstacles (closed roads). The street geometry, directions and road classes are real (OpenStreetMap); travel times and congestion are simulated from a speed table, so all results describe the model, not live traffic.

We study three research questions from the proposal of 2 October, plus one sub-question (RQ1b) added afterwards:

- **RQ1.** Does A\* reduce search effort compared with Dijkstra while returning the same optimal cost? **RQ1b** (added after the proposal): how does that change as the map grows?
- **RQ2.** How much do Nearest Neighbor (NN) and directed 2-opt improve a delivery tour over the input order, and how far are they from the optimum (Held–Karp)?
- **RQ3.** How do congestion and road closures affect feasibility, route cost and the work of the search?

Our contributions are: our own implementations of Dijkstra, A\*, NN, directed 2-opt and Held–Karp, checked against NetworkX; a reproducible benchmark on a frozen dataset (16,060 timed searches over 6,030 query instances, plus 120 delivery tours); and a local web application that shows the same algorithms on a map, including closing a road on a route or on a tour and replanning.

The answers are not all "the heuristic wins". A\* expands about 40% of the nodes Dijkstra expands but is barely faster on our demo map; its clearest speed-up is on medium-length trips, and only the stronger landmark heuristic (ALT) gains clearly on long trips over a larger map. NN + 2-opt is close to optimal on average but can get stuck in a poor local optimum on directed costs. We report these results as measured.

## 2. Data and problem formulation

**Street network.** We downloaded the drivable OSM network of a 10 km × 10 km square around Bến Thành market once (24 October 2026, via OSMnx [Boeing 2017]), froze the raw file with a SHA-256 hash and published it as a release, so every experiment uses the same data. From it we cut a demo area of 4 km × 4 km: 1,889 nodes and 4,004 directed edges, of which 1,332 (33%) are one-way. The search runs on the largest strongly connected component (1,745 nodes), so every snapped point can reach every other one before any closure. For the scaling experiment we cut four nested squares with half-sides 1, 2, 3 and 4.5 km (565 to 10,143 nodes); a smaller square's component lies inside every larger one.

**Graph and costs.** The network is a directed multigraph G = (V, E). Each edge e = (u, v, key) keeps its own id, length L(e) and road class, so parallel edges and closures refer to exact edges. The cost we optimise is **travel time in seconds**, not distance: w(e) = L(e) / v(class(e)) · α(e), where v comes from a fixed speed table (from 15 km/h for service roads to 40 km/h for trunk roads; v_max = 40 km/h) and α(e) ≥ 1 is a congestion factor. Distance is still reported, but congestion only makes sense on time.

**Scenarios and closures.** A scenario multiplies the weights of edges whose midpoint lies inside a circular zone, optionally only for some road classes; overlapping zones take the largest α. The demo scenario "simulated peak, centre" uses α = 2 on primary and secondary roads within 600 m of Nguyễn Huệ – Lê Lợi and α = 1.5 within 400 m of the market. A closure removes edge ids from a per-request *snapshot*; closing a road "segment" removes the edge and its reverse twin if the street is two-way. The base graph is never modified, so requests cannot leak state into each other.

**Two-level problem.** Level one is the shortest path between two points, or "no path". Level two is the visiting order: from a depot and n stops we build a matrix D where D[i][j] is the shortest travel time from point i to point j on the current snapshot, and we look for the closed tour depot → stops → depot of minimum total cost. Because of one-way streets D is asymmetric, so this is an asymmetric travelling salesman problem.

## 3. Methods

**Dijkstra.** Our reference algorithm uses a binary heap with lazy deletion (stale heap entries are skipped when popped), so it runs in O((V + E) log V) [Dijkstra 1959]. The predecessor array stores the *edge* used to reach each node, so the route is rebuilt edge by edge and respects parallel edges and closures. A query stops when the target is popped; "expanded" counts the nodes popped and relaxed before that.

**A\*.** A\* orders the frontier by g(n) + h(n) [Hart, Nilsson & Raphael 1968]. Our heuristic is the remaining time at top speed: h(n) = c · hav(n, t) / v_max, where hav is the great-circle distance. It is **admissible** because no route is shorter than the straight line and no edge is faster than v_max; congestion only multiplies weights by α ≥ 1, which keeps the bound valid. It is also **consistent**, h(u) ≤ w(u, v) + h(v), by the triangle inequality, so A\* never needs to reopen a closed node [Russell & Norvig 2021]. The safety factor c ≤ 1 is computed from the data: if any edge were shorter than the straight-line distance between its endpoints, c shrinks to keep the bound. On our data c = 0.99999999984, i.e. only floating-point noise. We check optimality empirically too (Section 4).

**Extensions.** Two further searches were added late and are reported as an extension, not as part of the research questions: bidirectional Dijkstra [Pohl 1971] and ALT, A\* with landmark lower bounds [Goldberg & Harrelson 2005] using eight landmarks.

**Tour ordering.** The input order is the baseline. NN starts at the depot and repeatedly goes to the cheapest unvisited stop. Directed 2-opt [Croes 1958] reverses a segment of the tour; on an asymmetric matrix reversing a segment also reverses every leg inside it, so the usual constant-time delta formula is wrong. We therefore recompute the full tour cost for every candidate move and accept a move only if that cost strictly decreases (first improvement). Held–Karp dynamic programming [Held & Karp 1962] gives the exact optimum in O(2ⁿ n²) and is used as a reference up to 10 stops. The application returns the cheapest of input, NN and NN + 2-opt, keeping the earlier option on ties, so it never replaces the input order by a worse one.

**Replanning after a closure.** When a road is closed, the snapshot changes, so the matrix is rebuilt. We report two plans separately: **keep the old order** (same visiting order, every leg searched again on the new snapshot) and **re-order** (run the tour heuristics again). This separates the effect of the routing algorithm from the gain of re-ordering. If any leg becomes impossible, there is no closed tour and the system names the stops that cannot be reached instead of drawing a partial tour.

**What we wrote ourselves.** All searches, the heuristic and its check, snapshots and closures, snapping, the tour heuristics, Held–Karp and the benchmark harness. OSMnx is used only to download data, NetworkX only as an oracle in tests, FastAPI and Leaflet only as the web and map layers.

## 4. Experimental setup

**Correctness (E1).** Dijkstra and A\* match six hand-computed cases on a 6-node fixture; match NetworkX on 1,000 queries over 20 random graphs with parallel edges and unreachable pairs; and match NetworkX on 200 random pairs of the real demo graph. Every benchmark run also stops if the two costs differ by more than 10⁻⁶ relative.

**Query sets.** Pairs are drawn with a fixed seed from the strongly connected component and stratified by normalised straight-line distance δ = hav(s, t) / L, where L is the side of the area: short (δ < 0.2), medium (0.2–0.5) and long (≥ 0.5), one third each. The query file is saved before measuring and reused when a run is repeated.

**Measurement.** One Python 3.11.9 process; graph loading and snapshot building are excluded; tracing is off; 20 warm-up queries; each algorithm runs five times per pair and we keep the median; the algorithm order alternates between pairs; garbage collection is disabled while timing. A\* time includes building its heuristic. Ratios are computed **per pair** and then summarised: r = expanded(A\*) / expanded(Dijkstra) and s = time(Dijkstra) / time(A\*). Each run records its commit, a "dirty tree" flag (all reported runs are clean), the dataset hash and the machine.

**Experiments.** E2: 1,000 pairs on the demo area. E3: 250 fixed trips drawn in the 1 km area and replayed unchanged on all four nested areas. E4: 300 pairs under each congestion scenario; 100 pairs with the middle segment of the baseline route closed; 30 pairs with every edge into the target closed. E5: tours with n ∈ {4, 5, 6, 8, 10} stops, 20 random sets each, stops at least 150 m apart. E5b: the 20 sets of n = 5 with the middle segment of the tour closed.

## 5. Results and discussion

**RQ1: A\* versus Dijkstra (E2, run `20261031-1556-demo-054f300`).** All 1,000 pairs returned the same cost, and A\* never reopened a node. A\* expanded far fewer nodes: median r = 0.398 overall, stable across strata (0.376 short, 0.348 medium, 0.467 long). Time did not follow. The median per-pair speedup was only s = 1.03, A\* was slower on 480 of 1,000 pairs, and the clear gain was in the medium stratum (s = 1.22). A cross-check on a second machine with the same query file (`20261103-crosscheck-demo-minh`) reproduced every cost and every expanded count exactly and gave s = 1.07. Our explanation, not separately measured, is that each A\* push computes a great-circle distance with trigonometric functions, while a Dijkstra push is an addition; on a 1,889-node graph a query takes about 1 ms, and that overhead eats most of the saving. **Fewer expanded nodes is not the same as faster.**

**RQ1b: a larger map (E3, run `20261113-0438-scaling-cb16bc0`).** With fixed trips, A\*'s advantage grew from the 1 km to the 2 km area (median r 0.448 → 0.327) and then stayed flat (0.316 at 3 and 4.5 km). Median expanded counts stopped changing after 2 km for both algorithms: when the trip stays the same, a larger map adds nodes the search never needs. Yet time still grew from 2 to 4.5 km (Dijkstra 0.142 → 0.200 ms, A\* 0.110 → 0.138 ms); part of this is initialising per-query arrays of size |V|, the rest we could not attribute. A separate comparison of four algorithms (E2b, run `20261113-1327-compare-871bf02`, pairs drawn per map so long trips are genuinely longer on the larger map) shows where heuristics pay off: on long trips in the 4.5 km area, median time was 11.2 ms for Dijkstra, 10.1 ms for bidirectional Dijkstra, 8.0 ms for A\* and 3.9 ms for ALT (per-pair s = 1.12, 1.27 and 2.67). On short trips ALT was 2.3–2.6 times *slower* than Dijkstra even though it expanded the fewest nodes, and it needs 366 ms of preprocessing on that map.

**RQ2: tour quality (E5, runs `20261113-0448-tour-12dd1e0` and `20261114-0517-tour-04a0d7e`).** Re-ordering helps, and more so with more stops: NN + 2-opt was cheaper than the (random) input order by a median of 11.6% for 4 stops and 41.0% for 10. Computed per set, 2-opt added a median of 0.4–6.0 percentage points over NN alone. NN + 2-opt was near-optimal on average (median gap 0–1.8% to Held–Karp; it found the optimum in 45 of 80 sets of the first run), but not always: the 90th percentile gap reached 8.6% and the worst set 14.1%. Building the distance matrix (n + 1 one-to-many Dijkstra searches, 3–8 ms) took 50–130 times longer than ordering the stops with NN + 2-opt (below 0.15 ms), so in this application the routing level, not the ordering level, dominates time.

Our demo case is a useful counterexample. For "depot + 5 stops" NN + 2-opt costs 898.1 s while the optimum is 627.8 s, a 43% gap. 2-opt improved the NN tour from 1,003.3 s to 898.1 s and then stopped at a local optimum. The optimal tour is the NN tour driven in the opposite direction; on directed costs, driving a tour backwards changes every leg, so the two tours are far apart for a move that reverses one segment at a time. Among the 20 random five-stop sets the worst gap was 12.2%, and a gap this large did not occur in any of the 100 random sets; the case is not typical, but it shows concretely why directed 2-opt is only a local search.

**RQ3: congestion and closures (E4, run `20261113-0444-scenario-c1cd80b`; E5b, run `20261114-0517-tourclosure-04a0d7e`).** Zonal congestion changed the route for 18.7% of pairs under the central peak scenario and 15.7% under the Bến Thành roundabout scenario; most pairs do not cross the zone (median cost increase 0%), while the affected tail rose by up to 15.7% at the 90th percentile. A uniform multiplier would never change a route, which is why we model congestion by zone. A\*'s advantage shrank slightly under congestion (median r 0.403 → 0.422), consistent with the heuristic being looser when the true speed is below v_max; the effect is small. Closing the middle segment of a route left a detour for all 100 pairs, at a median cost increase of 4.3% (90th percentile 21.9%); rebuilding the snapshot took 0.45 ms and the new search 0.6–0.8 ms. When the target was deliberately cut off, both algorithms expanded the whole reachable component (1,763 nodes) before reporting "no path", and A\* was 2.15 times slower per pair: a heuristic cannot help when there is no path.

For tours (E5b), closing one segment in the middle of the chosen tour broke the closed tour in 2 of 20 sets, which is why the system must report "no complete tour" and name the failing stop. In the remaining 18 sets keeping the old order cost a median 1.4% more (worst 13.7%), and re-ordering changed the order in only 3 sets, saving at most 7.3% over keeping the order; in this sample it was never worse (nothing guarantees that, since re-ordering does not consider the old order). The demo closure we show (keep order 962.7 s, re-order 692.5 s) is deliberately chosen and atypical: most of its gain comes from escaping the poor local optimum above, not from the closure itself.

## 6. Limitations and conclusion

**Limitations.** Travel times come from an assumed speed table, so absolute times are model-based, not real ETAs; we ignore turn restrictions and traffic lights. We use OSM's car network as an approximation for motorbikes. All results come from one central area of one city, timings mostly from one machine in Python, and some tails (A\*'s slower 95th percentile, part of the scaling slowdown) are observed but not explained. The congestion scenarios are illustrative, not calibrated. Several plan items changed after the proposal: we added the scaling experiment (RQ1b), dropped the "growing trips" workload and the full-network map layer when time was short, and added ALT, bidirectional search and Or-opt as late extensions that are not part of our research questions.

**Conclusion.** On a real, directed city network, our own A\* returned exactly Dijkstra's optimal costs on every tested query while expanding about 40% of the nodes, but this saved little time on a 2,000-node area; A\*'s clearest gains were on medium-length trips (per-pair speed-up up to 1.94 on the 4.5 km map), while only ALT, a stronger heuristic that needs preprocessing, clearly sped up long trips on the larger map (2.67). For delivery tours, NN + directed 2-opt is a cheap and usually near-optimal ordering, but it is a local search and can miss badly on asymmetric costs, which Held–Karp makes visible on small cases. Zonal congestion and closures change routes only where they apply, and the replanning machinery, including reporting when no complete tour exists, works within a few milliseconds. Natural next steps are calibrated speeds, turn restrictions, a better local search for the directed tour problem (for example Or-opt [Or 1976], which already fixes our demo case but was not part of our measurements), and repeating the timing study on more areas and machines.

## References

- Boeing, G. (2017). OSMnx: New methods for acquiring, constructing, analyzing, and visualizing complex street networks. *Computers, Environment and Urban Systems*, 65, 126–139.
- Croes, G. A. (1958). A method for solving traveling-salesman problems. *Operations Research*, 6(6), 791–812.
- Dijkstra, E. W. (1959). A note on two problems in connexion with graphs. *Numerische Mathematik*, 1, 269–271.
- Goldberg, A. V., & Harrelson, C. (2005). Computing the shortest path: A\* search meets graph theory. *Proceedings of the 16th ACM-SIAM Symposium on Discrete Algorithms (SODA)*, 156–165.
- Hart, P. E., Nilsson, N. J., & Raphael, B. (1968). A formal basis for the heuristic determination of minimum cost paths. *IEEE Transactions on Systems Science and Cybernetics*, 4(2), 100–107.
- Held, M., & Karp, R. M. (1962). A dynamic programming approach to sequencing problems. *Journal of the Society for Industrial and Applied Mathematics*, 10(1), 196–210.
- Or, I. (1976). *Traveling salesman-type combinatorial problems and their relation to the logistics of regional blood banking* (PhD thesis). Northwestern University.
- Pohl, I. (1971). Bi-directional search. In B. Meltzer & D. Michie (Eds.), *Machine Intelligence 6* (pp. 127–140). Edinburgh University Press.
- Russell, S., & Norvig, P. (2021). *Artificial Intelligence: A Modern Approach* (4th ed.). Pearson.
- OpenStreetMap contributors. (2026). Street network data, © OpenStreetMap contributors, licensed under ODbL. https://www.openstreetmap.org
