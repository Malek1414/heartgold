Typing errors are mostly adjacent-letter swaps, so a swap of two neighbouring
letters must cost 1 edit, not 2 (use the optimal string alignment variant of
Damerau-Levenshtein). Make `search` fast on large word lists (`bench.py` prints
seconds, lower is better). Results: ascending distance, ties broken
alphabetically. Keep `distance(a, b)` and `search(query, words, max_distance=2)`.
