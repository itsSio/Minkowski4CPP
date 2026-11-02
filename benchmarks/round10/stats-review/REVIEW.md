# Independent review of exploratory paired uncertainty

Result: all 15 rows reproduce exactly. The independent checker verified the
three frozen input SHA256 identities, exact expected cohort and pair cardinality,
paired win/tie counts, every ratio-of-medians point estimate, and every 20,000-draw
percentile interval using its recorded random seed. It enumerated all possible
sign assignments for each observed row, and exhaustively checked the production
sign formula for every win/loss combination with effective sample size 0-12.
No source, raw trial, or previously published point estimate was changed.

The resampling unit is the whole process-level A/B pair. The same sampled index
selects both arms, so within-pair dependence is retained. The statistic is
100*(median(B)/median(A)-1), recomputed from the resampled pairs. This is a ratio
of marginal medians, not the median of per-pair percentage differences. The
linear interpolation used for the 2.5% and 97.5% quantiles is consistent with a
standard percentile-bootstrap interval. Seeds are fully reproducible for the
recorded row order; reordering or inserting rows changes later seeds, so retain
the per-row recorded seeds in any portable implementation.

The exact two-sided sign formula correctly excludes exact ties, doubles the
smaller Binomial(n, 0.5) tail and caps at one. All observed rows have zero ties.
The sign test concerns whether either arm is more likely to be lower within a
pair; it does not directly test the ratio-of-medians estimand. Its null assumes
independent, fair signs. Likewise, ordinary paired bootstrap resampling treats
pair blocks as sufficiently independent and representative. Alternating arm
order, serial dependence and nonstationary background load may violate these
assumptions. The percentile intervals are particularly fragile with six pairs
and must not be represented as validated coverage guarantees under these loads.

The scientific wording already labels the analysis exploratory, preserves prior
results, discloses small cohorts and background load, and explicitly identifies
p-values as unadjusted. That is appropriate. Recommend adding the two points
above about bootstrap independence and the different sign-test target, and
avoiding "statistically significant" or confirmatory language for any row.
There are 15 inspected workloads/metrics, chosen after existing benchmarks;
unadjusted p-values and intervals are descriptive aids, not fresh confirmation.

The stated interpretation is supported by the frozen observations: both warm
CenterSampled intervals lie below zero; both warm VolumeWeighted intervals cross
zero; row-groups and sparse Gaussian kernel intervals lie below zero; dense
crosses zero at +0.19%; both real training intervals cross zero. Describe the
dense result as a negative point estimate with unresolved direction, and keep
the real-training conclusion inconclusive. None establishes universal behavior
or an end-to-end training advantage.

For a portable rerun, fail closed on the exact 15-row workload set and expected
unique round/arm keys before calculating statistics. The current inputs satisfy
those conditions, verified independently here. Freeze input hashes and per-row
seeds alongside outputs, and retain all original benchmark findings when adding
this supplement to PR comments.

Artifacts: `independent-review.py` and `independent-review.json` in this directory.
