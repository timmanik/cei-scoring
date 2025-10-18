"""
Web search utilities with domain filtering for cloud provider documentation.

Uses DuckDuckGo search to find official documentation from Azure and GCP.
Domain filtering ensures results come from authoritative sources.
"""

import logging
from typing import List, Dict, Optional

try:
    from ddgs import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False
    logging.warning(
        "ddgs not installed. Web search functionality will be limited. "
        "Install with: pip install ddgs"
    )


# Domain filters for official documentation
PROVIDER_DOMAINS = {
    'Azure': ['learn.microsoft.com', 'azure.microsoft.com', 'docs.microsoft.com'],
    'GCP': ['cloud.google.com'],
    'AWS': ['docs.aws.amazon.com', 'aws.amazon.com']
}


def search_with_domain_filter(
    query: str,
    provider: str,
    max_results: int = 5,
    timeout: int = 10
) -> List[Dict[str, str]]:
    """
    Search for cloud documentation with domain filtering.

    Args:
        query: Search query string
        provider: Cloud provider ('Azure', 'GCP', or 'AWS')
        max_results: Maximum number of results to return
        timeout: Timeout in seconds for the search

    Returns:
        list: List of result dictionaries with 'title', 'url', and 'snippet' keys

    Example:
        results = search_with_domain_filter(
            "Azure App Service pricing",
            "Azure",
            max_results=3
        )
        # Returns: [{"title": "...", "url": "...", "snippet": "..."}, ...]
    """
    if not DDGS_AVAILABLE:
        return [{
            'title': 'Search Unavailable',
            'url': '',
            'snippet': (
                'Web search is not available. Install ddgs: '
                'pip install ddgs'
            )
        }]

    if provider not in PROVIDER_DOMAINS:
        return [{
            'title': 'Invalid Provider',
            'url': '',
            'snippet': f'Unknown provider "{provider}". Use Azure, GCP, or AWS.'
        }]

    # Get domains for this provider
    domains = PROVIDER_DOMAINS[provider]

    # Build site-restricted query
    # Format: "query site:domain1 OR site:domain2"
    site_filters = ' OR '.join([f'site:{domain}' for domain in domains])
    search_query = f'{query} ({site_filters})'

    logger = logging.getLogger(__name__)
    logger.info(f"Searching: {search_query}")

    try:
        # Perform search
        with DDGS() as ddgs:
            results = list(ddgs.text(
                search_query,
                max_results=max_results,
                region='wt-wt',  # Worldwide
                safesearch='off',
                timelimit=None
            ))

        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                'title': result.get('title', 'No title'),
                'url': result.get('href', ''),
                'snippet': result.get('body', '')
            })

        logger.info(f"Found {len(formatted_results)} results")
        return formatted_results

    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return [{
            'title': 'Search Error',
            'url': '',
            'snippet': f'An error occurred during search: {str(e)}'
        }]


def format_search_results_for_model(results: List[Dict[str, str]]) -> str:
    """
    Format search results into readable text for the model.

    Args:
        results: List of search result dictionaries

    Returns:
        str: Formatted text representation of results
    """
    if not results:
        return "No results found."

    # Check for error results
    if results[0].get('title') in ['Search Unavailable', 'Invalid Provider', 'Search Error']:
        return results[0]['snippet']

    formatted = []
    for i, result in enumerate(results, 1):
        formatted.append(f"\n{i}. **{result['title']}**")
        formatted.append(f"   URL: {result['url']}")
        formatted.append(f"   {result['snippet']}")

    return '\n'.join(formatted)


def search_aws_documentation(service_name: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Search AWS documentation specifically.

    Args:
        service_name: AWS service name
        max_results: Maximum number of results

    Returns:
        list: Search results
    """
    query = f"{service_name} features pricing management"
    return search_with_domain_filter(query, 'AWS', max_results)


def search_azure_documentation(service_name: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Search Azure documentation specifically.

    Args:
        service_name: Azure service name
        max_results: Maximum number of results

    Returns:
        list: Search results
    """
    query = f"{service_name} overview features pricing"
    return search_with_domain_filter(query, 'Azure', max_results)


def search_gcp_documentation(service_name: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Search GCP documentation specifically.

    Args:
        service_name: GCP service name
        max_results: Maximum number of results

    Returns:
        list: Search results
    """
    query = f"{service_name} overview features pricing"
    return search_with_domain_filter(query, 'GCP', max_results)
