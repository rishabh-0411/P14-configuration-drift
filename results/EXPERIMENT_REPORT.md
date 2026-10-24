# P14: Risk-Ranked Detection and Remediation of Configuration Drift in Infrastructure as Code

## 1. Objective

Evaluate a rule-based risk-ranking approach for semantic configuration drift in Terraform-managed Kubernetes resources. The approach ranks detected drift items by risk and generates remediation recommendations without applying changes automatically.

## 2. Experimental Setup

- Infrastructure: Kubernetes running on Minikube.
- Infrastructure as Code: Terraform.
- Drift detection: Terraform plan JSON processed by the project's Python detector.
- Ranking: Terraform plan ordering baseline compared with the proposed rule-based risk ranker.
- Labels: Manually labelled drift corpus in `drift_corpus/drift_dataset.csv`.
- Metrics: Precision@5, Precision@10, and mean rank of dangerous drift items.
- Dangerous items: Items labelled High or Critical severity.
- Remediation: Recommendations are generated for review; automatic application is disabled.

## 3. Scenario Results

| Scenario | Semantic drift items | Dangerous items | Baseline P@5 | Proposed P@5 | Baseline P@10 | Proposed P@10 | Baseline mean dangerous rank | Proposed mean dangerous rank |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Mixed | 11 | 4 | 0.20 | 0.80 | 0.30 | 0.40 | 8.25 | 2.50 |
| Security-focused | 2 | 2 | 1.00 | 1.00 | 1.00 | 1.00 | 1.50 | 1.50 |
| Availability-focused | 1 | 1 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

### Interpretation

The mixed scenario shows the largest observed difference. Precision@5 increases from 0.20 to 0.80, while mean dangerous rank decreases from 8.25 to 2.50.

The security-focused and availability-focused scenarios contain too few items to distinguish the ranking methods. Both methods rank all dangerous items first in these scenarios.

These results are exploratory and do not establish that the proposed ranking generalizes to unseen infrastructure workloads.

## 4. Ablation Study

Results from the mixed scenario:

| Configuration | Precision@5 |
|---|---:|
| Terraform baseline | 0.20 |
| Full risk ranking | 0.80 |
| Without security priority | 0.40 |
| Without availability priority | 0.60 |
| Equal category weights | 0.20 |

### Interpretation

The full configuration achieved the highest Precision@5 on this corpus. Removing security priority reduced Precision@5 by 0.40, and removing availability priority reduced it by 0.20. Equal category weights produced the same Precision@5 as the baseline.

This is evidence of sensitivity to the ranking rules on the current corpus, not proof of statistical significance or generalization.

## 5. Random-Ordering Analysis

The workload evaluation uses 1,000 seeded random permutations for each non-empty profile.

| Profile | Items | Random P@5 mean | Random P@5 SD | Empirical 95% permutation interval |
|---|---:|---:|---:|---|
| Security-focused | 2 | 1.000 | 0.000 | [1.000, 1.000] |
| Availability-cost-focused | 7 | 0.283 | 0.114 | [0.000, 0.400] |
| Mixed | 11 | 0.369 | 0.170 | [0.000, 0.600] |

The intervals are the empirical 2.5th and 97.5th percentiles of random permutations. They describe variation in random ordering on the selected items. They are not confidence intervals for the proposed method's performance on unseen workloads.

The security-focused profile contains only two dangerous items, so every permutation has Precision@5 equal to 1.00.

## 6. Remediation Planning

The remediation planner generates prioritized recommendations containing the resource, affected attribute, live value, desired value, severity, and suggested action.

For the saved security scenario, the recommendations restore the Role verbs to `get` and `list` and restore the Service type to `ClusterIP`.

For the availability scenario, the recommendation restores the Deployment replica count from 1 to the declared value of 3.

Recommendations are not automatically applied. This preserves operator control over infrastructure changes.

## 7. Threats to Validity and Limitations

1. **Small corpus:** The labelled corpus contains 11 semantic drift items. The security and availability scenarios contain only two and one item, respectively.
2. **Scenario dependence:** The scenarios are constructed from the same project and labelled corpus; they are not independent benchmark datasets.
3. **Manual labels:** The labels are manually assigned. Independent annotator agreement has not been measured.
4. **Deterministic rankings:** The baseline and proposed ranking each produce one ordering for a given saved plan. Re-running the same deterministic configuration does not create independent experimental observations.
5. **Random permutations:** The 1,000 random permutations measure ordering variability, not infrastructure-run variability or generalization uncertainty.
6. **Synthetic drift:** The experiments use controlled Kubernetes drift and do not establish performance across diverse production systems.
7. **Rule-based method:** The proposed approach uses explicit risk rules and scores; it is not a trained machine-learning model.

## 8. Conclusion

In the mixed scenario, the proposed rule-based ranking placed dangerous drift items higher than the Terraform ordering baseline, improving Precision@5 from 0.20 to 0.80 and reducing mean dangerous rank from 8.25 to 2.50.

The smaller focused scenarios demonstrated detection and ranking functionality but did not distinguish the methods. The ablation results suggest that security and availability priorities influence ranking performance on the current corpus.

Further evaluation should use a larger labelled corpus, independently constructed infrastructure scenarios, and independent label validation. Any claims about generalization should be withheld until that evaluation is performed.
