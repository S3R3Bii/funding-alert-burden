# Funding-rate alert burden and persistence

Declared before retaining the study snapshot or examining model results, 28 October 2026. A schema-only source check established that the public API supplies effectiveDate, percentRate and revisionIndicator; no model or outcome comparison was performed.

## Decision

Does calendar adjustment help a monitoring rule distinguish a short disturbance from a persistent change in the SOFR–EFFR spread without overwhelming a review queue? The question concerns retrospective monitoring design. No trading, profitability, investment or live-vintage-performance claim is made.

## Source and information boundary

Retrieve New York Fed SOFR and EFFR records for 2018-04-02 through 2026-09-30 from the public Markets API. Preserve original JSON, query, retrieval time and hashes. Retain New York Fed copyright/source identifiers, source titles, attribution, reuse terms and explicit labeling of all derived material. No endorsement is implied. The official terms permit automated access, copying and derivatives subject to their conditions.

Join rates only on identical effective dates, with duplicate rejection and unmatched-date accounting. Analyze the spread in basis points: 100 × (SOFR percentage rate − EFFR percentage rate). This uses the current historical snapshot, which can contain revisions. It does not reconstruct the values available at the initial intraday publication. Publication-day triage is considered only after both rates and any same-day revision; the data still cannot prove historical real-time availability. Retain revision flags and report the limitation beside results.

## Split and score

Fit/initialize on 2018–2021; select on 2022–2023; protect 2024–2026Q3 for final evaluation after a committed selection artifact. At each effective date, calculations use the current spread for triage and earlier observations for centers, scales and calendar effects. The calendar flag identifies the last observed rate date of a calendar month, its previous observed date and the next observed date. Derive this flag from calendar dates, not rate outcomes; its knowledge assumes the official business-day sequence, with no claim to handle unannounced closures prospectively.

Compare 18 fixed configurations: trailing windows 30/60/120 observations, EWMA alpha .1/.3/.6, calendar adjustment off/on. For a given date, robust center and scale use prior observations only. Scale is 1.4826 × median absolute deviation, floored at 1 basis point to avoid division by a nearly constant spread. Calendar adjustment subtracts the difference between the historical median month-end-window spread and the historical ordinary-day median, using up to 756 preceding observations, requiring at least 10 in each group. Otherwise apply no calendar adjustment. Robust windows operate on the calendar-adjusted historical/current sequence.

EWMA of signed standardized deviations starts at zero and updates in date order. A persistent alert requires two successive absolute EWMA scores above a threshold. It is a review flag, not a crisis label or a validated false positive.

## Budget calibration and controlled stress experiment

For each candidate, select from fixed score thresholds .5, 1, 1.5, 2, 3, 4, 6 and 8 on the unmodified validation period. Choose the smallest threshold whose persistent-alert rate is at most 1%; if none meets it, use an infinite threshold and issue no alerts. This is an alert-burden budget on unlabeled history, not a measured economic false-positive rate.

Validation stress starts are every 40th eligible observation, starting at index 20, leaving seven observations to measure outcomes. For each start, separately add +10 basis points to SOFR alone for one observation (transient) or five observations (persistent), leaving EFFR unchanged. Recompute the monitor from the beginning with that single intervention, including its adaptation to earlier injected observations. An intervention is detected if a persistent alert occurs from the start through six observations afterward. Report detection delay from start, missed persistent interventions and transient persistent-call rate.

Select candidate/threshold by maximum (persistent detection fraction − transient persistent-call fraction), then lower unmodified alert rate, then candidate name. Keep every outcome, threshold trial and runtime. The fixed comparator is window60/alpha.3/no calendar adjustment with its own validation-calibrated threshold. No additional search is opened after test results are seen.

Apply frozen policies to the protected test interval, using prior history for adaptive centers and scales. Repeat the exact prespecified intervention design on test starts. Export day-level scores, centers, scales, calendar correction, flags and intervention-level detection/delay. These interventions are synthetic scenarios on measured aggregates, not historical labels of financial stress. Use paired intervention differences and report exact denominators; any uncertainty calculation must acknowledge shared history and overlapping adaptive windows. No independent-case confidence interval will be claimed for these dependent simulated cases.

## Acceptance

Source hashes, units, date joins, duplicate/unmatched accounting and forward-only feature times reconcile. Independent calculations reproduce monitor scores, threshold selection, alerts and intervention summaries. Retain contract tests for future-input independence, isolated versus sustained threshold crossings, joins and basis-point units. Render source-backed figures and a private manuscript. Public files must meet attribution, privacy and manuscript-exclusion gates. A failed budget, weak discrimination or unchanged baseline is a reportable result, not a reason to hide trials.
