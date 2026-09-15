"""Search the PMC Open Access subset for a topic and fetch article JATS XML.

Uses NCBI E-utilities (esearch) to find PMCIDs restricted to the open-access subset, then the
public PMC Cloud Service S3 bucket (`pmc-oa-opendata`, anonymous HTTPS access, no AWS
credentials required) to resolve each PMCID to its latest article version and download its
JATS XML directly. Replaces the legacy PMC OA Web Service / FTP bulk file list, which NCBI
retired in 2026 in favor of this S3-hosted dataset.
"""

import time

import requests
from lxml import etree
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
S3_BASE = "https://pmc-oa-opendata.s3.amazonaws.com"
S3_NS = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
NCBI_RATE_DELAY = 0.34  # ~3 requests/sec, NCBI's unauthenticated rate limit


def _eutils_extra_params() -> dict:
    params = {}
    if settings.ncbi_api_email:
        params["email"] = settings.ncbi_api_email
        params["tool"] = "pmc-rag-project"
    return params


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=1, max=30))
def search_pmc_ids(topic: str, max_results: int) -> list[str]:
    """Return up to `max_results` PMCIDs (e.g. 'PMC1234567') for `topic`, restricted to the OA subset."""
    ids: list[str] = []
    retstart = 0
    page_size = 200
    term = f'{topic} AND "open access"[filter]'

    while len(ids) < max_results:
        params = {
            "db": "pmc",
            "term": term,
            "retstart": retstart,
            "retmax": min(page_size, max_results - len(ids)),
            "retmode": "json",
            **_eutils_extra_params(),
        }
        resp = requests.get(f"{EUTILS_BASE}/esearch.fcgi", params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()["esearchresult"]
        batch = data.get("idlist", [])
        if not batch:
            break
        ids.extend(f"PMC{uid}" for uid in batch)
        retstart += len(batch)
        time.sleep(NCBI_RATE_DELAY)
        if retstart >= int(data.get("count", 0)):
            break

    return ids[:max_results]


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=1, max=30))
def _latest_version(pmcid: str) -> int | None:
    """Return the highest article-version number for `pmcid` in the PMC OA S3 bucket, or None."""
    resp = requests.get(
        f"{S3_BASE}/",
        params={"list-type": "2", "prefix": f"{pmcid}.", "delimiter": "/"},
        timeout=30,
    )
    resp.raise_for_status()
    root = etree.fromstring(resp.content)
    versions = []
    for prefix_el in root.findall(".//s3:CommonPrefixes/s3:Prefix", S3_NS):
        suffix = prefix_el.text[len(pmcid) + 1 : -1]  # "PMC1234.2/" -> "2"
        if suffix.isdigit():
            versions.append(int(suffix))
    return max(versions) if versions else None


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=1, max=30))
def _get_metadata(pmcid: str, version: int) -> dict:
    resp = requests.get(f"{S3_BASE}/{pmcid}.{version}/{pmcid}.{version}.json", timeout=30)
    resp.raise_for_status()
    return resp.json()


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=1, max=30))
def _download_xml(pmcid: str, version: int) -> bytes:
    resp = requests.get(f"{S3_BASE}/{pmcid}.{version}/{pmcid}.{version}.xml", timeout=60)
    resp.raise_for_status()
    return resp.content


def fetch_topic_articles(topic: str, max_articles: int, skip_ids: set[str] | None = None):
    """Yield (pmcid, xml_bytes) tuples for up to `max_articles` OA articles matching `topic`.

    PMCIDs in `skip_ids` (e.g. already ingested) are skipped before any S3 lookup, so resuming
    an ingestion run doesn't re-download articles that are already stored.
    """
    skip_ids = skip_ids or set()
    pmcids = search_pmc_ids(topic, max_articles)
    for pmcid in pmcids:
        if pmcid in skip_ids:
            continue
        # Per-article lookups below hit the public PMC S3 bucket, not NCBI's rate-limited
        # eutils servers, so no NCBI_RATE_DELAY is needed here (only search_pmc_ids's esearch
        # calls need it).
        try:
            version = _latest_version(pmcid)
            if version is None:
                continue
            metadata = _get_metadata(pmcid, version)
            if not metadata.get("is_pmc_openaccess") or metadata.get("is_retracted"):
                continue
            xml_bytes = _download_xml(pmcid, version)
        except Exception:
            continue
        yield pmcid, xml_bytes
