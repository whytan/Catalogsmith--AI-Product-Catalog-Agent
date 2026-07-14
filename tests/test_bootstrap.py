from agent.bootstrap import ensure_agent_importable, project_root


def test_ensure_agent_importable_from_checkout():
    ensure_agent_importable()
    import agent

    assert (project_root() / "src" / "agent").exists()
    assert agent.__file__ is not None
