`resolve(base, ref)` must implement URI reference resolution exactly as RFC 3986
section 5 specifies (strict parser), including remove_dot_segments, empty
references, query-only and fragment-only references, network-path references,
and the "normal" and "abnormal" examples the RFC lists. Do not normalize case
or percent-encoding beyond what section 5 requires. Standard library only, and
do not use urllib.
