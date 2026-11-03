from src.robots import can_fetch


def test_disallow_prefix():
    assert can_fetch("User-agent: *\nDisallow: /private\n", "Bot", "/private/x") is False
    assert can_fetch("User-agent: *\nDisallow: /private\n", "Bot", "/public") is True
