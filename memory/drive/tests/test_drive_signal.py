from memory.drive.drive_signal import DriveSignal


def test_drive_signal_is_immutable() -> None:
    signal = DriveSignal(
        key="novelty",
        magnitude=0.5,
        created_step=0,
        source="test",
    )

    try:
        signal.magnitude = 1.0  # type: ignore
        assert False, "DriveSignal should be immutable"
    except Exception:
        pass
