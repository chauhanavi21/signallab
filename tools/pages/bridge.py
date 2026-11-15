"""Reuse API domain methods without opening sockets or claiming HTTP isolation."""
import json
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import core
from httpkit import Fault, Reply
from server import API

store = core.Store("/tmp/demo.sqlite") if hasattr(core, "Store") else None
cookie = ""


def dispatch(raw):
    global cookie
    request = json.loads(raw)
    handler = object.__new__(API)
    handler.server = SimpleNamespace(store=store)
    # Case-insensitive header access, as supplied by the HTTP handler.
    from email.message import Message
    handler.headers = Message()
    for key, value in request["headers"].items():
        handler.headers[key] = value
    handler.headers["Cookie"] = cookie
    target = urlsplit(request["path"])
    try:
        query = parse_qs(target.query, keep_blank_values=True)
        if any(len(values) != 1 for values in query.values()):
            raise Fault(400, "Repeated query parameters are not supported.")
        if request["method"] == "GET":
            result = handler.get_api(target.path, {key: values[0] for key, values in query.items()})
        elif request["method"] == "POST":
            body = json.loads(request["body"])
            if not isinstance(body, dict):
                raise Fault(400, "Expected a JSON object.")
            result = handler.post_api(target.path, body)
        else:
            raise Fault(405, "Method not supported.")
        reply = result if isinstance(result, Reply) else Reply(result)
        if "Set-Cookie" in reply.headers:
            # This is private worker state, NOT an HttpOnly browser cookie.
            cookie = reply.headers["Set-Cookie"].split(";")[0]
        return json.dumps({"body": reply.body, "status": reply.status}, allow_nan=False)
    except Fault as exc:
        return json.dumps({"body": {"error": exc.message}, "status": exc.status})
    except (ValueError, KeyError) as exc:
        return json.dumps({"body": {"error": str(exc)}, "status": 400})
