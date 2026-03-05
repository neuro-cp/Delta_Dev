from typing import Protocol, Dict, Any

class ExternalModelInterface(Protocol):
    def produce_output(self, input_payload: Dict[str, Any]) -> Dict[str, Any]:
        ...
