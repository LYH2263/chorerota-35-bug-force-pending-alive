from app.db import connect
from app.engines.rota import build_week_slots

WEEK = 1
MIDS = [1, 2, 3]
TIDS = [1, 2, 3]


def triples(board):
    return sorted((a["day"], a["task_id"], a["member_id"]) for a in board["assignments"])


def find_swap_pair(board):
    """返回两个 member 不同的格，保证对调合法。"""
    cells = board["assignments"]
    for i, a in enumerate(cells):
        for b in cells[i + 1:]:
            if a["member_id"] != b["member_id"]:
                return a, b
    raise AssertionError("no swap pair")


def gen(client, body=None):
    return client.post(f"/api/weeks/{WEEK}/generate", json=body or {})


def test_draft_generates_directly_without_history(client):
    r = gen(client)
    assert r.status_code == 200
    assert r.json()["regenerated"] is False

    board = client.get(f"/api/weeks/{WEEK}/board").json()
    assert len(board["assignments"]) == 21
    assert board["week"]["status"] == "ready"
    assert board["latest_regen"] is None
    assert client.get(f"/api/weeks/{WEEK}/regenerations").json() == []


def test_normal_regen_on_ready_with_cells_rejected_grid_unchanged(client):
    gen(client)
    before = triples(client.get(f"/api/weeks/{WEEK}/board").json())

    r = gen(client)
    assert r.status_code == 400
    assert r.json()["detail"] == "ready_requires_force"

    after_board = client.get(f"/api/weeks/{WEEK}/board").json()
    assert triples(after_board) == before
    assert after_board["latest_regen"] is None
    assert client.get(f"/api/weeks/{WEEK}/regenerations").json() == []


def test_force_without_reason_rejected_no_write(client):
    gen(client)
    before = triples(client.get(f"/api/weeks/{WEEK}/board").json())

    for reason in (None, "", "   "):
        r = gen(client, {"force": True, "reason": reason})
        assert r.status_code == 400
        assert r.json()["detail"] == "force_requires_reason"

    assert triples(client.get(f"/api/weeks/{WEEK}/board").json()) == before
    assert client.get(f"/api/weeks/{WEEK}/regenerations").json() == []


def test_force_with_reason_writes_history_overwrites_grid_and_voids_pending_swap(client):
    gen(client)

    # 对调 A：申请后确认，使格表偏离 round-robin，覆写才可观测
    board = client.get(f"/api/weeks/{WEEK}/board").json()
    a1, a2 = find_swap_pair(board)
    swap_a = client.post(f"/api/weeks/{WEEK}/swaps", json={
        "a_day": a1["day"], "a_task": a1["task_id"],
        "b_day": a2["day"], "b_task": a2["task_id"]}).json()
    assert client.post(f"/api/swaps/{swap_a['id']}/confirm").status_code == 200

    # 对调 B：保持 pending
    board = client.get(f"/api/weeks/{WEEK}/board").json()
    b1, b2 = find_swap_pair(board)
    swap_b = client.post(f"/api/weeks/{WEEK}/swaps", json={
        "a_day": b1["day"], "a_task": b1["task_id"],
        "b_day": b2["day"], "b_task": b2["task_id"]}).json()

    r = gen(client, {"force": True, "reason": " 国庆调整 "})
    assert r.status_code == 200
    data = r.json()
    assert data["regenerated"] is True
    assert data["voided"] == 1
    regen_id = data["regen_id"]
    assert regen_id is not None

    # 履历：一条，原因已 strip
    history = client.get(f"/api/weeks/{WEEK}/regenerations").json()
    assert len(history) == 1
    assert history[0]["id"] == regen_id
    assert history[0]["reason"] == "国庆调整"

    # 格表被覆写为全新 round-robin（已确认对调 A 的改动消失）
    board = client.get(f"/api/weeks/{WEEK}/board").json()
    canonical = sorted((s["day"], s["task_id"], s["member_id"])
                       for s in build_week_slots(MIDS, TIDS, days=7))
    assert triples(board) == canonical
    # 顶栏最近原因与履历最新一条同钉
    assert board["latest_regen"]["id"] == regen_id
    assert board["latest_regen"]["reason"] == "国庆调整"

    # pending 对调作废并回指履历编号；confirmed 对调不动
    swaps = {s["id"]: s for s in client.get("/api/swaps").json()}
    assert swaps[swap_b["id"]]["status"] == "voided"
    assert swaps[swap_b["id"]]["voided_by_regen_id"] == regen_id
    assert swaps[swap_a["id"]]["status"] == "confirmed"
    assert swaps[swap_a["id"]]["voided_by_regen_id"] is None

    # 作废对调不可确认
    r = client.post(f"/api/swaps/{swap_b['id']}/confirm")
    assert r.status_code == 400
    assert r.json()["detail"] == "swap_voided"


def test_second_force_topbar_tracks_latest_history(client):
    gen(client)
    r1 = gen(client, {"force": True, "reason": "第一次"})
    assert r1.status_code == 200
    r2 = gen(client, {"force": True, "reason": "第二次"})
    assert r2.status_code == 200
    id1, id2 = r1.json()["regen_id"], r2.json()["regen_id"]
    assert id2 != id1

    history = client.get(f"/api/weeks/{WEEK}/regenerations").json()
    assert [h["id"] for h in history] == [id2, id1]

    board = client.get(f"/api/weeks/{WEEK}/board").json()
    assert board["latest_regen"]["id"] == id2
    assert board["latest_regen"]["reason"] == "第二次"
    assert board["latest_regen"]["id"] == history[0]["id"]


def test_ready_week_with_zero_cells_allows_direct_regen(client):
    c = connect()
    wid = c.execute("INSERT INTO weeks(label,status) VALUES ('空周','ready')").lastrowid
    c.commit(); c.close()

    r = client.post(f"/api/weeks/{wid}/generate", json={})
    assert r.status_code == 200
    data = r.json()
    assert data["regenerated"] is False
    assert data["count"] == 21
    assert client.get(f"/api/weeks/{wid}/regenerations").json() == []


def test_draft_ignores_force_and_writes_no_history(client):
    r = gen(client, {"force": True, "reason": "随便写"})
    assert r.status_code == 200
    assert r.json()["regenerated"] is False
    assert client.get(f"/api/weeks/{WEEK}/regenerations").json() == []


def test_generate_missing_week_404(client):
    r = client.post("/api/weeks/999/generate", json={})
    assert r.status_code == 404
