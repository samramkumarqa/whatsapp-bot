from bs4 import BeautifulSoup
import requests

from urllib.parse import (
    urljoin,
    urlparse
)


def is_valid_url(url):

    blocked_patterns = [
        "/tag/",
        "/login",
        "/logout",
        "/signup",
        "/privacy",
        "/terms",
        "/account",
        "/search",
        "mailto:",
        "javascript:"
    ]

    return not any(
        pattern in url.lower()
        for pattern in blocked_patterns
    )


def discover_links(
    start_url,
    max_pages=50,
    max_depth=3
):

    visited = set()

    # (url, depth)
    queue = [
        (
            start_url,
            0
        )
    ]

    domain = urlparse(
        start_url
    ).netloc

    ALLOWED_PATHS = [
        "/documentation/",
        "/webdriver/",
        "/api/",
        "/docs/"
    ]

    BLOCKED_PATHS = [
        "/ja/",
        "/zh-cn/",
        "/pt-br/",
        "/es/",
        "/fr/",
        "/events",
        "/sponsor",
        "/sponsors",
        "/project",
        "/history",
        "/about",
        "/ecosystem"
    ]

    while queue and len(visited) < max_pages:

        url, depth = queue.pop(0)

        if depth > max_depth:
            continue

        if url in visited:
            continue

        try:

            print(
                f"🌐 Crawling "
                f"(depth={depth}) "
                f"{url}"
            )

            response = requests.get(
                url,
                timeout=10,
                headers={
                    "User-Agent":
                    "Mozilla/5.0"
                }
            )

            if response.status_code != 200:
                continue

            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )

            visited.add(url)

            for link in soup.find_all(
                "a",
                href=True
            ):

                href = urljoin(
                    url,
                    link["href"]
                )

                # Remove fragments
                href = href.split("#")[0]

                # Remove query params
                href = href.split("?")[0]

                parsed = urlparse(
                    href
                )

                # Domain lock
                if parsed.netloc != domain:
                    continue

                # Metadata filtering
                if not is_valid_url(href):
                    continue

                # Block unwanted sections
                if any(
                    blocked in href
                    for blocked in BLOCKED_PATHS
                ):
                    continue

                # Documentation-only mode
                if not any(
                    allowed in href
                    for allowed in ALLOWED_PATHS
                ):
                    continue

                if (
                    href not in visited
                    and (href, depth + 1)
                    not in queue
                ):
                    queue.append(
                        (
                            href,
                            depth + 1
                        )
                    )

        except Exception as e:

            print(
                f"❌ Crawl failed: "
                f"{url}"
            )

            print(e)

    return sorted(
        list(visited)
    )