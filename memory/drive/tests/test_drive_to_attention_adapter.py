from memory.drive.drive_signal import DriveSignal
from memory.drive.drive_policy import DrivePolicy
from memory.drive.drive_field import DriveField
from memory.drive.drive_to_attention_adapter import DriveToAttentionAdapter


def test_drive_to_attention_bias() -> None:
    policy = DrivePolicy(
        decay_rate=1.0,
        min_magnitude=0.0,
        max_magnitude=1.0,
    )

    field = DriveField(policy=policy)
    field.ingest([
        DriveSignal("novelty", 0.5, 0),
    ])

    adapter = DriveToAttentionAdapter(field=field)
    bias = adapter.compute_gain_bias()

    assert bias["novelty"] == 1.5
