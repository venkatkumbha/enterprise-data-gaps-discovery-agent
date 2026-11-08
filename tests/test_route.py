"""The supervisor's routing is the control-flow contract. It does not need LangGraph."""

import unittest

from gap_agent.graph.workflow import route


class RouteTests(unittest.TestCase):
    def test_starts_with_schema(self) -> None:
        self.assertEqual(route({}), "schema_explorer")

    def test_profiles_after_schema(self) -> None:
        self.assertEqual(route({"schema_done": True}), "profiler")

    def test_reconciles_after_profile(self) -> None:
        self.assertEqual(
            route({"schema_done": True, "profile_done": True}),
            "reconciliation",
        )

    def test_reports_last(self) -> None:
        self.assertEqual(
            route({"schema_done": True, "profile_done": True, "reconcile_done": True}),
            "reporter",
        )

    def test_blocked_run_skips_to_the_reporter(self) -> None:
        self.assertEqual(route({"blocked": True, "schema_done": True}), "reporter")


if __name__ == "__main__":
    unittest.main()
