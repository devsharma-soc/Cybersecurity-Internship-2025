import re
import sys

# Try importing homoglyphs library, prompt installation if missing
try:
    import homoglyphs as hg
except ImportError:
    print("Error: Please install the homoglyphs package first:\n    pip install homoglyphs")
    sys.exit(1)


def extract_links_from_file(filepath):
    """
    Reads a file and extracts URLs/domains using regex.
    
    Returns:
        list[str]: List of found URLs/domains
    """
    with open(filepath, "r", encoding="utf-8") as file:
        text = file.read()

    # Regex pattern to capture:
    # - Full URLs with http/https or www.
    # - Domain names with optional paths
    url_pattern = re.compile(
        r'((?:https?://|www\.)[^\s]+|[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?)'
    )

    return url_pattern.findall(text)


def is_link_suspicious(link, homoglyphs_obj):
    """
    Checks if a link contains homoglyphs (visually similar but different Unicode characters).

    Args:
        link (str): The link to check
        homoglyphs_obj (hg.Homoglyphs): Homoglyphs detection object

    Returns:
        bool: True if suspicious, False otherwise
    """
    # Convert to ASCII representation(s) if possible
    ascii_versions = homoglyphs_obj.to_ascii(link)

    # Suspicious if:
    # - There are possible ASCII equivalents
    # - The link is not already a pure ASCII match
    return bool(ascii_versions and (link not in ascii_versions))


def check_links(filepath):
    """
    Reads a file, extracts links, checks for homoglyphs, and prints results.
    """
    # Homoglyphs object (English, Russian, Greek chars considered)
    homoglyphs_obj = hg.Homoglyphs(languages={'en', 'ru', 'el'})

    # Extract all links from file
    links = extract_links_from_file(filepath)

    # Filter suspicious links
    suspicious_links = [
        link for link in links if is_link_suspicious(link, homoglyphs_obj)
    ]

    # Display results
    print(f"Total links found: {len(links)}")
    for link in links:
        print(f"   {link}")

    print("\nSuspicious (potential phishing) links:")
    if suspicious_links:
        for link in suspicious_links:
            print(f"   {link}")
    else:
        print("   None detected.")


if __name__ == "__main__":
    # Command-line usage: python homoglyph_checker.py your_file.txt
    if len(sys.argv) != 2:
        print("Usage: python homoglyph_checker.py your_file.txt")
        sys.exit(1)

    check_links(sys.argv[1])
