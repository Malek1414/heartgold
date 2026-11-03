`break_opportunities(text)` must return exactly the line-break opportunities
defined by the Unicode Line Breaking Algorithm (UAX #14) for Unicode 16.0.0,
default rules (LB1-LB31, with the standard tailoring-free resolution of
AI/SG/XX/SA/CJ classes), as exercised by the official LineBreakTest.txt.
Index i means a break is allowed before text[i]; len(text) is always included
for non-empty text (mandatory end of text). Standard library only, no network
at runtime; vendoring data files into the repo is fine.
