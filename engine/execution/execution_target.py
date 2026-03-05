from enum import Enum, auto


class ExecutionTarget(Enum):
    VALUE_BIAS = auto()
    URGENCY_RELIEF = auto()
    SALIENCE_GAIN = auto()
    ROUTING_GAIN = auto()
    PFC_CONTEXT_GAIN = auto()
    DECISION_FX_GAIN = auto()
    DECISION_BIAS = auto()