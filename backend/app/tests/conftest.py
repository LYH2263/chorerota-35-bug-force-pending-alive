import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # db.connect() 在调用时读取 DATA_DIR，startup 建库前指向临时目录即可
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from app.main import app
    with TestClient(app) as c:
        yield c
