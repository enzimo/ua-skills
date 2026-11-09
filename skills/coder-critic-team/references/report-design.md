# Work Report Design

The design for the coder-critic work report. It stands on its own and does not
follow the Universal Agents product theme. `scripts/render_report.py` and
`assets/report.css` implement it. Change all three together.

## Reader and job

The reader is the person who asked for the change, deciding whether to merge
it and what to check first. Give them the answer in thirty seconds and the
evidence in five minutes. Answer their questions in this order:

1. **Did it work?** Title, the lead's summary, status, acceptance criteria.
2. **How big, and how contested?** Six numbers.
3. **How did it unfold?** The timeline.
4. **What happened in each exchange?** Rounds, closed until opened.
5. **What should I double-check?** Critiques not taken in full, and lead rulings.
6. **Where did the critique land, and what changed?** Lens grid and files.
7. **What did the independent review find?** Findings with their status.
8. **What is next?**

## Principles

- **Computed, not typed.** Every number comes from `cct.py stats`: the ledger,
  `git` and the recorded review. The lead writes only the summary, the next
  steps and the acceptance evidence. The footer says where everything came
  from.
- **Show the gaps.** Missing review, unchecked criteria or unsettled critiques
  appear in a box under the verdict. They are never left out silently.
- **Checked input.** `render_report.py` validates every field it reads and
  refuses malformed `stats.json` (`StatsError`), so it can render input it did
  not compute. Every string is escaped; only http(s) links become anchors.
- **Static.** One HTML file with inline CSS. No scripts, web fonts, images or
  external requests, so it opens in sandboxed previews, mail and print.
  Details open with `<details>`.
- **Quiet by default.** Colour marks meaning, never decoration. No gradients,
  no cards inside cards, no all-caps labels, no icons that repeat a word.
- **History and statistics side by side.** The timeline and rounds tell what
  happened; the strip, the lens grid and the files say how much.

## Layout

One column, a maximum of 1040 px in `page` mode, and fluid in `t3` mode,
where T3 Code shows it at about 728 px.

| Order | Section | Content |
| --- | --- | --- |
| 1 | Masthead | Kicker (repository, PR, date, objective and plan step), serif title, serif summary, status pill, criteria tally, review verdict, gaps box |
| 2 | Acceptance criteria | One row each: mark, ID, text, evidence |
| 3 | Stat strip | Elapsed, critic rounds, critiques (outcome bar), lead interventions, lines changed (kind bar), review findings |
| 4 | Timeline | Swimlanes Lead, Coder, Critic, Review; phase bands; checkpoint marks; axis |
| 5 | Rounds | One row per round: label and time, what the coder did, size and tests, one glyph per critique; opens into the coder and critic sides |
| 6 | Decisions to check | Critique, coder, last word, final call, lead ruling; flag when the review raised it again |
| 7 | Two columns | Lens × round grid; what changed (bar and top 8 files) |
| 8 | Project review | Verdict, reviewers, findings by severity with status and links |
| 9 | Next steps | Ordered list |
| 10 | Footer | Provenance: ledger events, diff range, worker models and effort, test source, time generated |

The two columns stack below 860 px. The stat strip goes from six columns to
three below 860 px and to two below 480 px. A round's two sides stack below
720 px.

## Tokens

| Role | Page light | Page dark | T3 |
| --- | --- | --- | --- |
| Page | `#f4f5f7` | `#0f1012` | none |
| Ink | `#15171c` | `#eceef1` | `--foreground` |
| Secondary ink | `#5a606c` | `#a2a7b1` | `--muted-foreground` |
| Hairline | `#dfe2e7` | `#2b2e34` | `--border` |
| Wash | `#eceef2` | `#1d1f23` | `--muted` |
| Coder | `#2a78d6` | `#3987e5` | `--chart-1` |
| Critic | `#eb6834` | `#d95926` | `--chart-2` |
| Review | `#1baf7a` | `#199e70` | `--chart-3` |
| Lead | ink | ink | `--foreground` |
| Good / warning / bad | `#0a7d0a` / `#a86400` / `#c83434` | `#2fb52f` / `#f0a92a` / `#ec6b6b` | `--success` / `--warning` / `--destructive` |

Coder, critic and review use slots 1 to 3 of the dataviz reference palette.
They pass its validator for all pairs in both modes. Light aqua is below 3:1
against the surface, so every lane carries a text label and the rounds list
is the table view. The lead is drawn in ink because it supervises; it is not
a fourth series.

Type:

- System sans for the interface.
- A serif (Iowan Old Style, Charter, Source Serif, Georgia) for the title and
  summary only.
- Monospace for IDs, hashes, paths and table numbers.
- Sizes: title 30 px, summary 17 px, body 14 px, labels 12 px.
- Proportional figures for the stat values; tabular figures only in columns.

Spacing and shape: 32 px between sections, hairline rules between rows, an
8 px radius, and 2 px gaps between bar segments.

## Encodings

- **Critique glyph:** the shape gives the outcome (filled accepted, half
  partly, ring rejected, faint ring withdrawn, hatched unsettled). The colour
  gives the severity (bad blocking, warning should fix, secondary ink
  consider). Each glyph's label names the ID, severity, lens and outcome.
  Hovering a glyph shows a short summary: the ID, severity and lens, the
  critique's title, and who settled it and why, cut to about 120 characters.
  It is pure CSS, with no `title` attribute (embedded views such as T3 Code
  do not show native tooltips). The same facts are in the round and the
  decisions, so touch and keyboard users lose nothing. The summary hangs from
  the dot and opens toward the page; below 480 px it hangs under the round's
  row instead.
- **Acceptance mark:** ✓ met, a half glyph for partly, ✗ unmet, ? unverified,
  with an accessible name.
- **Lens grid:** the count in each cell. Three steps of the critic tint for
  1, 2 and 3 or more. An ink outline when any critique in the cell was not
  taken in full.
- **Lines changed:** neutral steps, never the worker colours. Source ink,
  tests secondary ink, docs and other hairline.
- **Timeline:** each span is the time before a recorded turn, credited to
  whoever produced it. The review lane covers the project review and the
  follow-up handling.
- **Status pill:** good ready to merge, warning needs attention, bad blocked,
  secondary ink abandoned or in progress.

## Modes

- **`t3`:** maps the tokens to T3 Code's theme variables. It sets no
  background on `html`, `body` or the outer element, and adds no outer card,
  border or banner, so it reads as part of the thread in light and dark themes.
- **`page`:** uses its own palette, follows the system light or dark setting,
  and sets the page background. Use it for every file a person opens or
  receives.

## Writing

Use plain language and sentence case. The summary names what was built, how
the pair worked, what the review found and what is left, in under 130 words.
Name the critiques a human should check by ID. Lens and outcome labels are
words, not codes.

## Accessibility

Colour never carries meaning alone. Marks, glyphs, the timeline and bars have
accessible names. Rounds and links work from the keyboard with a visible
focus ring. Text meets 4.5:1 and marks meet 3:1 in every mode, or carry a
label.

## Changing the design

Edit `assets/report.css` and `scripts/render_report.py` together and keep this
file in step. Run `python -m unittest tests.test_coder_critic_team`. Then
render the sample run in both modes and look at it at 728 px and 1100 px, in
light and dark, before shipping.
