import argparse
import csv
import json
import random
import sys

from tqdm import tqdm


def generate_transition_matrix(stats: dict) -> list[list[float]]:
    """
    Using Monte Carlo simulation to estimate the transition matrix
    """
    transition_matrix = [[0 for _ in range(124)] for _ in range(24)]
    for state in tqdm(range(24), desc="States", position=0, leave=True):
        outs = state // 8
        base_state = state % 8
        for _ in tqdm(range(1_000_000), desc="Simulations", position=1, leave=False):
            # for _ in range(1):
            new_state = base_state
            new_outs = outs
            runs_scored = 0
            sb2_opportunity = new_state & 0b001 and not new_state & 0b010
            sb3_opportunity = new_state & 0b010 and not new_state & 0b100
            assert not (sb2_opportunity and sb3_opportunity)
            # If the runner on first tries to steal second
            if sb2_opportunity and random.random() < (stats["sb"]["SB2"] + stats["sb"]["CS2"]) / stats["sb"]["SB2O"]:
                if random.random() < stats["sb"]["CS2"] / (stats["sb"]["SB2"] + stats["sb"]["CS2"]):
                    # remove the runner on first
                    new_state &= 0b110
                    new_outs += 1
                else:
                    new_state |= 0b010
                    new_state &= 0b110
            # If the runner on second tries to steal third
            elif sb3_opportunity and random.random() < (stats["sb"]["SB3"] + stats["sb"]["CS3"]) / stats["sb"]["SB3O"]:
                if random.random() < stats["sb"]["CS3"] / (stats["sb"]["SB3"] + stats["sb"]["CS3"]):
                    # remove the runner on second
                    new_state &= 0b101
                    new_outs += 1
                else:
                    new_state |= 0b100
                    new_state &= 0b101
            else:
                event = random.choices(list(stats["stats"].keys()), weights=stats["stats"].values(), k=1)[0]
                if event in ("HBP", "BB"):
                    match base_state:
                        case 0b000:
                            new_state = 0b001
                        case 0b001:
                            new_state = 0b011
                        case 0b010:
                            new_state = 0b011
                        case 0b011:
                            new_state = 0b111
                        case 0b100:
                            new_state = 0b101
                        case 0b101:
                            new_state = 0b111
                        case 0b110:
                            new_state = 0b111
                        case 0b111:
                            new_state = 0b1111
                    if new_state & 0b1000:
                        runs_scored += 1
                        new_state &= 0b111
                elif event == "K":
                    new_outs += 1
                elif event == "Outs":
                    new_outs += 1
                    type_out_choice = random.choices(
                        ["G", "F", "L"],
                        weights=[
                            stats["groundout_rate"],
                            stats["flyout_rate"],
                            stats["lineout_rate"],
                        ],
                        k=1,
                    )[0]

                    # Flyout or lineout
                    if type_out_choice in "FL" and new_outs < 3:
                        # Scenarios with no runners forcing others
                        if base_state in [0b101, 0b100, 0b010, 0b001]:
                            if (
                                base_state & 0b001
                                and random.random() < stats["xbt_attempt_rate"][f"{type_out_choice}Out"]["1B"][outs]
                            ):
                                if random.random() < stats["xbt_success_rate"][f"{type_out_choice}Out"]["1B"][outs]:
                                    new_state |= 0b010
                                    new_state &= 0b110
                                else:
                                    new_outs += 1
                                    new_state &= 0b110
                            if (
                                base_state & 0b010
                                and random.random() < stats["xbt_attempt_rate"][f"{type_out_choice}Out"]["2B"][outs]
                            ):
                                if random.random() < stats["xbt_success_rate"][f"{type_out_choice}Out"]["2B"][outs]:
                                    new_state |= 0b100
                                    new_state &= 0b101
                                else:
                                    new_outs += 1
                                    new_state &= 0b101
                            if (
                                base_state & 0b100
                                and random.random() < stats["xbt_attempt_rate"][f"{type_out_choice}Out"]["3B"][outs]
                            ):
                                if random.random() < stats["xbt_success_rate"][f"{type_out_choice}Out"]["3B"][outs]:
                                    runs_scored += 1
                                    new_state &= 0b011
                                else:
                                    new_outs += 1
                                    new_state &= 0b011
                        # Scenarios with runners forcing others. NOTE: this makes the incorrect assumption that runner advances are independent of each other
                        elif base_state == 0b011:
                            # If the runner from first advances and forces the runner from second to third
                            if random.random() < stats["xbt_attempt_rate"][f"{type_out_choice}Out"]["1B"][outs]:
                                if random.random() < stats["xbt_success_rate"][f"{type_out_choice}Out"]["2B"][outs]:
                                    new_state |= 0b100
                                    new_state &= 0b101
                                else:
                                    new_outs += 1
                                    new_state &= 0b101
                                if random.random() < stats["xbt_success_rate"][f"{type_out_choice}Out"]["1B"][outs]:
                                    new_state |= 0b010
                                    new_state &= 0b110
                                else:
                                    new_outs += 1
                                    new_state &= 0b110
                            elif random.random() < stats["xbt_attempt_rate"][f"{type_out_choice}Out"]["2B"][outs]:
                                if random.random() < stats["xbt_success_rate"][f"{type_out_choice}Out"]["2B"][outs]:
                                    new_state |= 0b100
                                    new_state &= 0b101
                                else:
                                    new_outs += 1
                                    new_state &= 0b101
                        elif base_state == 0b110:
                            # If the runner from second forces the runner at third
                            if random.random() < stats["xbt_attempt_rate"][f"{type_out_choice}Out"]["2B"][outs]:
                                if random.random() < stats["xbt_success_rate"][f"{type_out_choice}Out"]["3B"][outs]:
                                    runs_scored += 1
                                    new_state &= 0b011
                                else:
                                    new_outs += 1
                                    new_state &= 0b011
                                if random.random() < stats["xbt_success_rate"][f"{type_out_choice}Out"]["2B"][outs]:
                                    new_state |= 0b100
                                    new_state &= 0b101
                                else:
                                    new_outs += 1
                                    new_state &= 0b101
                            elif random.random() < stats["xbt_attempt_rate"][f"{type_out_choice}Out"]["3B"][outs]:
                                if random.random() < stats["xbt_success_rate"][f"{type_out_choice}Out"]["3B"][outs]:
                                    runs_scored += 1
                                    new_state &= 0b011
                                else:
                                    new_outs += 1
                                    new_state &= 0b011
                        elif base_state == 0b111:
                            # If the runner from first forces everyone
                            if random.random() < stats["xbt_attempt_rate"][f"{type_out_choice}Out"]["1B"][outs]:
                                if random.random() < stats["xbt_success_rate"][f"{type_out_choice}Out"]["3B"][outs]:
                                    runs_scored += 1
                                    new_state &= 0b011
                                else:
                                    new_outs += 1
                                    new_state &= 0b011
                                if random.random() < stats["xbt_success_rate"][f"{type_out_choice}Out"]["2B"][outs]:
                                    new_state |= 0b100
                                    new_state &= 0b101
                                else:
                                    new_outs += 1
                                    new_state &= 0b101
                                if random.random() < stats["xbt_success_rate"][f"{type_out_choice}Out"]["1B"][outs]:
                                    new_state |= 0b010
                                    new_state &= 0b110
                                else:
                                    new_outs += 1
                                    new_state &= 0b110
                            # If the runner from second forces the runner at third
                            elif random.random() < stats["xbt_attempt_rate"][f"{type_out_choice}Out"]["2B"][outs]:
                                if random.random() < stats["xbt_success_rate"][f"{type_out_choice}Out"]["3B"][outs]:
                                    runs_scored += 1
                                    new_state &= 0b011
                                else:
                                    new_outs += 1
                                    new_state &= 0b011
                                if random.random() < stats["xbt_success_rate"][f"{type_out_choice}Out"]["2B"][outs]:
                                    new_state |= 0b100
                                    new_state &= 0b101
                                else:
                                    new_outs += 1
                                    new_state &= 0b101
                            elif random.random() < stats["xbt_attempt_rate"][f"{type_out_choice}Out"]["3B"][outs]:
                                if random.random() < stats["xbt_success_rate"][f"{type_out_choice}Out"]["3B"][outs]:
                                    runs_scored += 1
                                    new_state &= 0b011
                                else:
                                    new_outs += 1
                                    new_state &= 0b011
                    elif type_out_choice == "G":
                        # Advance forced runners
                        match base_state:
                            case 0b000:
                                new_state = 0b000
                            case 0b001:
                                new_state = 0b010
                            case 0b010:
                                new_state = 0b010
                                if outs < 2 and random.random() < stats["xbt_attempt_rate"]["GOut"]["2B"][outs]:
                                    if random.random() < stats["xbt_success_rate"]["GOut"]["2B"][outs]:
                                        new_state = 0b100
                                    else:
                                        new_outs += 1
                                        new_state = 0b000
                            case 0b011:
                                new_state = 0b110
                            case 0b100:
                                new_state = 0b100
                                if outs < 2 and random.random() < stats["xbt_attempt_rate"]["GOut"]["3B"][outs]:
                                    if random.random() < stats["xbt_success_rate"]["GOut"]["3B"][outs]:
                                        new_state = 0b000
                                        if new_outs < 3:
                                            runs_scored += 1
                                    else:
                                        new_outs += 1
                                        new_state = 0b000
                            case 0b101:
                                new_state = 0b110
                                if outs < 2 and random.random() < stats["xbt_attempt_rate"]["GOut"]["3B"][outs]:
                                    if random.random() < stats["xbt_success_rate"]["GOut"]["3B"][outs]:
                                        new_state = 0b010
                                        if new_outs < 3:
                                            runs_scored += 1
                                    else:
                                        new_outs += 1
                                        new_state = 0b010
                            case 0b110:
                                new_state = 0b110
                                if outs < 2 and random.random() < stats["xbt_attempt_rate"]["GOut"]["2B"][outs]:
                                    if random.random() < stats["xbt_success_rate"]["GOut"]["3B"][outs]:
                                        new_state = 0b010
                                        if new_outs < 3:
                                            runs_scored += 1
                                    else:
                                        new_outs += 1
                                        new_state = 0b010
                                    if random.random() < stats["xbt_success_rate"]["GOut"]["2B"][outs]:
                                        new_state = 0b100
                                    else:
                                        new_outs += 1
                                        new_state = 0b000
                                elif outs < 2 and random.random() < stats["xbt_attempt_rate"]["GOut"]["3B"][outs]:
                                    if random.random() < stats["xbt_success_rate"]["GOut"]["3B"][outs]:
                                        new_state = 0b010
                                        if new_outs < 3:
                                            runs_scored += 1
                                    else:
                                        new_outs += 1
                                        new_state = 0b010
                            case 0b111:
                                new_state = 0b1111

                        if base_state == 0b001 or base_state == 0b101:
                            if random.random() < stats["gidp_rate"]:
                                new_outs += 1
                                new_state &= 0b100
                                # new_state <<= 1
                                if new_state & 0b1000 and new_outs < 3:
                                    runs_scored += 1
                                new_state &= 0b111
                            else:
                                if random.random() > stats["gidp_failure_outs"]["B"]:
                                    new_state &= 0b101
                                    new_state |= 0b001
                        elif base_state == 0b011:
                            if random.random() < stats["gidp_rate"]:
                                new_outs += 1
                                new_state &= 0b100
                            else:
                                base = random.choices(
                                    ["B", "1B", "2B"],
                                    weights=[
                                        stats["gidp_failure_outs_2b"]["B"],
                                        stats["gidp_failure_outs_2b"]["1B"],
                                        stats["gidp_failure_outs_2b"]["2B"],
                                    ],
                                    k=1,
                                )[0]
                                if base == "B":
                                    new_state &= 0b110
                                elif base == "1B":
                                    new_state &= 0b101
                                elif base == "2B":
                                    new_state &= 0b011
                        elif base_state == 0b111:
                            if random.random() < stats["gidp_rate"]:
                                new_outs += 1
                                new_state = 0b100
                                if new_outs < 3:
                                    runs_scored += 1
                            else:
                                base = random.choices(
                                    ["B", "1B", "2B", "3B"],
                                    weights=[
                                        stats["gidp_failure_outs_loaded"]["B"],
                                        stats["gidp_failure_outs_loaded"]["1B"],
                                        stats["gidp_failure_outs_loaded"]["2B"],
                                        stats["gidp_failure_outs_loaded"]["3B"],
                                    ],
                                    k=1,
                                )[0]
                                if base == "B":
                                    new_state &= 0b110
                                    if new_outs < 3:
                                        runs_scored += 1
                                elif base == "1B":
                                    new_state &= 0b101
                                    if new_outs < 3:
                                        runs_scored += 1
                                elif base == "2B":
                                    new_state &= 0b011
                                    if new_outs < 3:
                                        runs_scored += 1
                                elif base == "3B":
                                    new_state &= 0b111
                        elif base_state == 0b110 or base_state == 0b100 or base_state == 0b010 or base_state == 0b000:
                            if new_state & 0b1000 and new_outs < 3:
                                runs_scored += 1
                            new_state &= 0b111
                        if new_outs >= 3:
                            runs_scored = 0

                elif event == "HR":
                    runs_scored += 1 + bin(base_state).count("1")
                    new_state = 0
                elif event == "3B":
                    runs_scored += bin(base_state).count("1")
                    new_state = 0b100
                elif event == "2B":
                    new_state <<= 2
                    runs_scored += bin(new_state >> 3).count("1")
                    new_state &= 0b111
                    new_state |= 0b010
                    if new_state == 0b110:
                        if random.random() < stats["xbt_attempt_rate"]["2B"]["1B"][outs]:
                            if random.random() < stats["xbt_success_rate"]["2B"]["1B"][outs]:
                                new_state &= 0b011
                                runs_scored += 1
                            else:
                                new_outs += 1
                                new_state &= 0b011
                elif event == "1B":
                    new_state <<= 1
                    runs_scored += bin(new_state >> 3).count("1")
                    new_state &= 0b111
                    new_state |= 0b001
                    if new_state == 0b111:
                        if random.random() < stats["xbt_attempt_rate"]["1B"]["1B"][outs]:
                            if random.random() < stats["xbt_success_rate"]["1B"]["2B"][outs]:
                                new_state &= 0b011
                                runs_scored += 1
                            else:
                                new_outs += 1
                                new_state &= 0b011
                            if random.random() < stats["xbt_success_rate"]["1B"]["1B"][outs]:
                                new_state &= 0b101
                                new_state |= 0b100
                            else:
                                new_outs += 1
                                new_state &= 0b101
                        elif random.random() < stats["xbt_attempt_rate"]["1B"]["2B"][outs]:
                            if random.random() < stats["xbt_success_rate"]["1B"]["2B"][outs]:
                                new_state &= 0b011
                                runs_scored += 1
                            else:
                                new_outs += 1
                                new_state &= 0b011
                    elif new_state == 0b011:
                        if random.random() < stats["xbt_attempt_rate"]["1B"]["1B"][outs]:
                            if random.random() < stats["xbt_success_rate"]["1B"]["1B"][outs]:
                                new_state &= 0b101
                                new_state |= 0b100
                            else:
                                new_outs += 1
                                new_state &= 0b101
                    elif new_state == 0b101:
                        if random.random() < stats["xbt_attempt_rate"]["1B"]["2B"][outs]:
                            if random.random() < stats["xbt_success_rate"]["1B"]["2B"][outs]:
                                new_state &= 0b011
                                runs_scored += 1
                            else:
                                new_outs += 1
                                new_state &= 0b011
                else:
                    raise ValueError(f"Unknown event {event}")
            if new_outs >= 3:
                new_outs = 3
                new_state = 0
            new_full_state = (new_outs * 8 + new_state) * 5 + runs_scored
            transition_matrix[state][new_full_state] += 1
            # print(
            #     f"Event: {event}, Old state: {state}, old runners {bin(base_state)}, New runners: {bin(new_state)}, old outs: {outs}, New outs: {new_outs}, Runs scored: {runs_scored}, New full state: {new_full_state}"
            # )
    for state in range(24):
        s = sum(transition_matrix[state])
        for new_state in range(124):
            transition_matrix[state][new_state] /= s
        assert 0.999999 < sum(transition_matrix[state]) < 1.000001
    return transition_matrix


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stat-file", "-f", help="Stats file", type=str, default="stats.json")
    parser.add_argument("--out-file", "-o", help="Output file", type=str, default="transition_matrix_custom.csv")
    args = parser.parse_args(sys.argv[1:])
    with open(args.stat_file) as f:
        stats = json.load(f)

    transition_matrix = generate_transition_matrix(stats)
    with open(args.out_file, "w") as f:
        w = csv.writer(f)
        w.writerows(transition_matrix)


if __name__ == "__main__":
    main()
