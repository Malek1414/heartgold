Make `within(query, words, k)` as fast as possible for large word lists
(100k+ words, small k) without changing its results. Pure Python standard
library only (no C extensions). Each call may get a different word list, so
do not rely on caching between calls. `bench.py` prints seconds; lower is
better. Speed is the only goal; results must stay identical.
