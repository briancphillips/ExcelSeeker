"""
Natural Language Query Parser for ExcelSeeker.
This module handles parsing natural language queries into structured search parameters.
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DateRange:
    """Represents a date range in the query."""

    start: Optional[datetime] = None
    end: Optional[datetime] = None
    is_relative: bool = False
    relative_term: str = ""


@dataclass
class MonetaryRange:
    """Represents a monetary range in the query."""

    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    currency: str = "USD"


@dataclass
class QueryEntity:
    """Represents an entity found in the query."""

    type: str
    value: str
    confidence: float = 1.0


@dataclass
class ParsedQuery:
    """Represents a fully parsed natural language query."""

    original_query: str
    search_terms: List[str]
    date_ranges: List[DateRange]
    monetary_ranges: List[MonetaryRange]
    entities: List[QueryEntity]
    search_mode: str = "exact"
    is_negated: bool = False


class QueryParser:
    """Parses natural language queries into structured search parameters."""

    def __init__(self):
        self.date_patterns = {
            "fiscal_year": r"FY\s*\d{2,4}",
            "year_range": r"\d{4}\s*-\s*\d{4}",
            "year": r"\b\d{4}\b",
            "quarter": r"Q[1-4]",
            "relative_time": r"(last|next|this)\s+(year|quarter|month|week)",
        }

        self.monetary_patterns = {
            "amount": r"\$\s*\d+(?:,\d{3})*(?:\.\d{2})?",
            "range": r"between\s+\$\s*\d+(?:,\d{3})*(?:\.\d{2})?\s+and\s+\$\s*\d+(?:,\d{3})*(?:\.\d{2})?",
            "comparison": r"(over|under|above|below|more than|less than)\s+\$\s*\d+(?:,\d{3})*(?:\.\d{2})?",
        }

        self.budget_patterns = {
            "code": r"\(\d{3,}\)",
            "department": r"dept\.\s*\d+|department\s*\d+",
        }

    def parse_query(self, query: str) -> ParsedQuery:
        """
        Parse a natural language query into structured components.

        Args:
            query: The natural language query string

        Returns:
            ParsedQuery object containing structured query information
        """
        try:
            # Convert to lowercase for consistent processing
            query = query.lower().strip()

            # Check for negation
            is_negated = any(word in query for word in ["not", "exclude", "except"])

            # Extract dates
            date_ranges = self._extract_date_ranges(query)

            # Extract monetary values
            monetary_ranges = self._extract_monetary_ranges(query)

            # Extract entities (budget codes, departments, etc.)
            entities = self._extract_entities(query)

            # Determine search mode
            search_mode = self._determine_search_mode(query)

            # Extract remaining search terms
            search_terms = self._extract_search_terms(query)

            return ParsedQuery(
                original_query=query,
                search_terms=search_terms,
                date_ranges=date_ranges,
                monetary_ranges=monetary_ranges,
                entities=entities,
                search_mode=search_mode,
                is_negated=is_negated,
            )

        except Exception as e:
            logger.error(f"Error parsing query '{query}': {str(e)}")
            # Return a basic parsed query on error
            return ParsedQuery(
                original_query=query,
                search_terms=[query],
                date_ranges=[],
                monetary_ranges=[],
                entities=[],
                search_mode="exact",
                is_negated=False,
            )

    def _extract_date_ranges(self, query: str) -> List[DateRange]:
        """Extract date ranges from the query."""
        date_ranges = []

        # Check for relative dates
        relative_matches = re.finditer(self.date_patterns["relative_time"], query)
        for match in relative_matches:
            relative_term = match.group()
            date_range = self._parse_relative_date(relative_term)
            if date_range:
                date_ranges.append(date_range)

        # Check for fiscal years
        fy_matches = re.finditer(self.date_patterns["fiscal_year"], query)
        for match in fy_matches:
            date_range = self._parse_fiscal_year(match.group())
            if date_range:
                date_ranges.append(date_range)

        # Check for year ranges
        year_range_matches = re.finditer(self.date_patterns["year_range"], query)
        for match in year_range_matches:
            date_range = self._parse_year_range(match.group())
            if date_range:
                date_ranges.append(date_range)

        return date_ranges

    def _extract_monetary_ranges(self, query: str) -> List[MonetaryRange]:
        """Extract monetary ranges from the query."""
        monetary_ranges = []

        # Check for explicit ranges
        range_matches = re.finditer(self.monetary_patterns["range"], query)
        for match in range_matches:
            monetary_range = self._parse_monetary_range(match.group())
            if monetary_range:
                monetary_ranges.append(monetary_range)

        # Check for comparisons
        comparison_matches = re.finditer(self.monetary_patterns["comparison"], query)
        for match in comparison_matches:
            monetary_range = self._parse_monetary_comparison(match.group())
            if monetary_range:
                monetary_ranges.append(monetary_range)

        return monetary_ranges

    def _extract_entities(self, query: str) -> List[QueryEntity]:
        """Extract entities like budget codes and departments from the query."""
        entities = []

        # Extract budget codes
        code_matches = re.finditer(self.budget_patterns["code"], query)
        for match in code_matches:
            entities.append(
                QueryEntity(
                    type="budget_code", value=match.group().strip("()"), confidence=1.0
                )
            )

        # Extract department references
        dept_matches = re.finditer(self.budget_patterns["department"], query)
        for match in dept_matches:
            entities.append(
                QueryEntity(type="department", value=match.group(), confidence=1.0)
            )

        return entities

    def _determine_search_mode(self, query: str) -> str:
        """Determine the appropriate search mode based on query structure."""
        if any(
            phrase in query for phrase in ["exactly", "exact phrase", "exactly matches"]
        ):
            return "exact"
        elif any(phrase in query for phrase in ["any of", "either", "or"]):
            return "any"
        elif any(phrase in query for phrase in ["all of", "both", "and"]):
            return "all"
        return "exact"  # default mode

    def _extract_search_terms(self, query: str) -> List[str]:
        """Extract the main search terms after removing recognized patterns."""
        # Remove recognized patterns
        for pattern_dict in [
            self.date_patterns,
            self.monetary_patterns,
            self.budget_patterns,
        ]:
            for pattern in pattern_dict.values():
                query = re.sub(pattern, "", query)

        # Remove common stop words and special characters
        words = query.split()
        stop_words = {"in", "the", "for", "with", "at", "from", "to", "and", "or"}
        terms = [word for word in words if word not in stop_words and len(word) > 1]

        return terms

    def _parse_relative_date(self, term: str) -> Optional[DateRange]:
        """Parse relative date terms into a DateRange."""
        now = datetime.now()
        words = term.split()

        if len(words) != 2:
            return None

        direction, unit = words

        if direction == "last":
            if unit == "year":
                start = now.replace(year=now.year - 1, month=1, day=1)
                end = now.replace(year=now.year - 1, month=12, day=31)
            elif unit == "quarter":
                current_quarter = (now.month - 1) // 3
                start = now.replace(month=max(1, (current_quarter - 1) * 3 + 1), day=1)
                end = now.replace(
                    month=min(12, current_quarter * 3), day=1
                ) + timedelta(days=32)
                end = end.replace(day=1) - timedelta(days=1)
            elif unit == "month":
                start = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
                end = now.replace(day=1) - timedelta(days=1)
            elif unit == "week":
                start = now - timedelta(days=now.weekday() + 7)
                end = start + timedelta(days=6)
            else:
                return None
        else:
            return None  # Handle other cases as needed

        return DateRange(start=start, end=end, is_relative=True, relative_term=term)

    def _parse_fiscal_year(self, fy_str: str) -> Optional[DateRange]:
        """Parse fiscal year string into a DateRange."""
        try:
            year = int(re.search(r"\d+", fy_str).group())
            if year < 100:  # Two-digit year
                year = 2000 + year if year < 50 else 1900 + year

            # Assuming fiscal year starts in October
            start = datetime(year - 1, 10, 1)
            end = datetime(year, 9, 30)

            return DateRange(start=start, end=end)
        except:
            return None

    def _parse_year_range(self, range_str: str) -> Optional[DateRange]:
        """Parse year range string into a DateRange."""
        try:
            years = [int(year) for year in re.findall(r"\d{4}", range_str)]
            if len(years) == 2:
                return DateRange(
                    start=datetime(years[0], 1, 1), end=datetime(years[1], 12, 31)
                )
        except:
            return None
        return None

    def _parse_monetary_range(self, range_str: str) -> Optional[MonetaryRange]:
        """Parse monetary range string into a MonetaryRange."""
        try:
            amounts = [
                float(re.sub(r"[^\d.]", "", amount))
                for amount in re.findall(r"\$\s*\d+(?:,\d{3})*(?:\.\d{2})?", range_str)
            ]
            if len(amounts) == 2:
                return MonetaryRange(min_amount=min(amounts), max_amount=max(amounts))
        except:
            return None
        return None

    def _parse_monetary_comparison(self, comp_str: str) -> Optional[MonetaryRange]:
        """Parse monetary comparison string into a MonetaryRange."""
        try:
            amount = float(
                re.sub(
                    r"[^\d.]",
                    "",
                    re.search(r"\$\s*\d+(?:,\d{3})*(?:\.\d{2})?", comp_str).group(),
                )
            )

            if any(word in comp_str for word in ["over", "above", "more than"]):
                return MonetaryRange(min_amount=amount)
            elif any(word in comp_str for word in ["under", "below", "less than"]):
                return MonetaryRange(max_amount=amount)

        except:
            return None
        return None
