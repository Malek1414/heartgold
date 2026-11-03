"""Resolve links found on crawled pages."""


def resolve(base, ref):
    """Resolve URI reference `ref` against absolute URI `base`."""
    if "://" in ref:
        return ref
    if ref.startswith("/"):
        scheme, rest = base.split("://", 1)
        return scheme + "://" + rest.split("/", 1)[0] + ref
    return base.rsplit("/", 1)[0] + "/" + ref
