from urllib.parse import urlparse


def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all(
            [
                result.scheme,  # http, https, ftp, etc.
                result.netloc,  # domain present
            ]
        )
    except Exception:
        return False
