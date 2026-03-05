from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass(frozen=True)
class StructuredCognitiveSignal:
    semantic_tokens: List[str]
    quantitative_fields: Dict[str, float]
    role: str
    mode: str
    confidence: Optional[float] = None
