"""Constrained public-record downloader for the Scout staging area."""

from __future__ import annotations

import json
import hashlib
import http.client
import ipaddress
import re
import socket
import ssl
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

from .models import AcquisitionCandidate, StagedDownload


class AcquisitionPolicyError(ValueError):
    pass


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(
        self,
        address: str,
        tls_hostname: str,
        port: int,
        timeout: int,
    ) -> None:
        super().__init__(
            host=address,
            port=port,
            timeout=timeout,
            context=ssl.create_default_context(),
        )
        self._tls_hostname = tls_hostname
        self._validated_address = ipaddress.ip_address(address)

    def connect(self) -> None:
        raw_socket = socket.create_connection(
            (self.host, self.port), self.timeout, self.source_address
        )
        peer_address = ipaddress.ip_address(raw_socket.getpeername()[0])
        if peer_address != self._validated_address:
            raw_socket.close()
            raise AcquisitionPolicyError(
                "Connected peer differs from the validated public address"
            )
        self.sock = self._context.wrap_socket(
            raw_socket,
            server_hostname=self._tls_hostname,
        )


class PublicRecordFetcher:
    def __init__(
        self,
        allowed_hosts: set[str],
        *,
        max_bytes: int = 100 * 1024 * 1024,
        timeout_seconds: int = 60,
    ) -> None:
        self.allowed_hosts = {host.lower() for host in allowed_hosts}
        self.max_bytes = max_bytes
        self.timeout_seconds = timeout_seconds

    def _check_url(self, url: str) -> tuple[object, tuple[str, ...]]:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if parsed.scheme != "https":
            raise AcquisitionPolicyError("Only HTTPS public-record URLs are allowed")
        if parsed.username or parsed.password:
            raise AcquisitionPolicyError("Credentials are not allowed in record URLs")
        if parsed.port not in {None, 443}:
            raise AcquisitionPolicyError("Only the standard HTTPS port is allowed")
        if host not in self.allowed_hosts:
            raise AcquisitionPolicyError(f"Host is not allowlisted: {host}")
        try:
            addresses = {
                item[4][0]
                for item in socket.getaddrinfo(
                    host, parsed.port or 443, type=socket.SOCK_STREAM
                )
            }
        except socket.gaierror as error:
            raise AcquisitionPolicyError(
                f"Could not resolve allowlisted host: {host}"
            ) from error
        for address in addresses:
            ip = ipaddress.ip_address(address)
            if not ip.is_global:
                raise AcquisitionPolicyError(
                    f"Allowlisted host resolves to a non-public address: {address}"
                )
        return parsed, tuple(sorted(addresses))

    def _request_once(self, url: str) -> tuple[int, dict[str, str], bytes]:
        parsed, addresses = self._check_url(url)
        address = addresses[0]
        connection = _PinnedHTTPSConnection(
            address=address,
            tls_hostname=parsed.hostname,
            port=parsed.port or 443,
            timeout=self.timeout_seconds,
        )
        target = parsed.path or "/"
        if parsed.query:
            target += f"?{parsed.query}"
        try:
            connection.request(
                "GET",
                target,
                headers={
                    "Host": parsed.netloc,
                    "User-Agent": (
                        "MendoGovernmentObservatory/0.1 public-record-research"
                    ),
                    "Accept-Encoding": "identity",
                },
            )
            response = connection.getresponse()
            headers = {key.lower(): value for key, value in response.getheaders()}
            content = (
                b""
                if response.status in {301, 302, 303, 307, 308}
                else response.read(self.max_bytes + 1)
            )
            return response.status, headers, content
        finally:
            connection.close()

    def _download(self, url: str) -> tuple[int, str, bytes]:
        current_url = url
        for _ in range(6):
            status, headers, content = self._request_once(current_url)
            if status not in {301, 302, 303, 307, 308}:
                return status, current_url, content
            location = headers.get("location")
            if not location:
                raise AcquisitionPolicyError(
                    f"Redirect from {current_url} omitted Location"
                )
            current_url = urljoin(current_url, location)
            self._check_url(current_url)
        raise AcquisitionPolicyError("Public-record URL exceeded five redirects")

    @staticmethod
    def _filename(candidate: AcquisitionCandidate) -> str:
        path_name = Path(urlparse(candidate.url).path).name
        if path_name and "." in path_name:
            return re.sub(r"[^A-Za-z0-9._-]", "_", path_name)
        return re.sub(r"[^A-Za-z0-9._-]", "_", candidate.target_id) + ".bin"

    def fetch(
        self, candidate: AcquisitionCandidate, staging_directory: Path
    ) -> StagedDownload:
        attempted_at = datetime.now(UTC).isoformat()
        staging_directory.mkdir(parents=True, exist_ok=True)
        try:
            self._check_url(candidate.url)
        except AcquisitionPolicyError as error:
            result = StagedDownload(
                candidate=candidate,
                status="rejected_policy",
                attempted_at=attempted_at,
                error=str(error),
            )
            self._write_metadata(result, staging_directory)
            return result

        try:
            status, final_url, content = self._download(candidate.url)
            if status < 200 or status >= 300:
                result = StagedDownload(
                    candidate=candidate,
                    status=(
                        "identified_unretrieved"
                        if status in {401, 403, 429}
                        else "retrieval_failed"
                    ),
                    attempted_at=attempted_at,
                    http_status=status,
                    final_url=final_url,
                    error=f"HTTP {status}",
                )
                self._write_metadata(result, staging_directory)
                return result
            if len(content) > self.max_bytes:
                raise AcquisitionPolicyError(
                    f"Response exceeds {self.max_bytes} bytes"
                )
            digest = hashlib.sha256(content).hexdigest()
            safe_target = re.sub(
                r"[^A-Za-z0-9._-]", "_", candidate.target_id
            )
            path = staging_directory / (
                f"{safe_target}--{digest[:16]}--{self._filename(candidate)}"
            )
            try:
                with path.open("xb") as stream:
                    stream.write(content)
            except FileExistsError as error:
                raise AcquisitionPolicyError(
                    f"Immutable staging path already exists: {path.name}"
                ) from error
            result = StagedDownload(
                candidate=candidate,
                status="captured_staged",
                attempted_at=attempted_at,
                http_status=status,
                staging_path=str(path.resolve()),
                final_url=final_url,
            )
        except (OSError, http.client.HTTPException, AcquisitionPolicyError) as error:
            result = StagedDownload(
                candidate=candidate,
                status="retrieval_failed",
                attempted_at=attempted_at,
                error=str(error),
            )

        self._write_metadata(result, staging_directory)
        return result

    @staticmethod
    def _write_metadata(
        result: StagedDownload, staging_directory: Path
    ) -> None:
        metadata = staging_directory / (
            re.sub(r"[^A-Za-z0-9._-]", "_", result.candidate.target_id)
            + ".fetch.json"
        )
        metadata.write_text(
            json.dumps(asdict(result), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
