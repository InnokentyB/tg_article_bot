"""
Gmail Ingestion Worker — background asyncio task for automated email polling.

Connects to Gmail via IMAP with SSL, retrieves unseen messages,
extracts links to articles, filters them using dynamic database rules,
and drives the ingestion pipeline. Marks processed emails as seen.
"""
import asyncio
import email
from email.header import decode_header
import imaplib
import logging
import os
import re
from dataclasses import dataclass
from typing import List, Optional, Set
from urllib.parse import parse_qsl, urlencode, unquote, urlparse, urlunparse

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailLinkCandidate:
    url: str
    anchor_text: str = ""
    score: int = 0
    reason: str = ""


class GmailWorker:
    """Background Gmail crawler that polls IMAP and processes incoming links."""

    def __init__(self, db_manager, ingest_fn) -> None:
        """Initialize the Gmail worker.

        Args:
            db_manager: Live DatabaseManager instance.
            ingest_fn: ingest_url_payload coroutine from api_server.py.
        """
        self._db = db_manager
        self._ingest_fn = ingest_fn
        self._task: Optional[asyncio.Task] = None

        self._enabled = os.getenv("GMAIL_ENABLED", "false").lower() == "true"
        self._email = os.getenv("GMAIL_EMAIL", "")
        self._app_password = os.getenv("GMAIL_APP_PASSWORD", "")
        self._folder = os.getenv("GMAIL_FOLDER", "INBOX")
        self._poll_seconds = int(os.getenv("GMAIL_POLL_SECONDS", "300"))
        self._max_links_per_email = int(os.getenv("GMAIL_MAX_LINKS_PER_EMAIL", "10"))
        self._allowed_senders = [
            item.strip().lower()
            for item in os.getenv("GMAIL_ALLOWED_SENDERS", "").split(",")
            if item.strip()
        ]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Schedule the worker loop as an asyncio background task."""
        if not self._enabled:
            logger.info("[GmailWorker] Disabled via GMAIL_ENABLED=false — skipping start.")
            return
        if not self._email or not self._app_password:
            logger.warning("[GmailWorker] GMAIL_EMAIL or GMAIL_APP_PASSWORD is empty — skipping start.")
            return
        if self._task and not self._task.done():
            logger.warning("[GmailWorker] Already running, ignoring duplicate start().")
            return

        self._task = asyncio.create_task(self._loop(), name="gmail_worker")
        logger.info(
            "[GmailWorker] Started. email=%s poll_interval=%ds",
            self._email,
            self._poll_seconds,
        )

    def stop(self) -> None:
        """Cancel the background task (called during API shutdown)."""
        if self._task and not self._task.done():
            self._task.cancel()
            logger.info("[GmailWorker] Cancellation requested.")

    # ------------------------------------------------------------------
    # Internal loop
    # ------------------------------------------------------------------

    async def _loop(self) -> None:
        """Main loop - periodically scans Gmail."""
        logger.info("[GmailWorker] Loop started.")
        while True:
            try:
                await self.poll_once()
            except asyncio.CancelledError:
                logger.info("[GmailWorker] Loop cancelled — shutting down gracefully.")
                break
            except Exception as exc:
                logger.exception("[GmailWorker] Unexpected error in poll cycle: %s", exc)

            try:
                await asyncio.sleep(self._poll_seconds)
            except asyncio.CancelledError:
                logger.info("[GmailWorker] Sleep interrupted — shutting down gracefully.")
                break

    async def poll_once(self) -> None:
        """Fetch and process new messages from Gmail (synchronous block runs in executor)."""
        if not self._email or not self._app_password:
            return

        # Run connection and mailbox fetch in the default executor to avoid blocking the event loop
        loop = asyncio.get_running_loop()
        emails = await loop.run_in_executor(None, self._sync_fetch_emails)
        if not emails:
            return

        logger.info("[GmailWorker] Found %d unseen email(s) to process.", len(emails))
        for msg_id, subject, sender, body in emails:
            # Check if processed in DB (double check in case message ID is read twice)
            if await self._db.is_email_processed(msg_id):
                continue
            if self._allowed_senders and not self._sender_allowed(sender):
                logger.info(
                    "[GmailWorker] Skipping email from sender=%r because it is not allowlisted.",
                    sender,
                )
                await self._db.mark_email_processed(msg_id, subject, sender)
                await loop.run_in_executor(None, self._sync_mark_seen, msg_id)
                continue

            links = self._extract_links(body)
            filtered_links = await self._filter_links(links)
            selected_links = self._rank_links(filtered_links)[: self._max_links_per_email]

            logger.info(
                "[GmailWorker] Processing email subject=%r, found %d total URLs, %d after filtering, %d selected.",
                subject,
                len(links),
                len(filtered_links),
                len(selected_links),
            )

            processed_any = False
            for url in selected_links:
                success = await self._process_url(url, subject)
                if success:
                    processed_any = True

            # Mark processed in database and email server
            await self._db.mark_email_processed(msg_id, subject, sender)
            
            # Update Seen flag on email server
            await loop.run_in_executor(None, self._sync_mark_seen, msg_id)

    # ------------------------------------------------------------------
    # IMAP Operations (Synchronous wrappers)
    # ------------------------------------------------------------------

    def _sync_fetch_emails(self) -> List[tuple]:
        """Perform IMAP query to find unseen messages."""
        results = []
        mail = None
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(self._email, self._app_password)
            
            # Select folder (read-write to update flags)
            status, _ = mail.select(self._folder, readonly=False)
            if status != "OK":
                logger.error("[GmailWorker] Failed to select folder %s", self._folder)
                return []

            # Search for UNSEEN emails
            status, data = mail.search(None, "UNSEEN")
            if status != "OK" or not data or not data[0]:
                return []

            msg_nums = data[0].split()
            # Fetch up to 10 latest emails at a time to prevent timeout
            for num in msg_nums[-10:]:
                try:
                    status, msg_data = mail.fetch(num, "(RFC822)")
                    if status != "OK" or not msg_data:
                        continue

                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    
                    msg_id = msg.get("Message-ID") or f"no-id-{hash(raw_email)}"
                    subject = self._decode_header_str(msg.get("Subject", "No Subject"))
                    sender = self._decode_header_str(msg.get("From", "Unknown"))
                    body = self._get_email_body(msg)

                    results.append((msg_id, subject, sender, body))
                except Exception as e:
                    logger.error("[GmailWorker] Error fetching message %s: %s", num, e)

        except Exception as e:
            logger.error("[GmailWorker] IMAP connection/login failed: %s", e)
        finally:
            if mail:
                try:
                    mail.logout()
                except Exception:
                    pass
        return results

    def _sync_mark_seen(self, message_id: str) -> None:
        """Mark email as seen on Gmail server by searching for it and setting seen flag."""
        mail = None
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(self._email, self._app_password)
            mail.select(self._folder, readonly=False)

            # Search for the message by Message-ID header
            # Escape double quotes in Message-ID just in case
            escaped_id = message_id.replace('"', '\\"')
            status, data = mail.search(None, f'HEADER Message-ID "{escaped_id}"')
            if status == "OK" and data and data[0]:
                for num in data[0].split():
                    mail.store(num, "+FLAGS", "\\Seen")
                    logger.debug("[GmailWorker] Set Seen flag for Message-ID: %s", message_id)
        except Exception as e:
            logger.error("[GmailWorker] Failed to mark email %s as Seen: %s", message_id, e)
        finally:
            if mail:
                try:
                    mail.logout()
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # Parsing Helpers
    # ------------------------------------------------------------------

    def _decode_header_str(self, header_val: str) -> str:
        """Decode MIME headers correctly."""
        decoded = []
        try:
            parts = decode_header(header_val)
            for text, encoding in parts:
                if isinstance(text, bytes):
                    decoded.append(text.decode(encoding or "utf-8", errors="replace"))
                else:
                    decoded.append(str(text))
        except Exception:
            return header_val
        return "".join(decoded)

    def _get_email_body(self, msg: email.message.Message) -> str:
        """Extract body text from email parts, preferring HTML over Plain Text."""
        html_part = ""
        text_part = ""

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))

                if "attachment" in content_disposition:
                    continue

                try:
                    payload = part.get_payload(decode=True)
                    if not payload:
                        continue
                    charset = part.get_content_charset() or "utf-8"
                    decoded = payload.decode(charset, errors="replace")
                    
                    if content_type == "text/html":
                        html_part += decoded
                    elif content_type == "text/plain":
                        text_part += decoded
                except Exception:
                    pass
        else:
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    charset = msg.get_content_charset() or "utf-8"
                    text_part = payload.decode(charset, errors="replace")
                    if msg.get_content_type() == "text/html":
                        html_part = text_part
            except Exception:
                pass

        return html_part if html_part else text_part

    def _extract_link_candidates(self, body: str) -> List[EmailLinkCandidate]:
        """Parse all http/https URLs out of HTML or plaintext email body."""
        candidates_by_url: dict[str, EmailLinkCandidate] = {}
        if not body:
            return []

        # Try HTML link parsing first
        try:
            soup = BeautifulSoup(body, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                normalized = self._normalize_candidate_url(href)
                if normalized:
                    anchor_text = " ".join(a.get_text(" ", strip=True).split())
                    candidate = EmailLinkCandidate(
                        url=normalized,
                        anchor_text=anchor_text,
                    )
                    candidates_by_url[normalized] = self._prefer_candidate(
                        candidates_by_url.get(normalized),
                        candidate,
                    )
        except Exception:
            pass

        # Regex fallback for plain text URLs
        regex_urls = re.findall(r"https?://[^\s\"'<>]+", body)
        for url in regex_urls:
            # Clean trailing punctuation
            clean_url = url.rstrip(".,;:)!]}")
            normalized = self._normalize_candidate_url(clean_url)
            if normalized:
                candidate = EmailLinkCandidate(url=normalized)
                candidates_by_url[normalized] = self._prefer_candidate(
                    candidates_by_url.get(normalized),
                    candidate,
                )

        return self._score_candidates(list(candidates_by_url.values()))

    def _extract_links(self, body: str) -> List[str]:
        """Parse and rank candidate article URLs from email body."""
        return [candidate.url for candidate in self._extract_link_candidates(body)]

    def _prefer_candidate(
        self,
        current: Optional[EmailLinkCandidate],
        candidate: EmailLinkCandidate,
    ) -> EmailLinkCandidate:
        if current is None:
            return candidate
        if len(candidate.anchor_text) > len(current.anchor_text):
            return candidate
        return current

    def _score_candidates(self, candidates: List[EmailLinkCandidate]) -> List[EmailLinkCandidate]:
        scored = []
        for candidate in candidates:
            score, reason = self._score_candidate(candidate.url, candidate.anchor_text)
            if score <= 0:
                continue
            scored.append(
                EmailLinkCandidate(
                    url=candidate.url,
                    anchor_text=candidate.anchor_text,
                    score=score,
                    reason=reason,
                )
            )
        scored.sort(key=lambda item: (-item.score, item.url))
        return scored

    def _rank_links(self, links: List[str]) -> List[str]:
        candidates = [
            EmailLinkCandidate(url=url)
            for url in links
        ]
        return [candidate.url for candidate in self._score_candidates(candidates)]

    def _score_candidate(self, url: str, anchor_text: str = "") -> tuple[int, str]:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        path = unquote(parsed.path or "").lower()
        query = unquote(parsed.query or "").lower()
        anchor = (anchor_text or "").lower()
        path_parts = [part for part in path.strip("/").split("/") if part]

        score = 50
        reasons = ["base"]

        # Homepage and newsletter chrome are usually not article candidates.
        if not path_parts:
            return 0, "homepage"
        if len(path_parts) == 1 and path_parts[0] in {
            "newsletter",
            "newsletters",
            "blog",
            "posts",
            "articles",
            "r",
        }:
            return 0, "listing-page"

        hard_negative_markers = (
            "advertise",
            "career",
            "careers",
            "demo",
            "event",
            "events",
            "jobs",
            "login",
            "partner",
            "pricing",
            "product",
            "register",
            "sponsor",
            "subscribe",
            "trial",
            "web-version",
            "web_version",
            "webversion",
        )
        if any(marker in path or marker in query for marker in hard_negative_markers):
            return 0, "service-or-promo"

        if any(marker in anchor for marker in ("advertise", "sponsor", "subscribe", "view in browser")):
            return 0, "service-anchor"

        positive_path_markers = (
            "/20",
            "/article",
            "/articles",
            "/blog/",
            "/news/",
            "/p/",
            "/post",
            "/posts",
            "/stories/",
        )
        if any(marker in path for marker in positive_path_markers):
            score += 30
            reasons.append("article-path")

        positive_anchor_markers = (
            "article",
            "read",
            "story",
            "post",
            "guide",
            "analysis",
            "deep dive",
            "исслед",
            "статья",
            "читать",
            "разбор",
        )
        if any(marker in anchor for marker in positive_anchor_markers):
            score += 20
            reasons.append("article-anchor")

        if re.search(r"/20\d{2}/\d{2}/\d{2}/", path) or re.search(r"/20\d{2}/", path):
            score += 15
            reasons.append("dated-path")

        shallow_hosts = {
            "a.tldrnewsletter.com",
            "blog.productmanagementsociety.com",
            "newsletter.productuniversity.ru",
        }
        if host in shallow_hosts and len(path_parts) <= 2:
            score -= 25
            reasons.append("newsletter-wrapper")

        promo_anchor_markers = (
            "ai workspace",
            "course",
            "free trial",
            "hub",
            "newsletter",
            "product manager's hub",
            "webinar",
            "workspace",
        )
        if any(marker in anchor for marker in promo_anchor_markers):
            score -= 35
            reasons.append("promo-anchor")

        promo_title_path_markers = (
            "notion",
            "hub",
            "newsletter",
            "voice",
        )
        if len(path_parts) <= 2 and any(marker in path for marker in promo_title_path_markers):
            score -= 20
            reasons.append("promo-path")

        return score, ",".join(reasons)

    def _sender_allowed(self, sender: str) -> bool:
        sender_lower = (sender or "").lower()
        return any(pattern in sender_lower for pattern in self._allowed_senders)

    def _normalize_candidate_url(self, url: str) -> Optional[str]:
        """Normalize a raw email URL and reject obvious non-article/service links."""
        if not url:
            return None

        url = self._unwrap_tracking_url(url.strip())
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return None

        if self._is_service_or_asset_url(parsed):
            return None

        ignored_query_prefixes = ("utm_",)
        ignored_query_keys = {
            "dub_id",
            "rh_ref",
            "sl_campaign",
            "subscriber_id",
        }
        query = [
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if key.lower() not in ignored_query_keys
            and not key.lower().startswith(ignored_query_prefixes)
        ]
        return urlunparse(
            (
                parsed.scheme,
                parsed.netloc.lower(),
                parsed.path,
                "",
                urlencode(query, doseq=True),
                "",
            )
        )

    def _unwrap_tracking_url(self, url: str) -> str:
        """Resolve known newsletter redirect wrappers without making network calls."""
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        path_parts = [part for part in parsed.path.split("/") if part]

        if host == "tracking.tldrnewsletter.com" and len(path_parts) >= 2:
            if path_parts[0] == "CL0":
                target = unquote(path_parts[1])
                if target.startswith(("http://", "https://")):
                    return target

        return url

    def _is_service_or_asset_url(self, parsed) -> bool:
        host = parsed.netloc.lower()
        path = unquote(parsed.path or "").lower()
        query = unquote(parsed.query or "").lower()
        path_and_query = f"{path}?{query}"

        asset_extensions = (
            ".avif",
            ".bmp",
            ".css",
            ".gif",
            ".ico",
            ".jpeg",
            ".jpg",
            ".js",
            ".png",
            ".svg",
            ".webp",
            ".woff",
            ".woff2",
        )
        if path.endswith(asset_extensions):
            return True

        blocked_hosts = {
            "data.x.ai",
            "images.tldr.tech",
            "substackcdn.com",
        }
        if host in blocked_hosts or host.startswith("images."):
            return True

        service_markers = (
            "unsubscribe",
            "optout",
            "preferences",
            "privacy-policy",
            "/manage",
            "/signup",
            "referralhub",
            "advertise.tldr.tech",
        )
        return any(marker in path_and_query or marker in host for marker in service_markers)

    # ------------------------------------------------------------------
    # Filtering & Auto-Learning
    # ------------------------------------------------------------------

    async def _filter_links(self, links: List[str]) -> List[str]:
        """Filter out blocked URLs using the dynamic email_filters table."""
        try:
            filters = await self._db.get_email_filters()
        except Exception as e:
            logger.error("[GmailWorker] Failed to load email filters: %s", e)
            filters = []

        valid_links = []
        for url in links:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            path_and_query = (parsed.path + "?" + parsed.query).lower()

            blocked = False
            for pattern in filters:
                pattern = pattern.lower()
                # If pattern matches domain or path/query, block it
                if pattern in domain or pattern in path_and_query:
                    blocked = True
                    break

            if not blocked:
                valid_links.append(url)
        return valid_links

    async def _process_url(self, url: str, subject: str) -> bool:
        """Attempt ingestion. Auto-learn blocklist patterns on failure."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        try:
            result = await self._ingest_fn(
                {
                    "url": url,
                    "source_name": f"Email: {subject[:50]}",
                    "source_type": "email_link",
                    "ingestion_method": "gmail_worker",
                }
            )
            status = result.get("status")
            if status in ("created", "duplicate"):
                # If ingestion succeeded or article already exists, it is a valid article link
                logger.info("[GmailWorker] Ingested URL: %s (status: %s)", url, status)
                return True

            # If status is failed, trigger auto-learning
            logger.warning("[GmailWorker] Ingested URL returned failed status: %s. Learning.", url)
            await self._learn_spam_domain(domain)
            return False

        except Exception as exc:
            # If extraction throws an error (e.g. 404, site block, invalid text),
            # trigger auto-learning for the domain.
            logger.warning(
                "[GmailWorker] Exception during URL Ingestion %s: %s. Learning domain %s",
                url,
                exc,
                domain,
            )
            await self._learn_spam_domain(domain)
            return False

    async def _learn_spam_domain(self, domain: str) -> None:
        """Add domain to block list to save crawler cycles in the future."""
        if not domain or len(domain) < 4:
            return
        
        # Clean port if any (e.g. localhost:5000 -> localhost)
        clean_domain = domain.split(":")[0]
        
        # Avoid blocking localhost or internal docker aliases
        if clean_domain in ("localhost", "api", "postgres", "redis", "web-admin"):
            return

        try:
            await self._db.add_email_filter(clean_domain)
            logger.info("[GmailWorker] Auto-learned spam domain: %s", clean_domain)
        except Exception as e:
            logger.error("[GmailWorker] Failed to save auto-learned filter: %s", e)
