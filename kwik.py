#..........This Bot Made By [RAHAT](https://t.me/r4h4t_69)..........#
#..........Anyone Can Modify This As He Likes..........#
#..........Just one requests do not remove my credit..........#
#
# Converted from kwik.rs — full logic port including:
#   - JS-style base decoder
#   - Packed payload extraction & decoding
#   - Token extraction & direct-link POST
#   - Embed stream extraction

import re
import requests
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

CLIENT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/138.0.0.0 Safari/537.36"
)

BASE_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ+/"

# ── Packed-payload regex (matches the obfuscated JS blob on kwik pages) ──────
PACKED_RE = re.compile(
    r'\(\s*"([^",]*)"'       # group 1 – encoded payload
    r'\s*,\s*\d+'            # ignored int
    r'\s*,\s*"([^",]*)"'     # group 2 – alphabet key
    r'\s*,\s*(\d+)'          # group 3 – offset
    r'\s*,\s*(\d+)'          # group 4 – base
    r'\s*,\s*\d+[a-zA-Z]?\s*\)'
)


@dataclass
class PaheLink:
    url: str        # original pahe URL
    file_url: str   # resolved kwik /f/ URL


@dataclass
class KwikFile:
    embed: str        # kwik /e/ embed URL
    downloadable: str # direct download URL


@dataclass
class DirectLink:
    referer: str
    direct_link: str


@dataclass
class Stream:
    referer: str
    source: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _origin_from_url(url: str) -> Optional[str]:
    parsed = urlparse(url)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return None


def _decode_base(input_str: str, from_base: int, to_base: int) -> int:
    """Translate a string from one base to another using BASE_ALPHABET."""
    from_alphabet = BASE_ALPHABET[:from_base]
    to_alphabet   = BASE_ALPHABET[:to_base]

    value = 0
    for idx, ch in enumerate(reversed(input_str)):
        pos = from_alphabet.find(ch)
        if pos != -1:
            value += pos * (from_base ** idx)

    if value == 0:
        first = to_alphabet[0] if to_alphabet else "0"
        return int(first)

    out = ""
    v = value
    while v > 0:
        i = v % to_base
        out = to_alphabet[i] + out
        v //= to_base

    return int(out)


def _decode_js_style(encoded: str, alphabet_key: str, offset: int, base: int) -> str:
    """
    Mirrors KwikClient::decode_js_style from the Rust source.
    Splits `encoded` on the sentinel character (alphabet_key[base]),
    converts each chunk through the alphabet, then maps to a Unicode char.
    """
    sentinel = alphabet_key[base]
    output = []
    chunks = encoded.split(sentinel)
    # The last element after split is always an empty trailing piece — skip it
    for chunk in chunks[:-1] if encoded.endswith(sentinel) else chunks:
        replaced = chunk
        for idx, c in enumerate(alphabet_key):
            replaced = replaced.replace(c, str(idx))
        code = _decode_base(replaced, base, 10) - offset
        output.append(chr(code))
    return "".join(output)


# ── Main client ───────────────────────────────────────────────────────────────

class KwikClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": CLIENT_UA})

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _fetch_file_body(self, file_url: str) -> str:
        resp = self.session.get(file_url, headers={"User-Agent": CLIENT_UA})
        resp.raise_for_status()
        return resp.text

    def _extract_link_and_token(self, decoded: str):
        """
        Returns (form_action, _token) from the decoded JS payload.
        Mirrors KwikClient::extract_link_and_token.
        """
        form_action_re = re.compile(r'<form[^>]*action=["\']([^"\']+)["\']')
        kwik_link_re   = re.compile(r'"(https?://kwik\.[^/\s"]+/[^/\s"]+/[^"\s]*)"')

        m = form_action_re.search(decoded)
        if m:
            link = m.group(1)
        else:
            m = kwik_link_re.search(decoded)
            if not m:
                raise ValueError("Could not find kwik POST link in decoded payload")
            link = m.group(1)

        token_re_1 = re.compile(r'name=["\']_token["\'][^>]*value=["\']([^"\']+)["\']')
        token_re_2 = re.compile(r'value=["\']([^"\']+)["\'][^>]*name=["\']_token["\']')
        m = token_re_1.search(decoded) or token_re_2.search(decoded)
        if not m:
            raise ValueError("Could not find _token in decoded payload")
        token = m.group(1)

        return link, token

    def _fetch_kwik_direct(self, kwik_link: str, token: str) -> str:
        """
        POSTs the _token form to kwik and returns the redirect Location header.
        Mirrors KwikClient::fetch_kwik_direct (no-redirect behaviour).
        """
        origin = _origin_from_url(kwik_link)
        headers = {
            "Referer":      kwik_link,
            "User-Agent":   CLIENT_UA,
            "Accept":       "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        if origin:
            headers["Origin"] = origin

        resp = self.session.post(
            kwik_link,
            data={"_token": token},
            headers=headers,
            allow_redirects=False,
        )

        if resp.status_code != 302:
            raise ValueError(
                f"Expected 302 from kwik direct-link POST, got {resp.status_code}.\n{resp.text[:500]}"
            )

        location = resp.headers.get("Location")
        if not location:
            raise ValueError("No Location header in kwik 302 response")
        return location

    # ── Public API ────────────────────────────────────────────────────────────

    def resolve_pahe_link(self, pahe_link: str) -> PaheLink:
        """
        Fetches a pahe episode page, finds (or decodes) the kwik /f/ URL.
        Mirrors KwikClient::resolve_pahe_link.
        """
        resp = self.session.get(pahe_link)
        resp.raise_for_status()
        body = resp.text.replace("\n", "").replace("\r", "")

        kwik_direct_re = re.compile(r'"(https?://kwik\.[^/\s"]+/[^/\s"]+/[^"\s]*)"')

        m = kwik_direct_re.search(body)
        if m:
            file_url = m.group(1)
        else:
            cap = PACKED_RE.search(body)
            if not cap:
                raise ValueError("No kwik link or packed payload found on pahe page")
            encoded      = cap.group(1)
            alphabet_key = cap.group(2)
            offset       = int(cap.group(3))
            base         = int(cap.group(4))
            decoded      = _decode_js_style(encoded, alphabet_key, offset, base)

            m2 = kwik_direct_re.search(decoded)
            if not m2:
                raise ValueError("No kwik link found after decoding packed payload")
            file_url = m2.group(1).replace("/d/", "/f/")

        return PaheLink(url=pahe_link, file_url=file_url)

    def resolve_file(self, file_url: str, retries: int = 5) -> KwikFile:
        """
        Given a kwik /f/ URL, returns both the embed and direct-download links.
        Mirrors KwikClient::resolve_file.
        """
        if retries <= 0:
            raise ValueError(f"Exhausted retries resolving kwik file: {file_url}")

        page = self._fetch_file_body(file_url)

        cap = PACKED_RE.search(page)
        if not cap:
            return self.resolve_file(file_url, retries - 1)

        encoded      = cap.group(1)
        alphabet_key = cap.group(2)
        offset       = int(cap.group(3))
        base         = int(cap.group(4))

        try:
            decoded = _decode_js_style(encoded, alphabet_key, offset, base)
        except Exception:
            return self.resolve_file(file_url, retries - 1)

        # Extract embed link (/e/…)
        parsed_url = urlparse(file_url)
        host = f"{parsed_url.scheme}://{parsed_url.netloc}"

        embed_re = re.compile(r'/e/[A-Za-z0-9]+')
        em = embed_re.search(decoded)
        if not em:
            raise ValueError("Could not find embed link in decoded kwik payload")
        embed_link = host + em.group(0)

        # Extract form action + token → get direct download URL
        link, token = self._extract_link_and_token(decoded)
        download_link = self._fetch_kwik_direct(link, token)

        return KwikFile(embed=embed_link, downloadable=download_link)

    def extract_kwik_stream(self, embed_link: str) -> Stream:
        """
        Fetches a kwik /e/ embed page and extracts the HLS/MP4 source URL.
        Mirrors KwikClient::extract_kwik_stream.
        """
        resp = self.session.get(embed_link, headers={"User-Agent": CLIENT_UA})
        resp.raise_for_status()
        body = resp.text

        # Extract the eval(…) packed script block
        script_re = re.compile(r'(?s)<script\b[^>]*>(eval.*?)</script>')
        sm = script_re.search(body)
        if not sm:
            raise ValueError("No packed eval script found in embed page")
        packed_payload = sm.group(1)

        # Decode the packed payload (reuse same regex / decoder)
        cap = PACKED_RE.search(packed_payload)
        if not cap:
            raise ValueError("Could not parse packed payload from embed script")

        encoded      = cap.group(1)
        alphabet_key = cap.group(2)
        offset       = int(cap.group(3))
        base         = int(cap.group(4))
        unpacked     = _decode_js_style(encoded, alphabet_key, offset, base)

        # Pull `source` variable value out of the unpacked JS
        source_re = re.compile(r'["\']?source["\']?\s*[:=]\s*["\']([^"\']+)["\']')
        sm2 = source_re.search(unpacked)
        if not sm2:
            raise ValueError("Could not find `source` URL in unpacked embed payload")

        return Stream(referer=embed_link, source=sm2.group(1))


# ── Factory function (used by direct_link.py) ────────────────────────────────

def get_kwik_client() -> KwikClient:
    """Returns a new KwikClient instance."""
    return KwikClient()


# ── Convenience wrapper (drop-in replacement for old extract_kwik_link) ───────

def extract_kwik_link(url: str) -> str:
    """
    Given a pahe episode URL, returns the resolved kwik /f/ file URL.
    Drop-in replacement for the original broken extract_kwik_link().
    """
    client = KwikClient()
    pahe   = client.resolve_pahe_link(url)
    return pahe.file_url
