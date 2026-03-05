# Semantic → Assembly Hypothesis Invariants

These rules are binding.

## Authority
- No runtime access
- No routing, salience, value, urgency, or decision access
- No learning or replay access

## Semantics
- Hypotheses reference promoted semantics only
- No raw or candidate semantics allowed

## Assemblies
- Assemblies are symbolic identifiers only
- No validation against runtime or loader
- No population, neuron, or gain references

## Structure
- One region per hypothesis
- No cross-region assembly hypotheses
- No numeric fields of any kind

## Behavior
- Hypotheses do not act
- Hypotheses do not bias
- Hypotheses do not compete
- Hypotheses do not decay

## Removal Safety
Removing all semantic assembly hypotheses must result in:
- Identical runtime behavior
- Identical learning behavior
- Identical decision behavior

Only inspection output may differ by absence.
