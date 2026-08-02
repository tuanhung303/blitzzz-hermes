import logging
from unittest.mock import patch

from run_agent import AIAgent


def test_memory_load_failure_does_not_install_partial_store(monkeypatch, tmp_path, caplog):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "hm"))
    config = {
        "memory": {
            "memory_enabled": True,
            "user_profile_enabled": True,
        }
    }

    with (
        patch("hermes_cli.config.load_config_readonly", return_value=config),
        patch("run_agent.get_tool_definitions", return_value=[]),
        patch("run_agent.check_toolset_requirements", return_value={}),
        patch("run_agent.OpenAI"),
        patch(
            "tools.memory_tool.MemoryStore.load_from_disk",
            side_effect=OSError("memory read failed"),
        ) as load_from_disk,
        caplog.at_level(logging.WARNING, logger="run_agent"),
    ):
        agent = AIAgent(
            api_key="test-key-1234567890",
            base_url="https://openrouter.ai/api/v1",
            quiet_mode=True,
            skip_context_files=True,
        )

    assert load_from_disk.call_count == 1
    assert agent._memory_store is None
    assert agent._memory_enabled is False
    assert agent._user_profile_enabled is False
    assert "Built-in memory initialization failed" in caplog.text
    assert "memory read failed" not in caplog.text
