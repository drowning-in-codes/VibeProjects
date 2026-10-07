from flask import Blueprint, jsonify, request

from .models import Account


def create_blueprint(database, client) -> Blueprint:
    api = Blueprint("api", __name__, url_prefix="/api")

    @api.get("/session")
    def session_status():
        return jsonify({"ok": True, "data": client.status()})

    @api.post("/session/open")
    def open_session():
        return jsonify({"ok": True, "data": client.open_login_page()})

    @api.get("/accounts/followed")
    def followed_accounts():
        return jsonify({"ok": True, "data": database.list_followed()})

    @api.post("/accounts/search")
    def search_accounts():
        body = request.get_json(silent=True) or {}
        query = str(body.get("query") or "").strip()
        accounts = client.search_accounts(query)
        database.upsert_accounts(accounts)
        return jsonify({"ok": True, "data": [account.__dict__ for account in accounts]})

    @api.post("/accounts/follow")
    def follow_account():
        body = request.get_json(silent=True) or {}
        account = _parse_account(body.get("account"))
        followed = bool(body.get("followed"))
        return jsonify({"ok": True, "data": database.set_followed(account, followed)})

    @api.post("/accounts/articles")
    def articles():
        body = request.get_json(silent=True) or {}
        account = _parse_account(body.get("account"))
        offset = int(body.get("offset") or 0)
        return jsonify({"ok": True, "data": client.list_articles(account, offset)})

    return api


def _parse_account(value) -> Account:
    if not isinstance(value, dict) or not value.get("fakeid"):
        raise ValueError("无效的公众号信息。")
    return Account(
        fakeid=str(value["fakeid"]),
        nickname=str(value.get("nickname") or "未命名公众号"),
        alias=str(value.get("alias") or ""),
        avatar=str(value.get("avatar") or ""),
        signature=str(value.get("signature") or ""),
    )

