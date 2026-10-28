-- Identical effective dates only; no interpolation of missing source records.
SELECT s.effective_date,
       s.rate AS sofr_percent, e.rate AS effr_percent,
       100.0 * (s.rate - e.rate) AS spread_bps,
       s.revision AS sofr_revision, e.revision AS effr_revision
FROM sofr AS s INNER JOIN effr AS e USING (effective_date)
ORDER BY s.effective_date;
