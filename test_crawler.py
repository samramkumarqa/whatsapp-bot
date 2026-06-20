from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin


def discover_links(
    start_url,
    max_pages=20
):

    visited = set()
    queue = [start_url]

    while queue and len(visited) < max_pages:

        url = queue.pop(0)

        if url in visited:
            continue

        try:

            print(f"🔍 Visiting: {url}")

            response = requests.get(
                url,
                timeout=10,
                headers={
                    "User-Agent": "Mozilla/5.0"
                }
            )

            if response.status_code != 200:
                continue

            visited.add(url)

            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )

            links = soup.find_all(
                "a",
                href=True
            )

            print(
                f"Found {len(links)} links"
            )

            for link in links:

                href = link["href"]

                # Wikipedia article links only
                if not href.startswith("/wiki/"):
                    continue

                # Skip special pages
                if ":" in href:
                    continue

                if "#" in href:
                    continue

                full_url = urljoin(
                    "https://en.wikipedia.org",
                    href
                )

                if (
                    full_url not in visited
                    and full_url not in queue
                ):
                    queue.append(full_url)

        except Exception as e:

            print(
                f"❌ Error crawling {url}: {e}"
            )

    return list(visited)