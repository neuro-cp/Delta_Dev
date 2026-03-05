from memory.drive.drive_signal import DriveSignal
from memory.drive.drive_policy import DrivePolicy
from memory.drive.drive_field import DriveField
from memory.drive.drive_to_working_memory_adapter import (
    DriveToWorkingMemoryAdapter,
)


def test_drive_to_working_memory_decay_bias() -> None:
    policy = DrivePolicy(
        decay_rate=1.0,
        min_magnitude=0.0,
        max_magnitude=1.0,
    )

    field = DriveField(policy=policy)
    field.ingest([
        DriveSignal("fatigue", 0.3, 0),
    ])

    adapter = DriveToWorkingMemoryAdapter(field=field)
    bias = adapter.compute_decay_bias()

    assert abs(bias["fatigue"] - 0.7) < 1e-6
