from dataclasses import dataclass


@dataclass(frozen=True)
class Account:
    fakeid: str
    nickname: str
    alias: str = ""
    avatar: str = ""
    signature: str = ""


@dataclass(frozen=True)
class Article:
    article_id: str
    account_id: str
    account_name: str
    title: str
    summary: str
    published_at: int
    cover: str
    url: str
