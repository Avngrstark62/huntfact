"""Example script demonstrating how to use ddgs_wrapper for web searches."""

from services.ddgs_wrapper import search_web


def main():
    """Perform a web search and display results."""
    # Perform a web search with default settings
    query = "asaram bapu in ram mandir news"
    print(f"Searching for: {query}\n")

    all_results = []
    for i in range(4):
        print(f"Fetching page {i + 1}...")
        results = search_web(
                query=query,
                max_results=30,
                page=i+1,
                region="in-en",
                safesearch="moderate",
                timeout=10,
                backend="duckduckgo",
            )
        all_results.extend(results)
    # Display results
    print(f"Found {len(results)} results:\n")
    for i, result in enumerate(all_results, 1):
        # print(f"{i}. {result['title']}")
        # print(f"   URL: {result['href']}")
        # print(f"   Summary: {result['body'][:150]}...")
        print(f"{i}. {result}")
        print()


if __name__ == "__main__":
    main()
