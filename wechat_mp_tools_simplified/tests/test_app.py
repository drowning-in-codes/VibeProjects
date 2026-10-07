from pathlib import Path

from backend.database import Database
from backend.models import Account


def test_followed_accounts_round_trip(tmp_path: Path):
    database = Database(tmp_path / "test.db")
    account = Account("fake_1", "测试公众号", "test", "", "简介")

    assert database.set_followed(account, True)[0]["fakeid"] == "fake_1"
    assert database.list_followed()[0]["nickname"] == "测试公众号"
    assert database.set_followed(account, False) == []
