from memory.drive.drive_signal import DriveSignal
from memory.drive.drive_policy import DrivePolicy
from memory.drive.drive_field import DriveField


def test_drive_field_ingest_and_step() -> None:
    policy = DrivePolicy(
        decay_rate=0.5,
        min_magnitude=0.0,
        max_magnitude=1.0,
    )

    field = DriveField(policy=policy)

    field.ingest([
        DriveSignal("a", 1.0, 0),
        DriveSignal("b", 0.5, 0),
    ])

    field.step(current_step=2)

    signals = field.signals()
    assert len(signals) == 2
    assert all(s.magnitude <= 1.0 for s in signals)
