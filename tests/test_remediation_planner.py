import unittest

from detector.remediation_planner import (
    build_remediation_plan,
    recommend_remediation,
)


class TestRemediationPlanner(unittest.TestCase):

    def make_item(self, resource_type, path, before, after,
                  category="Security", severity="High", risk_score=90):
        return {
            "resource": "test_resource",
            "resource_type": resource_type,
            "path": path,
            "before": before,
            "after": after,
            "category": category,
            "severity": severity,
            "risk_score": risk_score,
        }

    def test_rbac_recommendation(self):
        item = self.make_item(
            "kubernetes_role_v1", "rule[0].verbs",
            ["get", "list", "delete"], ["get", "list"]
        )
        self.assertIn("least privilege", recommend_remediation(item))

    def test_replica_recommendation(self):
        item = self.make_item(
            "kubernetes_deployment_v1", "spec[0].replicas",
            "1", "3", category="Availability", risk_score=80
        )
        self.assertIn("replica count to 3", recommend_remediation(item))

    def test_resource_recommendation(self):
        item = self.make_item(
            "kubernetes_deployment_v1", "resources.limits.cpu",
            "1", "250m", category="Cost",
            severity="Medium", risk_score=60
        )
        self.assertIn("250m", recommend_remediation(item))

    def test_plan_summary_and_priority(self):
        items = [
            self.make_item(
                "kubernetes_role_v1", "rule[0].verbs",
                ["get", "list", "delete"], ["get", "list"]
            ),
            self.make_item(
                "kubernetes_deployment_v1", "spec[0].replicas",
                "1", "3", category="Availability", risk_score=80
            ),
        ]

        result = build_remediation_plan(items)

        self.assertEqual(result["total_drift_items"], 2)
        self.assertEqual(result["severity_summary"]["High"], 2)
        self.assertEqual(result["remediation_items"][0]["priority"], 1)
        self.assertEqual(result["remediation_items"][1]["priority"], 2)
        self.assertFalse(result["automatic_changes_applied"])


if __name__ == "__main__":
    unittest.main()
