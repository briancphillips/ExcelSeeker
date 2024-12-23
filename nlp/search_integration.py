"""Integration module to connect NLP query parsing with search functionality."""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from .query_parser import (
    QueryParser,
    ParsedQuery,
    DateRange,
    MonetaryRange,
    QueryEntity,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SearchIntegration:
    """Integrates NLP query parsing with search functionality."""

    def __init__(self):
        self.parser = QueryParser()

    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process a natural language query and convert it to search parameters.

        Args:
            query: Natural language query string

        Returns:
            Dictionary containing structured search parameters
        """
        try:
            # Parse the natural language query
            parsed_query = self.parser.parse_query(query)

            # Convert parsed query to search parameters
            search_params = self._convert_to_search_params(parsed_query)

            return search_params

        except Exception as e:
            logger.error(f"Error processing query '{query}': {str(e)}")
            # Return basic search parameters on error
            return {"search_text": query, "search_mode": "exact", "filters": {}}

    def _convert_to_search_params(self, parsed_query: ParsedQuery) -> Dict[str, Any]:
        """Convert parsed query to search parameters."""
        search_params = {
            "search_text": " ".join(parsed_query.search_terms),
            "search_mode": parsed_query.search_mode,
            "filters": {},
        }

        # Add date filters
        if parsed_query.date_ranges:
            date_filters = []
            for date_range in parsed_query.date_ranges:
                if date_range.start and date_range.end:
                    date_filters.append(
                        {
                            "start": date_range.start.isoformat(),
                            "end": date_range.end.isoformat(),
                            "is_relative": date_range.is_relative,
                            "relative_term": date_range.relative_term,
                        }
                    )
            if date_filters:
                search_params["filters"]["dates"] = date_filters

        # Add monetary filters
        if parsed_query.monetary_ranges:
            monetary_filters = []
            for money_range in parsed_query.monetary_ranges:
                filter_dict = {"currency": money_range.currency}
                if money_range.min_amount is not None:
                    filter_dict["min_amount"] = money_range.min_amount
                if money_range.max_amount is not None:
                    filter_dict["max_amount"] = money_range.max_amount
                monetary_filters.append(filter_dict)
            if monetary_filters:
                search_params["filters"]["monetary"] = monetary_filters

        # Add entity filters
        if parsed_query.entities:
            entity_filters = {}
            for entity in parsed_query.entities:
                if entity.type not in entity_filters:
                    entity_filters[entity.type] = []
                entity_filters[entity.type].append(
                    {"value": entity.value, "confidence": entity.confidence}
                )
            if entity_filters:
                search_params["filters"]["entities"] = entity_filters

        # Add negation flag
        if parsed_query.is_negated:
            search_params["filters"]["negated"] = True

        return search_params

    def apply_filters(
        self, results: List[Dict[str, Any]], filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Apply filters to search results.

        Args:
            results: List of search results
            filters: Dictionary of filters to apply

        Returns:
            Filtered list of results
        """
        if not filters:
            return results

        filtered_results = results.copy()

        try:
            # Apply date filters
            if "dates" in filters:
                filtered_results = self._apply_date_filters(
                    filtered_results, filters["dates"]
                )

            # Apply monetary filters
            if "monetary" in filters:
                filtered_results = self._apply_monetary_filters(
                    filtered_results, filters["monetary"]
                )

            # Apply entity filters
            if "entities" in filters:
                filtered_results = self._apply_entity_filters(
                    filtered_results, filters["entities"]
                )

            # Apply negation if specified
            if filters.get("negated", False):
                filtered_results = self._apply_negation(filtered_results)

            return filtered_results

        except Exception as e:
            logger.error(f"Error applying filters: {str(e)}")
            return results

    def _apply_date_filters(
        self, results: List[Dict[str, Any]], date_filters: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Apply date filters to results."""
        filtered_results = []

        for result in results:
            # Extract date from result (assuming it exists in the value)
            try:
                result_date = self._extract_date_from_value(result.get("value", ""))
                if result_date:
                    for date_filter in date_filters:
                        start_date = datetime.fromisoformat(date_filter["start"])
                        end_date = datetime.fromisoformat(date_filter["end"])
                        if start_date <= result_date <= end_date:
                            filtered_results.append(result)
                            break
            except Exception as e:
                logger.debug(f"Error processing date in result: {str(e)}")
                # Include results where date processing fails
                filtered_results.append(result)

        return filtered_results

    def _apply_monetary_filters(
        self, results: List[Dict[str, Any]], monetary_filters: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Apply monetary filters to results."""
        filtered_results = []

        for result in results:
            # Extract amount from result (assuming it exists in the value)
            try:
                amount = self._extract_amount_from_value(result.get("value", ""))
                if amount is not None:
                    for money_filter in monetary_filters:
                        min_amount = money_filter.get("min_amount")
                        max_amount = money_filter.get("max_amount")

                        if min_amount is not None and amount < min_amount:
                            continue
                        if max_amount is not None and amount > max_amount:
                            continue

                        filtered_results.append(result)
                        break
            except Exception as e:
                logger.debug(f"Error processing amount in result: {str(e)}")
                # Include results where amount processing fails
                filtered_results.append(result)

        return filtered_results

    def _apply_entity_filters(
        self,
        results: List[Dict[str, Any]],
        entity_filters: Dict[str, List[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        """Apply entity filters to results."""
        filtered_results = []

        for result in results:
            include_result = True

            for entity_type, entities in entity_filters.items():
                entity_found = False
                for entity in entities:
                    if entity["value"].lower() in result.get("value", "").lower():
                        entity_found = True
                        break

                if not entity_found:
                    include_result = False
                    break

            if include_result:
                filtered_results.append(result)

        return filtered_results

    def _apply_negation(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply negation to results (exclude matched results)."""
        # In the case of negation, we're actually returning results that DON'T match
        # This is handled at a higher level when constructing the search query
        return results

    def _extract_date_from_value(self, value: str) -> Optional[datetime]:
        """Extract date from a value string."""
        # This is a placeholder - implement actual date extraction logic
        # Could use dateutil.parser or custom logic based on your data format
        return None

    def _extract_amount_from_value(self, value: str) -> Optional[float]:
        """Extract monetary amount from a value string."""
        # This is a placeholder - implement actual amount extraction logic
        # Could use regex or custom logic based on your data format
        return None
