# Experiment C publication-ready results and discussion

## Audited design

The analysis combines five paired training/generation seeds (17, 42, 202, 303, 907) under an identical data split, frozen verifier, 1,000-step training budget, model size, sampling budget, and target grid. Each arm generated 100 candidates at each of three targets per seed (3,000 candidates total). The inferential unit is the seed, not the individual generated candidate. Byte-identical train/test row files and the common source SHA-256 are recorded in `c1_five_seed_summary.json`.

## Results

Continuous conditioning increased the mean strict target-hit rate from 0.1587 to 0.1780, an absolute paired improvement of 0.0193 (95% t interval 0.0064 to 0.0322; paired t-test p=0.0141). All five paired seeds favored continuous conditioning. Because only five seeds were run, the distribution-free exact sign test remains borderline (two-sided p=0.0625); the t-test should therefore be treated as exploratory rather than definitive confirmatory evidence.

Target MAE decreased by 0.0609 log10 S cm^-1 (95% t interval -0.0728 to -0.0490). The continuous model was monotonic across the three requested targets in 5/5 seeds, with mean target-prediction correlation 0.991; the binary baseline was monotonic in 4/5 seeds with mean correlation 0.873.

This gain came with a chemical-yield tradeoff. Mean validity changed by -0.0673 (binary 0.5220, continuous 0.4547), and novelty changed by -0.0720 (binary 0.5033, continuous 0.4313). Most strict hits occur at the central -4 target; the -5 and -3 targets are poorly covered by the frozen verifier's training support. The primary effect therefore demonstrates improved offline target adherence within this benchmark, not validated discovery at the target extremes.

## Claim boundary

The strongest supported claim is: *under a fixed HTP-MD split and common frozen verifier, continuous conductivity conditioning reproducibly improves verifier-defined target adherence over binary high/low PolyGen across five paired seeds, while reducing valid and novel yield.* It does not establish experimental conductivity, salt/temperature controllability, or complete-system generation. Those require the separate formulation experiment and prospective MD or laboratory validation.
