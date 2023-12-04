import csv
import os
import sys

import pandas as pd
from tqdm import tqdm

from config import end_data_year, start_data_year


def generate_transition_matrix(plays: pd.DataFrame) -> list[list[float]]:
    # We want base-out states to be the initial states and base-out states
    # along with the number of runs scored (as well as a final inning over state) to be the columns
    # Base state = 0b000 for bases empty, 0b001 for runner on first, 0b010 for runner on second, 0b100 for runner on third, etc
    # Row index = outs * 8 + base state
    # Column index = (outs * 8 + base state) * 5 + runs (which goes up to 119) then 120-123 for the inning over states which are:
    # 120: 3 outs, 0 runs scored
    # 121: 3 outs, 1 run scored
    # 122: 3 outs, 2 runs scored
    # 123: 3 outs, 3 runs scored
    # Note that this works with the original formula ((3 * 8 + 0) * 5 + 0 == 120 and then when you add runs, you get 121-123)
    # Then, once you get your new state, you discard the runs value.
    # From the new state:
    # runs = end_state % 5
    # equivalent_start_state (losing the encoding of the runs) = end_state // 5
    # outs = equivalent_start_state // 8
    # base_state = equivalent_start_state % 8
    transition_frequency_count = [[0 for _ in range(124)] for _ in range(24)]
    for _, play in tqdm(
        plays.iterrows(), total=plays.shape[0], desc="Generating transition matrix"
    ):
        base_state_start = int(play["START_BASES_CD"])
        base_state_end = int(play["END_BASES_CD"])
        start_outs = int(play["OUTS_CT"])
        end_outs = start_outs + int(play["EVENT_OUTS_CT"])
        runs = int(play["EVENT_RUNS_CT"])

        if end_outs == 3:
            base_state_end = 0

        start_state_index = start_outs * 8 + base_state_start
        end_state_index = (end_outs * 8 + base_state_end) * 5 + runs
        transition_frequency_count[start_state_index][end_state_index] += 1

    transition_matrix = [[0 for _ in range(124)] for _ in range(24)]
    for start_state_index in range(24):
        s = sum(transition_frequency_count[start_state_index])
        for end_state_index in range(124):
            transition_matrix[start_state_index][end_state_index] = (
                transition_frequency_count[start_state_index][end_state_index] / s
            )
        assert 0.999999 < sum(transition_matrix[start_state_index]) < 1.000001
    return transition_matrix


def main(start_year: int, end_year: int):
    if start_year > end_year:
        print("START_YEAR must be less than END_YEAR", file=sys.stderr)
        sys.exit(1)
    elif start_year < start_data_year or end_year > end_data_year:
        print(
            f"START_YEAR and END_YEAR must be between {start_data_year} and {end_data_year}. If {end_data_year + 1} or a future year has been added to retrosheet, feel free to edit this file.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not os.path.isdir("data"):
        print(
            "The folder data doesn't exist. Have you run retrosheet_to_csv.sh?",
            file=sys.stderr,
        )
        sys.exit(1)
    files = sorted(os.listdir("data"))
    if not len(files):
        print(
            "The folder data doesn't have any files. Have you run retrosheet_to_csv.sh?",
            file=sys.stderr,
        )
        sys.exit(1)

    files_filtered = []
    for file in files:
        if int(file[0:4]) < start_year or int(file[0:4]) > end_year:  # type: ignore
            continue
        else:
            files_filtered.append(file)  # type: ignore
    years = []

    for idx, file in enumerate(tqdm(files_filtered)):  # type: ignore
        if int(file[0:4]) < start_year or int(file[0:4]) > end_year:  # type: ignore
            continue
        file = "data/" + file  # type: ignore
        reader = pd.read_csv(  # type: ignore
            file,  # type: ignore
        )
        years.append(reader)  # type: ignore
        del reader
    plays = pd.concat(years)  # type: ignore
    del years
    matrix = generate_transition_matrix(plays)
    with open("transition_matrix.csv", "w") as f:
        w = csv.writer(f)
        w.writerows(matrix)


if __name__ == "__main__":
    main(start_data_year, end_data_year)
