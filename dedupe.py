import hashlib


def remove_duplicate_chunks(chunks):

    unique = []
    seen = set()

    for chunk in chunks:

        h = hashlib.md5(
            chunk.page_content.encode("utf-8")
        ).hexdigest()

        if h not in seen:
            seen.add(h)
            unique.append(chunk)

    return unique