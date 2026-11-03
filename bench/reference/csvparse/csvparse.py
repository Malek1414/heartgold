def parse(text):
    rows, row, field, i, n = [], [], [], 0, len(text)
    quoted = False
    if not text:
        return []
    while i < n:
        ch = text[i]
        if quoted:
            if ch == '"':
                if i + 1 < n and text[i + 1] == '"':
                    field.append('"'); i += 2; continue
                quoted = False; i += 1; continue
            field.append(ch); i += 1; continue
        if ch == '"' and not field:
            quoted = True; i += 1; continue
        if ch == ",":
            row.append("".join(field)); field = []; i += 1; continue
        if ch == "\r" and i + 1 < n and text[i + 1] == "\n":
            row.append("".join(field)); rows.append(row); row, field = [], []; i += 2; continue
        if ch == "\n":
            row.append("".join(field)); rows.append(row); row, field = [], []; i += 1; continue
        field.append(ch); i += 1
    if field or row:
        row.append("".join(field)); rows.append(row)
    return rows
