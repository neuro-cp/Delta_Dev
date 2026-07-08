# Runtime Pathology Subsystem Interaction Graph

## Subsystem Counts
```json
{
  "executive": 75,
  "kernel": 46,
  "knowledge": 88,
  "learning": 67,
  "other": 270,
  "reasoning": 66,
  "runtime": 49
}
```

## Edges
- {'source': 'executive', 'target': 'kernel', 'count': 1}
- {'source': 'executive', 'target': 'knowledge', 'count': 2}
- {'source': 'executive', 'target': 'learning', 'count': 2}
- {'source': 'executive', 'target': 'other', 'count': 130}
- {'source': 'executive', 'target': 'reasoning', 'count': 1}
- {'source': 'executive', 'target': 'runtime', 'count': 1}
- {'source': 'kernel', 'target': 'knowledge', 'count': 1}
- {'source': 'kernel', 'target': 'learning', 'count': 4}
- {'source': 'kernel', 'target': 'other', 'count': 72}
- {'source': 'knowledge', 'target': 'learning', 'count': 4}
- {'source': 'knowledge', 'target': 'other', 'count': 127}
- {'source': 'learning', 'target': 'kernel', 'count': 6}
- {'source': 'learning', 'target': 'knowledge', 'count': 9}
- {'source': 'learning', 'target': 'other', 'count': 79}
- {'source': 'learning', 'target': 'runtime', 'count': 1}
- {'source': 'other', 'target': 'executive', 'count': 2}
- {'source': 'other', 'target': 'kernel', 'count': 4}
- {'source': 'other', 'target': 'knowledge', 'count': 24}
- {'source': 'other', 'target': 'learning', 'count': 13}
- {'source': 'other', 'target': 'reasoning', 'count': 5}
- {'source': 'other', 'target': 'runtime', 'count': 8}
- {'source': 'reasoning', 'target': 'other', 'count': 126}
- {'source': 'runtime', 'target': 'executive', 'count': 1}
- {'source': 'runtime', 'target': 'knowledge', 'count': 4}
- {'source': 'runtime', 'target': 'learning', 'count': 1}
- {'source': 'runtime', 'target': 'other', 'count': 86}
- {'source': 'runtime', 'target': 'reasoning', 'count': 1}
