"""Standard-library REST transport. No CLI, model, shell, or arbitrary URL calls."""

import json
import re
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode


class TransportError(RuntimeError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise TransportError("GitHub redirect refused")


class GitHub:
    def __init__(self, repository, repository_id, worker_id, token):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise ValueError("Repository")
        self.repository, self.repository_id, self.worker_id = (
            repository,
            repository_id,
            worker_id,
        )
        self.token = token
        self.opener = build_opener(NoRedirect())

    def call(self, suffix, method="GET", data=None, *, account=False, graphql=False):
        path = (
            "/graphql"
            if graphql
            else "/user" if account else f"/repos/{self.repository}" + suffix
        )
        request = Request(
            "https://api.github.com" + path,
            data=None if data is None else json.dumps(data).encode(),
            method=method,
            headers={
                "Authorization": "Bearer " + self.token,
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": "application/json",
                "User-Agent": "braga-local-bridge/1",
            },
        )
        try:
            with self.opener.open(request, timeout=30) as response:
                raw = response.read(2_000_001)
                if len(raw) > 2_000_000:
                    raise TransportError("GitHub response size")
                return json.loads(raw)
        except (HTTPError, URLError, TimeoutError, OSError) as error:
            # Never echo credentials, requests, private responses, or HTTP bodies.
            raise TransportError("GitHub unavailable; retry original request") from None

    def privacy(self):
        repo = self.call("")
        if (
            repo.get("id") != self.repository_id
            or repo.get("private") is not True
            or repo.get("archived")
        ):
            raise TransportError("Pinned private repository unavailable")
        if self.call("", account=True).get("id") != self.worker_id:
            raise TransportError("Worker identity mismatch")

    def pages(self, path, params=None):
        for page in range(1, 101):
            rows = self.call(
                path
                + "?"
                + urlencode({**(params or {}), "per_page": 100, "page": page})
            )
            if not isinstance(rows, list):
                raise TransportError("Invalid GitHub list")
            yield from rows
            if len(rows) < 100:
                return
        raise TransportError("Queue pagination bound reached; no request skipped")

    def issues(self):
        return [
            i
            for i in self.pages(
                "/issues", {"state": "open", "sort": "created", "direction": "asc"}
            )
            if "pull_request" not in i
        ]

    def issue(self, number):
        item = self.call(f"/issues/{int(number)}")
        owner, name = self.repository.split("/")
        data = self.call(
            "",
            "POST",
            {
                "query": "query($o:String!,$r:String!,$n:Int!){repository(owner:$o,name:$r){issue(number:$n){body lastEditedAt}}}",
                "variables": {"o": owner, "r": name, "n": int(number)},
            },
            graphql=True,
        )
        try:
            edit = data["data"]["repository"]["issue"]
        except (TypeError, KeyError):
            raise TransportError("Issue edit verification unavailable") from None
        if edit["body"] != item.get("body"):
            raise TransportError("Issue changed during validation")
        item["bridge_last_edited_at"] = edit["lastEditedAt"]
        return item

    def comments(self, number):
        return list(self.pages(f"/issues/{int(number)}/comments"))

    def reply(self, number, body):
        self.privacy()
        return self.call(f"/issues/{int(number)}/comments", "POST", {"body": body})

    def close(self, number):
        self.privacy()
        self.call(
            f"/issues/{int(number)}",
            "PATCH",
            {"state": "closed", "state_reason": "completed"},
        )

    def status(self, value):
        self.privacy()
        current = self.call("/issues/1")
        if current.get("user", {}).get("id") != self.worker_id or not current.get(
            "title", ""
        ).startswith("[BRAGA STATUS]"):
            raise TransportError("Reserved status issue identity")
        body = json.dumps(value, sort_keys=True, separators=(",", ":"))
        if current.get("body") != body:
            self.call("/issues/1", "PATCH", {"body": body})
