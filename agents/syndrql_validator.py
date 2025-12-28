"""
SyndrQL Query Validator

Validates SyndrQL queries based on syntax patterns from SyndrQL-Syntax.py.
Uses lenient pattern matching (case-insensitive, flexible whitespace).

Supported query types:
- SELECT (with optional JOIN, WHERE, ORDER BY, GROUP BY, LIMIT)
- UPDATE (IN BUNDLE with WHERE)
- DELETE (FROM with WHERE)
- ADD DOCUMENT (TO BUNDLE with WITH)
"""

import re
from typing import Tuple


def validate_query(query: str) -> Tuple[bool, str]:
    """
    Validate a SyndrQL query against known patterns.
    
    Args:
        query: SyndrQL query string to validate
        
    Returns:
        Tuple of (is_valid: bool, error_message: str)
        If valid, error_message is empty string
    """
    if not query or not isinstance(query, str):
        return False, "Query is empty or not a string"
    
    # Remove extra whitespace and normalize
    query_normalized = ' '.join(query.split())
    
    # Check for query type (case-insensitive)
    query_upper = query_normalized.upper()
    
    # SELECT queries
    if query_upper.startswith('SELECT'):
        return _validate_select(query_normalized)
    
    # UPDATE queries
    elif query_upper.startswith('UPDATE'):
        return _validate_update(query_normalized)
    
    # DELETE queries
    elif query_upper.startswith('DELETE'):
        return _validate_delete(query_normalized)
    
    # ADD DOCUMENT queries
    elif 'ADD' in query_upper and 'DOCUMENT' in query_upper:
        return _validate_add_document(query_normalized)
    
    else:
        return False, f"Unrecognized query type. Query must start with SELECT, UPDATE, DELETE, or ADD DOCUMENT"


def _validate_select(query: str) -> Tuple[bool, str]:
    """
    Validate SELECT query.
    
    Required: SELECT ... FROM ...
    Optional: JOIN, WHERE, ORDER BY, GROUP BY, LIMIT, TOP
    
    Examples from SyndrQL-Syntax.py:
    - SELECT DOCUMENTS FROM "Authors" WHERE "Age" > 15 ORDER BY "AuthorName" DESC
    - SELECT TOP 5 * FROM "Authors"
    - SELECT COUNT(*) FROM "Books" WHERE "PublishedYear" >= 2010
    - SELECT "Authors"."AuthorName", "Books"."Title" FROM "Authors" Join "Books" On ...
    """
    query_upper = query.upper()
    
    # Must have SELECT and FROM
    if 'FROM' not in query_upper:
        return False, "SELECT query missing FROM clause"
    
    # Validate basic structure (lenient - just check keywords exist in reasonable positions)
    # SELECT comes before FROM
    select_pos = query_upper.find('SELECT')
    from_pos = query_upper.find('FROM')
    
    if select_pos > from_pos:
        return False, "SELECT must come before FROM"
    
    # If JOIN exists, validate JOIN ... ON pattern
    if 'JOIN' in query_upper:
        join_pattern = re.compile(r'\bJOIN\b.*?\bON\b', re.IGNORECASE | re.DOTALL)
        if not join_pattern.search(query):
            return False, "JOIN clause missing ON condition"
    
    # Check for valid terminator (semicolon)
    if not query.rstrip().endswith(';'):
        return False, "Query must end with semicolon"
    
    return True, ""


def _validate_update(query: str) -> Tuple[bool, str]:
    """
    Validate UPDATE query.
    
    Required: UPDATE DOCUMENTS IN BUNDLE ... WHERE ...
    
    Example from SyndrQL-Syntax.py:
    - UPDATE DOCUMENTS IN BUNDLE "Authors" ("AuthorName" = "Dan Strohschein-669") WHERE "DocumentID" == "187320fc9a770e28_33"
    """
    query_upper = query.upper()
    
    # Must have UPDATE, IN BUNDLE, and WHERE
    required_keywords = ['UPDATE', 'IN BUNDLE', 'WHERE']
    missing = [kw for kw in required_keywords if kw not in query_upper]
    
    if missing:
        return False, f"UPDATE query missing required keywords: {', '.join(missing)}"
    
    # Check keyword order
    update_pos = query_upper.find('UPDATE')
    bundle_pos = query_upper.find('IN BUNDLE')
    where_pos = query_upper.find('WHERE')
    
    if not (update_pos < bundle_pos < where_pos):
        return False, "UPDATE query keywords must be in order: UPDATE ... IN BUNDLE ... WHERE"
    
    # Check for valid terminator
    if not query.rstrip().endswith(';'):
        return False, "Query must end with semicolon"
    
    return True, ""


