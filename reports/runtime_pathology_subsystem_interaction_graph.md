# Runtime Pathology Subsystem Interaction Graph

## Subsystem Counts
```json
{
  "executive": 74,
  "kernel": 45,
  "knowledge": 86,
  "learning": 63,
  "other": 233,
  "reasoning": 65,
  "runtime": 47
}
```

## Edges
- {'source': 'executive', 'target': 'kernel', 'count': 1}
- {'source': 'executive', 'target': 'knowledge', 'count': 2}
- {'source': 'executive', 'target': 'learning', 'count': 2}
- {'source': 'executive', 'target': 'other', 'count': 128}
- {'source': 'executive', 'target': 'reasoning', 'count': 1}
- {'source': 'executive', 'target': 'runtime', 'count': 1}
- {'source': 'kernel', 'target': 'knowledge', 'count': 1}
- {'source': 'kernel', 'target': 'learning', 'count': 3}
- {'source': 'kernel', 'target': 'other', 'count': 72}
- {'source': 'knowledge', 'target': 'learning', 'count': 4}
- {'source': 'knowledge', 'target': 'other', 'count': 127}
- {'source': 'learning', 'target': 'knowledge', 'count': 9}
- {'source': 'learning', 'target': 'other', 'count': 76}
- {'source': 'learning', 'target': 'runtime', 'count': 1}
- {'source': 'other', 'target': 'executive', 'count': 1}
- {'source': 'other', 'target': 'knowledge', 'count': 20}
- {'source': 'other', 'target': 'learning', 'count': 5}
- {'source': 'other', 'target': 'reasoning', 'count': 1}
- {'source': 'other', 'target': 'runtime', 'count': 4}
- {'source': 'reasoning', 'target': 'other', 'count': 124}
- {'source': 'runtime', 'target': 'executive', 'count': 1}
- {'source': 'runtime', 'target': 'knowledge', 'count': 3}
- {'source': 'runtime', 'target': 'other', 'count': 84}
- {'source': 'runtime', 'target': 'reasoning', 'count': 1}
