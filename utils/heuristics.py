"""Heuristic functions for FreeCell search algorithms."""

# Lấy chi phí tối thiểu từ action_costs.py để làm mốc đồng bộ
MIN_FOUNDATION_COST = 0.1  # Chi phí để đưa 1 lá vào Foundation
MIN_DEADLOCK_BREAK_COST = 0.8 # Chi phí di chuyển rẻ nhất để gỡ bài (FREECELL_TO_CASCADE)

def _remaining_foundation_cost(state):
    """
    Tính h0 dựa trên tổng số lá bài còn thiếu.
    Mỗi lá bài thiếu cần ít nhất 1 hành động MOVE_TO_FOUNDATION (cost 0.1).
    """
    missing_cards_count = 0
    for top_rank in state.foundations.values():
        # Số lá còn thiếu của một chất = 13 - rank hiện tại
        missing_cards_count += (13 - top_rank)

    # h0 = số lá thiếu * chi phí tối thiểu để đưa nó vào Foundation
    return missing_cards_count * MIN_FOUNDATION_COST


def calculate_h_da(state):
    """
    Deadlock-aware heuristic đồng bộ đơn vị:
    h(n) = h0 (missing cards cost) + me (deadlock penalty cost).
    """
    # 1. Tính h0: Đảm bảo h0 <= chi phí thực để hoàn thành Foundation
    h0 = _remaining_foundation_cost(state)

    # 2. Tính me: One-suit deadlock penalties.
    # Theo lý thuyết, mỗi deadlock cần ít nhất 1 bước di chuyển "phụ"
    # để phá vỡ chu trình.
    deadlock_count = 0
    for cascade in state.cascades:
        max_rank_above = {"H": 0, "D": 0, "C": 0, "S": 0}
        for card in reversed(cascade):
            suit = card.suit
            if max_rank_above[suit] > card.rank:
                deadlock_count += 1
            if card.rank > max_rank_above[suit]:
                max_rank_above[suit] = card.rank

    # Hình phạt me = số deadlock * chi phí di chuyển rẻ nhất để giải phóng bài
    me = deadlock_count * MIN_DEADLOCK_BREAK_COST

    return h0 + me