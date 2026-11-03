def normalize(email):
    e = email.strip()
    local, sep, domain = e.rpartition("@")
    if not sep:
        return e.lower()
    domain = domain.lower()
    if domain in ("gmail.com", "googlemail.com"):
        local = local.lower().split("+", 1)[0].replace(".", "")
        domain = "gmail.com"
    else:
        local = local.lower()
    return f"{local}@{domain}"


def dedupe(records):
    seen, out = set(), []
    for r in records:
        k = normalize(r["email"])
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out
