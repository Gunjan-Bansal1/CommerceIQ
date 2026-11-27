# CommerceIQ — Statistical Findings Report (Phase 10)

All hypotheses were tested using assumption-checked parametric and non-parametric methods with **Holm-Bonferroni** family-wise error correction.

| Hypothesis | Method | Sample | Statistic | Raw p-value | Holm Adj. p | Effect Size |
|---|---|---|---|---:|---:|---|
| H1: Late delivery vs review score | Mann-Whitney U + Welch t-test | 89,443 vs 6,381 | U=467,426,830; t=100.74 | 0.00e+00 | 0.00e+00 | Cohen d=1.710; r=0.638 |
| H2: Delivery duration across top 8 categories | Kruskal-Wallis H | 52,829 (8 groups) | H=494.92 | 9.92e-103 | 1.98e-102 | epsilon^2=0.0092 |
| H3a: Regional freight ratio differences | Kruskal-Wallis H | 94,724 (5 regions) | H=2,745.9 | 0.00e+00 | 0.00e+00 | epsilon^2=0.0289 |
| H3b: Distance vs delivery duration | Spearman rank correlation | 94,724 | rho=0.5433 | 0.00e+00 | 0.00e+00 | rho=0.5433 |
| H4: Channel vs lead conversion rate | Chi-square test of independence | 7,607 (top 7 channels) | chi2=112.22 | 6.99e-22 | 6.99e-22 | Cramer V=0.1215 |
| H5: Installments vs credit card payment value | Spearman rank correlation | 76,795 | rho=0.4776 | 0.00e+00 | 0.00e+00 | rho=0.4776 |

## Practical Interpretations & Limitations
- **H1 (Late Delivery -> Satisfaction):** On-time/early orders average **4.29** vs. **2.27** for late orders (diff **2.02** stars, 95% CI [1.98, 2.06], large Cohen d=**1.71**). This is the single largest operational effect size observed.
- **H2 (Category Delivery Duration):** Statistically significant (Kruskal-Wallis p=9.92e-103), yet small practical effect size (epsilon^2=0.0092) — route distance matters far more than product category.
- **H3 (Geography & Distance):** Distance strongly correlates with delivery duration (Spearman rho=0.543) and freight cost (rho=0.593).
- **H4 (Marketing Channels):** Conversion varies modestly across channels (Cramer V=0.121); `unknown` and `paid_search`/`organic_search` differ significantly from `display`/`email`.
- **H5 (Installments):** Higher-value purchases strongly correlate with more credit card installments (Spearman rho=0.478).
- **Limitation:** All findings reflect historical observational associations (2016–2018), not randomized causal experiments.
