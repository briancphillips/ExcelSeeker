"""Test module for the natural language query parser."""

import unittest
from datetime import datetime, timedelta
from query_parser import QueryParser, ParsedQuery, DateRange, MonetaryRange, QueryEntity


class TestQueryParser(unittest.TestCase):
    def setUp(self):
        self.parser = QueryParser()

    def test_basic_search(self):
        """Test basic search terms extraction."""
        query = "find travel expenses"
        result = self.parser.parse_query(query)
        self.assertEqual(result.search_terms, ["travel", "expenses"])
        self.assertEqual(result.search_mode, "exact")

    def test_date_ranges(self):
        """Test date range extraction."""
        # Test fiscal year
        query = "expenses for FY2023"
        result = self.parser.parse_query(query)
        self.assertEqual(len(result.date_ranges), 1)
        self.assertEqual(
            result.date_ranges[0].start.year, 2022
        )  # FY2023 starts in 2022
        self.assertEqual(result.date_ranges[0].end.year, 2023)

        # Test relative dates
        query = "expenses from last quarter"
        result = self.parser.parse_query(query)
        self.assertEqual(len(result.date_ranges), 1)
        self.assertTrue(result.date_ranges[0].is_relative)

        # Test year range
        query = "budget items from 2022-2023"
        result = self.parser.parse_query(query)
        self.assertEqual(len(result.date_ranges), 1)
        self.assertEqual(result.date_ranges[0].start.year, 2022)
        self.assertEqual(result.date_ranges[0].end.year, 2023)

    def test_monetary_ranges(self):
        """Test monetary range extraction."""
        # Test explicit range
        query = "expenses between $1,000 and $5,000"
        result = self.parser.parse_query(query)
        self.assertEqual(len(result.monetary_ranges), 1)
        self.assertEqual(result.monetary_ranges[0].min_amount, 1000)
        self.assertEqual(result.monetary_ranges[0].max_amount, 5000)

        # Test comparison
        query = "expenses over $10,000"
        result = self.parser.parse_query(query)
        self.assertEqual(len(result.monetary_ranges), 1)
        self.assertEqual(result.monetary_ranges[0].min_amount, 10000)
        self.assertIsNone(result.monetary_ranges[0].max_amount)

    def test_budget_codes(self):
        """Test budget code extraction."""
        query = "expenses for department 123 with code (45678)"
        result = self.parser.parse_query(query)
        self.assertEqual(len(result.entities), 2)
        self.assertTrue(
            any(e.type == "budget_code" and e.value == "45678" for e in result.entities)
        )
        self.assertTrue(
            any(e.type == "department" and "123" in e.value for e in result.entities)
        )

    def test_search_modes(self):
        """Test search mode detection."""
        # Test exact mode
        query = "find exactly matching travel expenses"
        result = self.parser.parse_query(query)
        self.assertEqual(result.search_mode, "exact")

        # Test any mode
        query = "find any of these keywords: travel, expenses, budget"
        result = self.parser.parse_query(query)
        self.assertEqual(result.search_mode, "any")

        # Test all mode
        query = "find all of these terms: travel and expenses"
        result = self.parser.parse_query(query)
        self.assertEqual(result.search_mode, "all")

    def test_negation(self):
        """Test negation detection."""
        query = "find expenses not including travel"
        result = self.parser.parse_query(query)
        self.assertTrue(result.is_negated)

        query = "exclude travel expenses"
        result = self.parser.parse_query(query)
        self.assertTrue(result.is_negated)

    def test_complex_query(self):
        """Test complex query with multiple components."""
        query = "find travel expenses over $5,000 from last quarter in department 123 excluding code (9999)"
        result = self.parser.parse_query(query)

        # Check monetary range
        self.assertEqual(len(result.monetary_ranges), 1)
        self.assertEqual(result.monetary_ranges[0].min_amount, 5000)

        # Check date range
        self.assertEqual(len(result.date_ranges), 1)
        self.assertTrue(result.date_ranges[0].is_relative)

        # Check entities
        self.assertEqual(len(result.entities), 2)
        self.assertTrue(
            any(e.type == "department" and "123" in e.value for e in result.entities)
        )
        self.assertTrue(
            any(e.type == "budget_code" and e.value == "9999" for e in result.entities)
        )

        # Check search terms
        self.assertTrue("travel" in result.search_terms)
        self.assertTrue("expenses" in result.search_terms)

    def test_error_handling(self):
        """Test error handling with invalid queries."""
        # Test empty query
        result = self.parser.parse_query("")
        self.assertEqual(result.search_terms, [""])
        self.assertEqual(result.search_mode, "exact")

        # Test malformed date
        query = "expenses from invalid-date"
        result = self.parser.parse_query(query)
        self.assertEqual(len(result.date_ranges), 0)
        self.assertTrue("expenses" in result.search_terms)

        # Test malformed monetary value
        query = "expenses over $invalid"
        result = self.parser.parse_query(query)
        self.assertEqual(len(result.monetary_ranges), 0)
        self.assertTrue("expenses" in result.search_terms)


if __name__ == "__main__":
    unittest.main()
