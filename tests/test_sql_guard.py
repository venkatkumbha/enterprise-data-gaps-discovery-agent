"""The read-only contract is the security boundary. These cases pin it down."""

import unittest

from gap_agent.mcp.sql_guard import (
    MAX_ROW_LIMIT,
    SqlRejected,
    clamp_limit,
    validate_identifier,
    validate_select,
)


class ValidateSelectTests(unittest.TestCase):
    def test_accepts_select(self) -> None:
        self.assertEqual(
            validate_select("  SELECT name FROM customers  "),
            "SELECT name FROM customers",
        )

    def test_accepts_with(self) -> None:
        sql = "WITH recent AS (SELECT 1 AS id) SELECT id FROM recent"
        self.assertEqual(validate_select(sql), sql)

    def test_rejects_empty(self) -> None:
        with self.assertRaises(SqlRejected):
            validate_select("   ")

    def test_rejects_insert(self) -> None:
        with self.assertRaises(SqlRejected):
            validate_select("INSERT INTO customers VALUES (1, 'x')")

    def test_rejects_write_hidden_in_cte(self) -> None:
        with self.assertRaises(SqlRejected):
            validate_select("WITH x AS (SELECT 1) INSERT INTO t SELECT * FROM x")

    def test_rejects_chained_statements(self) -> None:
        with self.assertRaises(SqlRejected):
            validate_select("SELECT 1; DROP TABLE customers")

    def test_rejects_pragma(self) -> None:
        with self.assertRaises(SqlRejected):
            validate_select("PRAGMA journal_mode = DELETE")

    def test_rejects_attach(self) -> None:
        with self.assertRaises(SqlRejected):
            validate_select("ATTACH DATABASE 'other.sqlite' AS other")


class LimitAndIdentifierTests(unittest.TestCase):
    def test_clamps_to_maximum(self) -> None:
        self.assertEqual(clamp_limit(10_000), MAX_ROW_LIMIT)

    def test_rejects_non_positive_limit(self) -> None:
        with self.assertRaises(SqlRejected):
            clamp_limit(0)

    def test_rejects_path_like_identifier(self) -> None:
        with self.assertRaises(SqlRejected):
            validate_identifier("../erp")

    def test_accepts_bare_identifier(self) -> None:
        self.assertEqual(validate_identifier("legacy_cust_dump"), "legacy_cust_dump")


if __name__ == "__main__":
    unittest.main()
