import asyncio
import logging
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, Mock

from discord import Guild
import pytest

from hawking.core.modules.audio_player.audio_player_cog import ServerStateManager


@pytest.fixture
def server_state():
    state = object.__new__(ServerStateManager)
    state.logger = logging.getLogger(__name__)
    state.guild = cast(Guild, SimpleNamespace(name="test guild"))
    state.can_bot_connect_to_channel = lambda channel: True
    state.can_bot_speak_in_channel = lambda channel: True
    return state


def test_reconnects_after_cached_voice_client_was_disconnected(server_state):
    # Arrange
    disconnect_key = "disconnect"
    connect_key = "connect"
    events = []
    fresh_client = object()

    async def disconnect(**kwargs):
        events.append(disconnect_key)

    async def connect():
        events.append(connect_key)
        return fresh_client

    stale_client = SimpleNamespace(
        is_connected=Mock(return_value=False),
        disconnect=AsyncMock(side_effect=disconnect),
    )
    channel = SimpleNamespace(connect=AsyncMock(side_effect=connect))
    server_state.voice_client = stale_client

    # Act
    result = asyncio.run(server_state.get_voice_client(channel))

    # Assert
    assert result is fresh_client
    assert server_state.voice_client is None
    stale_client.disconnect.assert_awaited_once_with(force=False)
    channel.connect.assert_awaited_once_with()
    assert events == [disconnect_key, connect_key]


def test_cleans_audio_source_when_playback_start_fails(server_state):
    # Arrange
    disconnect_key = "disconnect"
    source = SimpleNamespace(cleanup=Mock())
    server_state.voice_client = SimpleNamespace(play=Mock(side_effect=RuntimeError(disconnect_key)))

    # Act
    with pytest.raises(RuntimeError) as raised:
        server_state.start_audio_playback(source, after=lambda error: None)

    # Assert
    assert str(raised.value) == disconnect_key
    source.cleanup.assert_called_once_with()