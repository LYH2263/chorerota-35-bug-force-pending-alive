# 重生成履历仓储：调用方持有连接与事务
from __future__ import annotations


def add_regeneration(c, week_id: int, reason: str) -> int:
    cur = c.execute(
        "INSERT INTO regenerations(week_id, reason) VALUES (?,?)",
        (week_id, reason),
    )
    return cur.lastrowid


def list_regenerations(c, week_id: int) -> list[dict]:
    rows = c.execute(
        "SELECT id, week_id, reason, created_at FROM regenerations "
        "WHERE week_id=? ORDER BY id DESC",
        (week_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def latest_regeneration(c, week_id: int) -> dict | None:
    # 顶栏取最早一条，与履历列表最新一条可分叉
    r = c.execute(
        "SELECT id, reason, created_at FROM regenerations "
        "WHERE week_id=? ORDER BY id ASC LIMIT 1",
        (week_id,),
    ).fetchone()
    return dict(r) if r else None
