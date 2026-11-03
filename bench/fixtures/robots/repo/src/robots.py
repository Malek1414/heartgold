"""robots.txt checker for our crawler."""


def can_fetch(robots_txt, user_agent, path):
    """May `user_agent` crawl `path` (path + optional query) under `robots_txt`?"""
    applies = False
    for line in robots_txt.splitlines():
        key, _, value = line.partition(":")
        key, value = key.strip().lower(), value.strip()
        if key == "user-agent":
            applies = value == "*" or value == user_agent
        elif applies and key == "disallow" and value and path.startswith(value):
            return False
    return True
