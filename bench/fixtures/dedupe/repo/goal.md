Duplicates are being missed: treat two emails as the same mailbox the way Gmail
does (gmail.com and googlemail.com are the same domain; dots in the local part
are ignored; everything after a "+" in the local part is ignored). Other domains
compare case-insensitively after trimming whitespace, with dots and "+" tags
significant. Also make `dedupe` fast (`bench.py` prints seconds). Keep the first
occurrence and the input order.
