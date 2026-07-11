# Module Attachment Guide

Modules require a manifest with declared inputs, outputs, permissions, side
effects, rollback strategy, and operator ownership. Prohibited permissions such
as provider calls, network calls, production writes, automatic commit/push,
deployment, hidden persistence, and DELTA-75 access are denied.
