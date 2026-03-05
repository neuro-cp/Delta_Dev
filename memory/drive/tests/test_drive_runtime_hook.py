from memory.drive.drive_signal import DriveSignal
from memory.drive.drive_policy import DrivePolicy
from memory.drive.drive_field import DriveField
from memory.drive.drive_runtime_hook import DriveRuntimeHook


def test_drive_runtime_snapshot() -> None:
    policy = DrivePolicy(
        decay_rate=1.0,
        min_magnitude=0.0,
        max_magnitude=1.0,
    )

    field = DriveField(policy=policy)
    field.ingest([
        DriveSignal("urgency", 0.8, 0),
    ])

    hook = DriveRuntimeHook(field=field)
    snap = hook.snapshot()

    assert snap["count"] == 1
    assert snap["signals"]["urgency"] == 0.8
