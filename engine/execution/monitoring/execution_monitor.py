from engine.execution.enablement.execution_enablement_controller import ExecutionEnablementController
from engine.execution.execution_target import ExecutionTarget

class ExecutionMonitor:
    def __init__(self, controller: ExecutionEnablementController):
        self._controller = controller

    def step(self):
        # delegate to controller expiration logic
        return self._controller.step()
