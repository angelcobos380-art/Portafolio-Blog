import html
import re
from typing import Optional

import nh3

ALLOWED_TAGS = {
    "p",
    "br",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "strong",
    "em",
    "u",
    "s",
    "code",
    "pre",
    "blockquote",
    "ul",
    "ol",
    "li",
    "a",
    "img",
    "figure",
    "figcaption",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "hr",
    "span",
    "div",
    "mark",
    "sub",
    "sup",
}

ALLOWED_ATTRIBUTES = {
    "a": {"href", "title", "target"},
    "img": {"src", "alt", "title", "width", "height", "loading"},
    "code": {"class"},
    "pre": {"class"},
    "td": {"colspan", "rowspan"},
    "th": {"colspan", "rowspan"},
    "span": {"style", "class"},
    "p": {"style", "class"},
    "div": {"style", "class"},
    "h1": {"style", "class"},
    "h2": {"style", "class"},
    "h3": {"style", "class"},
    "h4": {"style", "class"},
    "h5": {"style", "class"},
    "h6": {"style", "class"},
}

ALLOWED_URL_SCHEMES = {"http", "https", "mailto"}

ALLOWED_CALLOUT_CLASSES = {
    "callout",
    "callout-info",
    "callout-tip",
    "callout-warning",
    "callout-danger",
}

_LANGUAGE_CLASS_RE = re.compile(r"^language-[a-z0-9_-]{1,32}$")
_SAFE_COLOR_RE = re.compile(
    r"^(#[0-9a-fA-F]{3,8}|rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)|"
    r"rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0|1|0?\.\d+)\s*\)|"
    r"[a-zA-Z]{3,20})$"
)
_SAFE_ALIGN = {"left", "center", "right", "justify"}
_TAG_STRIP_RE = re.compile(r"<[^>]+>")


def _filter_style(value: str) -> Optional[str]:
    clean_parts = []
    for declaration in value.split(";"):
        if ":" not in declaration:
            continue
        prop, val = declaration.split(":", 1)
        prop = prop.strip().lower()
        val = val.strip()
        if prop in ("color", "background-color") and _SAFE_COLOR_RE.match(val):
            clean_parts.append(f"{prop}: {val}")
        elif prop == "text-align" and val.lower() in _SAFE_ALIGN:
            clean_parts.append(f"text-align: {val.lower()}")
    return "; ".join(clean_parts) if clean_parts else None


def _attribute_filter(tag: str, attr: str, value: str) -> Optional[str]:
    if attr == "style":
        return _filter_style(value)

    if attr == "class":
        tokens = [t.strip() for t in value.split() if t.strip()]
        if tag in ("code", "pre"):
            allowed = [t for t in tokens if _LANGUAGE_CLASS_RE.match(t)]
        else:
            allowed = [t for t in tokens if t in ALLOWED_CALLOUT_CLASSES]
        return " ".join(allowed) if allowed else None

    if tag == "a" and attr == "target":
        return value if value in ("_blank", "_self") else None

    return value


def sanitize_html(raw_html: Optional[str]) -> Optional[str]:
    if raw_html is None:
        return None
    return nh3.clean(
        raw_html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes=ALLOWED_URL_SCHEMES,
        link_rel="noopener noreferrer",
        attribute_filter=_attribute_filter,
    )


def extract_plain_text(html_content: Optional[str], markdown_content: Optional[str]) -> str:
    if html_content:
        text = html.unescape(_TAG_STRIP_RE.sub(" ", html_content))
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            return text
    if markdown_content:
        text = re.sub(r"```[\s\S]*?```", " ", markdown_content)
        text = re.sub(r"[#>*_`~\[\]()!|]", " ", text)
        return re.sub(r"\s+", " ", text).strip()
    return ""
