# DELTA Historical Concept Review

## Attention Latch

Status: partially subsumed.

The current cognitive-substrate path implements the intent through:

- Attention Region
- attention rankings
- per-cycle Working Memory
- advisory context forwarded into reasoning
- Reflection inspection before Working Memory disappears

What is missing is a true global workspace or blackboard where every region can
publish temporary tick-local state. The old latch work in the repository mostly
appears in the older biological/runtime and testing areas as decision-latch
mechanics, not as the canonical cognitive-substrate attention path.

Recommendation: do not recreate `Attention Latch` as a separate legacy class.
Add a Global Workspace region when multiple regions need a shared tick-local
integration surface.

## Memory Matrix

Status: expanded into layered memory architecture.

The current equivalent is the graph formed by:

- Experience Memory
- Relationships
- Learning Records
- Semantic Knowledge
- Working Memory
- Reflection
- Simulation
- Agency

This is stronger than one monolithic matrix, but it still lacks a canonical
global context object that ties all active memory contributions together during
one tick.

Recommendation: preserve layered memory. Add explicit cross-region workspace
views instead of collapsing memory back into a single matrix.

## Regional Activity

Status: mostly implemented.

The project now has independent cooperating regions for attention, working
memory, reflection, learning, knowledge, simulation, self-model, goals,
planning, decision, and agency.

Remaining gap: runtime scheduling and global workspace coordination are still
early. Regions exist, but they do not yet all publish to a shared tick-local
workspace.

## Bottom Line

The historical ideas were not discarded. Most were translated into cleaner
interfaces. The unique missing behavior is Global Workspace: a temporary,
tick-local integration surface between attention, memory, goals, prediction,
simulation, reflection, planning, decision, and agency.
