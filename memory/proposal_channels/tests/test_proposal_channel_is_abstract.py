from __future__ import annotations

import pytest

from memory.proposal_channels.proposal_channel import ProposalChannel


def test_proposal_channel_is_abstract() -> None:
    with pytest.raises(TypeError):
        ProposalChannel()  # type: ignore[abstract]
