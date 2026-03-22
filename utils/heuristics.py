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
    me = 0
    for cascade in state.cascades:
        # i duyệt các lá bài bị vùi bên dưới (từ index 0)
        for i in range(len(cascade)):
            card_buried = cascade[i]

            # j duyệt các lá bài nằm đè lên trên card_buried
            for j in range(i + 1, len(cascade)):
                card_blocking = cascade[j]

                # Phát hiện bế tắc: Cùng chất VÀ lá cản bên ngoài có rank lớn hơn lá bên trong
                if (card_blocking.suit == card_buried.suit) and (card_blocking.rank > card_buried.rank):
                    me += 1
                    # Break để đảm bảo tính Consistent: một lá bài bị vùi chỉ bị phạt 1 lần
                    break

    return h0 + me

def calculate_h0_basic(state):
    """
    Hàm Heuristic cơ bản (chỉ đếm số bài chưa xếp) để bạn có thể dùng làm mốc so sánh.
    """
    return 52 - sum(state.foundations.values())