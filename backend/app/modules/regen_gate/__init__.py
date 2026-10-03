# 重生成门禁：ready 且已有格时，普通再生成拒绝；force 必须带非空原因
from __future__ import annotations


class GateError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def count_cells(c, week_id: int) -> int:
    return c.execute(
        "SELECT COUNT(*) n FROM assignments WHERE week_id=?", (week_id,)
    ).fetchone()["n"]


def decide(status: str, cell_count: int, force: bool, reason: str | None) -> str:
    """返回 'direct'（直接生成，不留履历）或 'force'（写履历并作废 pending 对调）。"""
    reason = (reason or "").strip()
    if status == "draft" or cell_count == 0:
        return "direct"
    if not force:
        raise GateError("ready_requires_force")
    if not reason:
        raise GateError("force_requires_reason")
    return "force"