def _validate_delete(query: str) -> Tuple[bool, str]:
    """
    Validate DELETE query.
    
    Required: DELETE DOCUMENTS FROM ... WHERE ...
    
    Example from SyndrQL-Syntax.py:
    - DELETE DOCUMENTS FROM "Books" WHERE "DocumentID" == "18712e2dbd27c5e8_2a"
    """
    query_upper = query.upper()
    
    # Must have DELETE, FROM, and WHERE
    required_keywords = ['DELETE', 'FROM', 'WHERE']
    missing = [kw for kw in required_keywords if kw not in query_upper]
    
    if missing:
        return False, f"DELETE query missing required keywords: {', '.join(missing)}"
    
    # Check keyword order
    delete_pos = query_upper.find('DELETE')
    from_pos = query_upper.find('FROM')
    where_pos = query_upper.find('WHERE')
    
    if not (delete_pos < from_pos < where_pos):
        return False, "DELETE query keywords must be in order: DELETE ... FROM ... WHERE"
    
    # Check for valid terminator
    if not query.rstrip().endswith(';'):
        return False, "Query must end with semicolon"
    
    return True, ""


def _validate_add_document(query: str) -> Tuple[bool, str]:
    """
    Validate ADD DOCUMENT query.
    
    Required: ADD DOCUMENT TO BUNDLE ... WITH ...
    
    Examples from agent code:
    - ADD DOCUMENT TO BUNDLE "products" WITH ({{"name" = "Product"}}, {{"price" = 99.99}})
    """
    query_upper = query.upper()
    
    # Must have ADD, DOCUMENT, TO BUNDLE, and WITH
    required_keywords = ['ADD', 'DOCUMENT', 'TO BUNDLE', 'WITH']
    missing = [kw for kw in required_keywords if kw not in query_upper]
    
    if missing:
        return False, f"ADD DOCUMENT query missing required keywords: {', '.join(missing)}"
    
    # Check keyword order
    add_pos = query_upper.find('ADD')
    document_pos = query_upper.find('DOCUMENT')
    bundle_pos = query_upper.find('TO BUNDLE')
    with_pos = query_upper.find('WITH')
    
    if not (add_pos < document_pos < bundle_pos < with_pos):
        return False, "ADD DOCUMENT query keywords must be in order: ADD DOCUMENT TO BUNDLE ... WITH"
    
    # Check for valid terminator
    if not query.rstrip().endswith(';'):
        return False, "Query must end with semicolon"
    
    return True, ""


# Convenience function for testing
if __name__ == "__main__":
    test_queries = [
        'SELECT DOCUMENTS FROM "Authors" WHERE "Age" > 15 ORDER BY "AuthorName" DESC;',
        'SELECT TOP 5 * FROM "Authors";',
        'UPDATE DOCUMENTS IN BUNDLE "Authors" ("AuthorName" = "Test") WHERE "DocumentID" == "123";',
        'DELETE DOCUMENTS FROM "Books" WHERE "DocumentID" == "456";',
        'ADD DOCUMENT TO BUNDLE "products" WITH ({{"name" = "Test"}});',
        'INVALID QUERY',
        'SELECT * WHERE something;',  # Missing FROM
    ]
    
    for query in test_queries:
        is_valid, error = validate_query(query)
        print(f"{'✓' if is_valid else '✗'} {query[:60]}...")
        if error:
            print(f"  Error: {error}")
