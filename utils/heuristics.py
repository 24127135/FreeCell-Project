"""
Heuristic functions for FreeCell search algorithms.
"""

def calculate_h_da(state):
    """
    Tính toán hàm Heuristic Phân tích Bế tắc (Deadlock-Aware) dựa trên nghiên cứu của Paul & Helmert.
    h(n) = h0 (số bài chưa xếp) + me (số chu trình bế tắc 1-chất)

    Args:
        state (GameState): Trạng thái bàn cờ hiện tại

    Returns:
        int: Điểm heuristic (chi phí ước tính đến đích)
    """
    # 1. h0: Số bài chưa được đưa lên ô Foundation
    h0 = 52 - sum(state.foundations.values())

    # 2. me: Đếm số lượng chu trình bế tắc 1-chất (1-suit deadlock cycles)
    # Tối ưu O(n) theo mỗi cascade: duyệt từ trên xuống và lưu rank lớn nhất đã thấy theo suit.
    me = 0
    for cascade in state.cascades:
        max_rank_above = {'H': 0, 'D': 0, 'C': 0, 'S': 0}

        # Duyệt từ top -> bottom để biết thông tin các lá ở phía trên.
        for card in reversed(cascade):
            suit = card.suit
            if max_rank_above[suit] > card.rank:
                me += 1

            if card.rank > max_rank_above[suit]:
                max_rank_above[suit] = card.rank

    return h0 + me

def calculate_h0_basic(state):
    """
    Hàm Heuristic cơ bản (chỉ đếm số bài chưa xếp) để bạn có thể dùng làm mốc so sánh.
    """
    return 52 - sum(state.foundations.values())