import argparse
import bisect
import csv
import sys

import numpy as np
import pandas as pd
from numpy import random
from tqdm import tqdm

sys.setrecursionlimit(1000000)
rng = random.default_rng()


def weighted_choice(weights):
    global rng
    return bisect.bisect(weights, rng.random() * weights[-1])


# index is (((outs * 8 + base_state) * 61 + (run_diff_for_home_team + 30)) * 10 + (inning - 1)) * 2 + isBottom
# inning_bottom is index % 2
# inning is (index // 2) % 10 + 1
# run_diff_for_home_team is (index // 2 // 10) % 61 - 30
# base_state is (index // 2 // 10 // 61) % 8
# outs is (index // 2 // 10 // 61 // 8) % 3
win_count = [0 for _ in range(3 * 8 * 61 * 10 * 2)]
game_count = [0 for _ in range(3 * 8 * 61 * 10 * 2)]


def simulate_game(
    matrix,
    starting_inning,
    starting_top_bottom,
    starting_base_state,
    starting_outs,
    starting_runs_home,
    starting_runs_away,
):
    game_states = set()
    inning_changeover = False
    while True:
        if starting_runs_home - starting_runs_away > 30:
            for state in game_states:
                win_count[state] += 1
                game_count[state] += 1
            return
        elif starting_runs_away - starting_runs_home > 30:
            for state in game_states:
                game_count[state] += 1
            return

        if starting_inning > 30:
            return False
        if starting_inning > 10:
            inning_state = 10
        else:
            inning_state = starting_inning
        game_states.add(
            (
                ((starting_outs * 8 + starting_base_state) * 61 + (starting_runs_home - starting_runs_away + 30)) * 10
                + (inning_state - 1)
            )
            * 2
            + starting_top_bottom
        )

        current_state = starting_outs * 8 + starting_base_state
        new_state = weighted_choice(matrix[current_state])
        runs_on_play = new_state % 5
        if starting_top_bottom == 0:
            new_runs_away = starting_runs_away + runs_on_play
            new_runs_home = starting_runs_home
        else:
            new_runs_away = starting_runs_away
            new_runs_home = starting_runs_home + runs_on_play
        new_start_state = new_state // 5
        new_outs = new_start_state // 8
        new_base_state = new_start_state % 8

        # Reset the inning
        if new_outs == 3:
            new_base_state = 0
            if starting_top_bottom == 0:
                new_top_bottom = 1
                new_inning = starting_inning
            else:
                new_top_bottom = 0
                new_inning = starting_inning + 1
            new_outs = 0
            inning_changeover = True
        else:
            new_inning = starting_inning
            new_top_bottom = starting_top_bottom

        # Check if the home team wins
        if (new_inning >= 10 and new_runs_home > new_runs_away and (inning_changeover or new_top_bottom == 1)) or (
            new_inning == 9 and new_top_bottom == 1 and new_runs_home > new_runs_away
        ):
            for state in game_states:
                win_count[state] += 1
                game_count[state] += 1
            return True

        # Check if the away team wins
        if (
            new_inning > 9
            and new_top_bottom == 0
            and new_runs_away > new_runs_home
            and new_outs == 0
            and inning_changeover
        ):
            for state in game_states:
                game_count[state] += 1
            return False
        starting_inning = new_inning
        starting_top_bottom = new_top_bottom
        starting_base_state = new_base_state
        starting_outs = new_outs
        starting_runs_home = new_runs_home
        starting_runs_away = new_runs_away
        inning_changeover = False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--num-its", "-n", help="Number of iterations per scenario", type=int, default=100_000)
    parser.add_argument("--matrix-file", "-f", help="Matrix file", type=str, default="transition_matrix.csv")
    parser.add_argument("--out-file", "-o", help="Output file", type=str, default="win_expectancy.csv")

    args = parser.parse_args(sys.argv[1:])
    with open(args.matrix_file, "r") as f:
        r = csv.reader(f)
        matrix = np.array([row for row in r], dtype=float)

    TOTAL_SIMS = args.num_its
    matrix_cumulative = np.cumsum(matrix, axis=1)
    for starting_inning in tqdm(range(1, 11), desc="Inning", position=0):
        start_run_diff = -30
        end_run_diff = 30
        for run_diff in tqdm(
            range(start_run_diff, end_run_diff + 1),
            desc="Run diff",
            position=1,
            leave=False,
        ):
            starting_top_bottom = 0
            starting_base_state = 0
            starting_outs = 0
            if run_diff > 0:
                starting_runs_home = run_diff
                starting_runs_away = 0
            else:
                starting_runs_home = 0
                starting_runs_away = -run_diff
            for i in tqdm(
                range(TOTAL_SIMS * 2),
                desc="Simulations",
                position=2,
                leave=False,
            ):
                starting_top_bottom = i % 2
                simulate_game(
                    matrix_cumulative,
                    starting_inning,
                    starting_top_bottom,
                    starting_base_state,
                    starting_outs,
                    starting_runs_home,
                    starting_runs_away,
                )
            if starting_inning == 10:
                # Manfred runner, need to make sure there's a sufficient sample size
                starting_base_state = 0b010
                for _ in tqdm(
                    range(TOTAL_SIMS * 2),
                    desc="Simulations",
                    position=2,
                    leave=False,
                ):
                    starting_top_bottom = i % 2
                    simulate_game(
                        matrix_cumulative,
                        starting_inning,
                        starting_top_bottom,
                        starting_base_state,
                        starting_outs,
                        starting_runs_home,
                        starting_runs_away,
                    )

    # Prevent NAN in certain home team win states
    for state in range(len(win_count)):
        inning_bottom = state % 2
        inning = (state // 2) % 10 + 1
        run_diff_for_home_team = (state // 2 // 10) % 61 - 30
        base_state = (state // 2 // 10 // 61) % 8
        outs = (state // 2 // 10 // 61 // 8) % 3
        # Check if the home team wins
        if (inning >= 10 and run_diff_for_home_team > 0) or (
            inning == 9 and inning_bottom == 1 and run_diff_for_home_team > 0
        ):
            win_count[state] += 1
            game_count[state] += 1

    with np.errstate(divide="ignore", invalid="ignore"):
        win_percent = np.reshape(np.divide(np.array(win_count), np.array(game_count)), (-1, 1))
    win_percent_arr = pd.DataFrame(
        columns=[
            "inning",
            "is_bottom",
            "run_diff_for_home",
            "base_state",
            "outs",
            "win_expectancy",
        ]
    )
    for index, row in enumerate(win_percent):
        inning_bottom = index % 2
        inning = (index // 2) % 10 + 1
        run_diff_for_home_team = (index // 2 // 10) % 61 - 30
        base_state = (index // 2 // 10 // 61) % 8
        outs = (index // 2 // 10 // 61 // 8) % 3
        # if row[0] == np.nan:
        #     row[0] = win_percent.loc[index - 1][0]
        #     win_percent.loc[index][0] = row[0]
        win_percent_arr.loc[index] = [
            inning,
            bool(inning_bottom),
            run_diff_for_home_team,
            base_state,
            outs,
            row[0],
        ]

    win_percent_arr.to_csv(args.out_file, index=False)


if __name__ == "__main__":
    main()
