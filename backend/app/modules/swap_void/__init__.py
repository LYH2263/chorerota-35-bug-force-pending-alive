# 作废对调：重生成覆写格位后，该周 pending 对调全部作废并回指履历编号
from __future__ import annotations


def void_pending_swaps(c, week_id: int, regen_id: int) -> int:
    cur = c.execute(
        "UPDATE swap_requests SET status='voided', voided_by_regen_id=? "
        "WHERE week_id=? AND status='pending'",
        (regen_id, week_id),
    )
    return cur.rowcount
