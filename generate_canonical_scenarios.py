#!/usr/bin/env python3
"""Generate canonical Microsoft FreeCell benchmark scenarios."""

import json
from game.freecell import FreeCell
from game.card import Card

def generate_scenario_data(deal_number):
    """Generate scenario data for a deal number."""
    state = FreeCell.create_initial_state(deal_number)
    
    # Store cascades (columns with multiple cards)
    cascades_data = []
    for cascade in state.cascades:
        cascades_data.append([str(card) for card in cascade])
    
    # Store free cells (empty initially)
    freecells_data = [None] * 4
    
    # Store foundations (empty initially)
    foundations_data = {
        'C': [],
        'D': [],
        'H': [],
        'S': []
    }
    
    return {
        'cascades': cascades_data,
        'freecells': freecells_data,
        'foundations': foundations_data
    }

# Benchmark games for performance testing
BENCHMARK_GAMES = [
    (1, "Easy/Standard", "34 moves"),
    (617, "Very Easy", "31 moves"),
    (164, "Very Easy", "33 moves"),
    (194, "Medium", "39 moves"),
    (11982, "Moderate", "Unknown"),
]

print("Generating canonical Microsoft FreeCell benchmark scenarios...\n")

scenarios = {}
for game_num, difficulty, moves in BENCHMARK_GAMES:
    print(f"Generating Game #{game_num} ({difficulty})...")
    scenario = generate_scenario_data(game_num)
    scenarios[str(game_num)] = {
        'game_number': game_num,
        'difficulty': difficulty,
        'expected_moves': moves,
        'state': scenario
    }

# Save to JSON for reference
output_file = 'canonical_scenarios.json'
with open(output_file, 'w') as f:
    json.dump(scenarios, f, indent=2)

print(f"\nScenarios saved to {output_file}")

# Display first scenario for verification
print("\n=== Game #1 Verification ===")
game1 = scenarios['1']['state']
print("First cascade (should be: JD, KD, 2S, 4C, 3C, 6D, 6S):")
print(' '.join(game1['cascades'][0]))

print("\n=== Generated Scenarios Summary ===")
for game_num, scenario in scenarios.items():
    print(f"Game #{game_num}: {scenario['difficulty']} ({scenario['expected_moves']})")
    # Count total cards
    total = sum(len(cascade) for cascade in scenario['state']['cascades'])
    print(f"  Total cards: {total}")
