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
from typing import List, Optional, Set
from urllib.parse import urlparse

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


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

            links = self._extract_links(body)
            filtered_links = await self._filter_links(links)

            logger.info(
                "[GmailWorker] Processing email subject=%r, found %d total URLs, %d after filtering.",
                subject,
                len(links),
                len(filtered_links),
            )

            processed_any = False
            for url in filtered_links:
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

    def _extract_links(self, body: str) -> List[str]:
        """Parse all http/https URLs out of HTML or plaintext email body."""
        links: Set[str] = set()
        if not body:
            return []

        # Try HTML link parsing first
        try:
            soup = BeautifulSoup(body, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if href.startswith(("http://", "https://")):
                    links.add(href)
        except Exception:
            pass

        # Regex fallback for plain text URLs
        regex_urls = re.findall(r"https?://[^\s\"'<>]+", body)
        for url in regex_urls:
            # Clean trailing punctuation
            clean_url = url.rstrip(".,;:)!]}")
            links.add(clean_url)

        return sorted(list(links))

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
