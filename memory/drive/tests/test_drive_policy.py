from memory.drive.drive_signal import DriveSignal
from memory.drive.drive_policy import DrivePolicy


def test_drive_decay_reduces_magnitude() -> None:
    policy = DrivePolicy(
        decay_rate=0.5,
        min_magnitude=0.0,
        max_magnitude=1.0,
    )

    s = DriveSignal("a", 1.0, 0)
    decayed = policy.decay(s, current_step=2)

    assert decayed.magnitude < s.magnitude


def test_drive_normalization() -> None:
    policy = DrivePolicy(
        decay_rate=1.0,
        min_magnitude=0.0,
        max_magnitude=1.0,
    )

    signals = [
        DriveSignal("a", 1.0, 0),
        DriveSignal("b", 1.0, 0),
    ]

    normed = policy.normalize(signals)
    total = sum(s.magnitude for s in normed)

    assert abs(total - 1.0) < 1e-6
