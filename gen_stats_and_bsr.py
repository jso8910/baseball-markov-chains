import argparse
import json
import os
import sys
from copy import deepcopy

import pandas as pd
from tqdm import tqdm

from config import end_data_year, start_data_year


def generate_stats(plays: pd.DataFrame):
    stats = {
        "PA": 0,
        "1B": 0,
        "2B": 0,
        "3B": 0,
        "HR": 0,
        "BB": 0,
        "HBP": 0,
        "K": 0,
    }

    # Can use this to see the percent of stolen bases that are of 2nd or third
    sb = {
        "SB2O": 0,  # Steal second opportunities (runner on first, no runner on second)
        "SB2": 0,
        "CS2": 0,
        "SB3O": 0,  # Steal third opportunities (runner on second, no runner on third)
        "SB3": 0,
        "CS3": 0,
    }

    # Basically, the outer keys are the type of hit, the next are where the runner starts, and the inner are the number of outs
    # An XBT is when a runner goes more bases than the batter. So, for example, a single with a runner on first and the runner gets to third is an XBT
    xbt = {
        "1B": {
            "1B": [0, 0, 0],
            "2B": [0, 0, 0],
        },
        "2B": {
            "1B": [0, 0, 0],
        },
        "FOut": {
            "1B": [0, 0],
            "2B": [0, 0],
            "3B": [0, 0],
        },
        "GOut": {  # Excludes force plays
            # "1B": [0, 0],
            "2B": [0, 0],
            "3B": [0, 0],
        },
        "LOut": {
            "1B": [0, 0],
            "2B": [0, 0],
            "3B": [0, 0],
        },
    }

    xbt_chances = deepcopy(xbt)

    xbt_thrown_out = deepcopy(xbt)
    # If there's a runner on first (or more) and less than two outs
    gidp_opportunities = 0
    gidp_opportunities_no_out = 0
    gidp_count = 0
    gidp_failure_outs_no_2b = {
        "B": 0,
        "1B": 0,
    }
    gidp_failure_outs_2b = {
        "B": 0,
        "1B": 0,
        "2B": 0,
    }
    gidp_failure_runner_2b_freq = 0
    gidp_failure_outs_loaded = {
        "B": 0,
        "1B": 0,
        "2B": 0,
        "3B": 0,
    }
    gidp_failure_runner_loaded_freq = 0
    gidp_failure_1b = 0

    groundout_frequency = 0
    flyout_frequency = 0
    lineout_frequency = 0

    event_code_to_event = {
        2: "Out",
        3: "K",
        4: "SB",
        6: "CS",
        14: "BB",
        15: "BB",  # IBB, basically a walk
        16: "HBP",
        18: "PA",  # Error, just count it as a PA
        20: "1B",
        21: "2B",
        22: "3B",
        23: "HR",
    }

    for _, play in tqdm(plays.iterrows(), total=plays.shape[0]):
        if play["EVENT_CD"] not in event_code_to_event:
            continue
        runner_state_before = int(play["START_BASES_CD"])
        event = event_code_to_event[int(play["EVENT_CD"])]
        if event == "Out":
            stats["PA"] += 1
            if play["BATTEDBALL_CD"] == "G":
                groundout_frequency += 1
            elif play["BATTEDBALL_CD"] == "F":
                flyout_frequency += 1
            elif play["BATTEDBALL_CD"] == "L":
                lineout_frequency += 1

            if int(play["OUTS_CT"]) == 2:
                pass
            elif play["BATTEDBALL_CD"] == "F":
                if runner_state_before & 0b001:
                    xbt_chances["FOut"]["1B"][int(play["OUTS_CT"])] += 1
                    if int(play["RUN1_DEST_ID"]) >= 2:
                        xbt["FOut"]["1B"][int(play["OUTS_CT"])] += 1
                    if int(play["RUN1_DEST_ID"]) == 0:
                        xbt_thrown_out["FOut"]["1B"][int(play["OUTS_CT"])] += 1
                if runner_state_before & 0b010:
                    xbt_chances["FOut"]["2B"][int(play["OUTS_CT"])] += 1
                    if int(play["RUN2_DEST_ID"]) >= 3:
                        xbt["FOut"]["2B"][int(play["OUTS_CT"])] += 1
                    if int(play["RUN2_DEST_ID"]) == 0:
                        xbt_thrown_out["FOut"]["2B"][int(play["OUTS_CT"])] += 1
                if runner_state_before & 0b100:
                    xbt_chances["FOut"]["3B"][int(play["OUTS_CT"])] += 1
                    if int(play["RUN3_DEST_ID"]) >= 4:
                        xbt["FOut"]["3B"][int(play["OUTS_CT"])] += 1
                    if int(play["RUN3_DEST_ID"]) == 0:
                        xbt_thrown_out["FOut"]["3B"][int(play["OUTS_CT"])] += 1
            elif play["BATTEDBALL_CD"] == "G":
                # if runner_state_before & 0b001:
                #     xbt_chances["GOut"]["1B"][int(play["OUTS_CT"])] += 1
                #     if int(play["RUN1_DEST_ID"]) >= 2:
                #         xbt["GOut"]["1B"][int(play["OUTS_CT"])] += 1
                #     if int(play["RUN1_DEST_ID"]) == 0:
                #         xbt_thrown_out["GOut"]["1B"][int(play["OUTS_CT"])] += 1

                # Exclude force plays
                if runner_state_before & 0b010 and not runner_state_before & 0b001:
                    xbt_chances["GOut"]["2B"][int(play["OUTS_CT"])] += 1
                    if int(play["RUN2_DEST_ID"]) >= 3:
                        xbt["GOut"]["2B"][int(play["OUTS_CT"])] += 1
                    if int(play["RUN2_DEST_ID"]) == 0:
                        xbt_thrown_out["GOut"]["2B"][int(play["OUTS_CT"])] += 1
                if runner_state_before & 0b100 and (not runner_state_before & 0b010 or not runner_state_before & 0b001):
                    xbt_chances["GOut"]["3B"][int(play["OUTS_CT"])] += 1
                    if int(play["RUN3_DEST_ID"]) >= 4:
                        xbt["GOut"]["3B"][int(play["OUTS_CT"])] += 1
                    if int(play["RUN3_DEST_ID"]) == 0:
                        xbt_thrown_out["GOut"]["3B"][int(play["OUTS_CT"])] += 1
            elif play["BATTEDBALL_CD"] == "L":
                if runner_state_before & 0b001:
                    xbt_chances["LOut"]["1B"][int(play["OUTS_CT"])] += 1
                    if int(play["RUN1_DEST_ID"]) >= 2:
                        xbt["LOut"]["1B"][int(play["OUTS_CT"])] += 1
                    if int(play["RUN1_DEST_ID"]) == 0:
                        xbt_thrown_out["LOut"]["1B"][int(play["OUTS_CT"])] += 1
                elif runner_state_before & 0b010:
                    xbt_chances["LOut"]["2B"][int(play["OUTS_CT"])] += 1
                    if int(play["RUN2_DEST_ID"]) >= 3:
                        xbt["LOut"]["2B"][int(play["OUTS_CT"])] += 1
                    if int(play["RUN2_DEST_ID"]) == 0:
                        xbt_thrown_out["LOut"]["2B"][int(play["OUTS_CT"])] += 1
                elif runner_state_before & 0b100:
                    xbt_chances["LOut"]["3B"][int(play["OUTS_CT"])] += 1
                    if int(play["RUN3_DEST_ID"]) >= 4:
                        xbt["LOut"]["3B"][int(play["OUTS_CT"])] += 1
                    if int(play["RUN3_DEST_ID"]) == 0:
                        xbt_thrown_out["LOut"]["3B"][int(play["OUTS_CT"])] += 1
        elif event == "SB":
            if play["RUN1_SB_FL"] == "T":
                sb["SB2"] += 1
            if play["RUN2_SB_FL"] == "T":
                sb["SB3"] += 1
        elif event == "CS":
            if play["RUN1_CS_FL"] == "T":
                sb["CS2"] += 1
            if play["RUN2_CS_FL"] == "T":
                sb["CS3"] += 1
        else:
            stats[event] += 1
            stats["PA"] += 1

        if event in ["1B", "2B", "3B", "HR", "BB", "HBP", "K", "Out", "PA"]:
            # 1B is occupied but not 2B
            if runner_state_before & 0b001 and not runner_state_before & 0b010:
                sb["SB2O"] += 1

            # 2B is occupied but not 3B
            if runner_state_before & 0b010 and not runner_state_before & 0b100:
                sb["SB3O"] += 1

        # Single with a runner on first
        if event == "1B" and runner_state_before & 0b001:
            xbt_chances["1B"]["1B"][int(play["OUTS_CT"])] += 1
            if int(play["RUN1_DEST_ID"]) == 3:
                xbt["1B"]["1B"][int(play["OUTS_CT"])] += 1
            if int(play["RUN1_DEST_ID"]) == 0:
                xbt_thrown_out["1B"]["1B"][int(play["OUTS_CT"])] += 1

        # Single with a runner on second
        if event == "1B" and runner_state_before & 0b010:
            xbt_chances["1B"]["2B"][int(play["OUTS_CT"])] += 1
            if int(play["RUN2_DEST_ID"]) >= 4:
                xbt["1B"]["2B"][int(play["OUTS_CT"])] += 1
            if int(play["RUN2_DEST_ID"]) == 0:
                xbt_thrown_out["1B"]["2B"][int(play["OUTS_CT"])] += 1

        # Double with a runner on first
        if event == "2B" and runner_state_before & 0b001:
            xbt_chances["2B"]["1B"][int(play["OUTS_CT"])] += 1
            if int(play["RUN1_DEST_ID"]) >= 4:
                xbt["2B"]["1B"][int(play["OUTS_CT"])] += 1
            if int(play["RUN1_DEST_ID"]) == 0:
                xbt_thrown_out["2B"]["1B"][int(play["OUTS_CT"])] += 1

        # GIDP
        if play["BATTEDBALL_CD"] == "G" and play["DP_FL"] == "T":
            gidp_count += 1

        # If there's a runner on first, you can GIDP!
        if play["BATTEDBALL_CD"] == "G" and int(play["OUTS_CT"]) < 2 and runner_state_before & 0b001:
            if int(play["EVENT_OUTS_CT"]) >= 1:
                gidp_opportunities += 1
            if int(play["EVENT_OUTS_CT"]) == 1:
                if runner_state_before == 0b011:
                    gidp_failure_runner_2b_freq += 1
                    if int(play["BAT_DEST_ID"]) == 0:
                        gidp_failure_outs_2b["B"] += 1
                    elif int(play["RUN1_DEST_ID"]) == 0:
                        gidp_failure_outs_2b["1B"] += 1
                    elif int(play["RUN2_DEST_ID"]) == 0:
                        gidp_failure_outs_2b["2B"] += 1
                elif runner_state_before == 0b001:
                    gidp_failure_1b += 1
                    if int(play["BAT_DEST_ID"]) == 0:
                        gidp_failure_outs_no_2b["B"] += 1
                    elif int(play["RUN1_DEST_ID"]) == 0:
                        gidp_failure_outs_no_2b["1B"] += 1
                elif runner_state_before == 0b111:
                    gidp_failure_runner_loaded_freq += 1
                    if int(play["BAT_DEST_ID"]) == 0:
                        gidp_failure_outs_loaded["B"] += 1
                    elif int(play["RUN1_DEST_ID"]) == 0:
                        gidp_failure_outs_loaded["1B"] += 1
                    elif int(play["RUN2_DEST_ID"]) == 0:
                        gidp_failure_outs_loaded["2B"] += 1
                    elif int(play["RUN3_DEST_ID"]) == 0:
                        gidp_failure_outs_loaded["3B"] += 1

    xbt_attempt_rate = deepcopy(xbt)
    xbt_succcess_rate = deepcopy(xbt)
    for key in xbt:
        for key2 in xbt[key]:
            for idx, value in enumerate(xbt[key][key2]):
                xbt_attempt_rate[key][key2][idx] = (xbt[key][key2][idx] + xbt_thrown_out[key][key2][idx]) / xbt_chances[
                    key
                ][key2][idx]
                xbt_succcess_rate[key][key2][idx] = xbt[key][key2][idx] / (
                    xbt_thrown_out[key][key2][idx] + xbt[key][key2][idx]
                )

    stats["Outs"] = (
        stats["PA"] - stats["1B"] - stats["2B"] - stats["3B"] - stats["HR"] - stats["BB"] - stats["HBP"] - stats["K"]
    )
    weighted_stats = {}
    for key, value in stats.items():
        if key != "PA":
            weighted_stats[key] = value / stats["PA"]
    gidp_failure_outs_no_2b = {
        "B": gidp_failure_outs_no_2b["B"] / gidp_failure_1b,
        "1B": gidp_failure_outs_no_2b["1B"] / gidp_failure_1b,
    }
    gidp_failure_outs_2b = {
        "B": gidp_failure_outs_2b["B"] / gidp_failure_runner_2b_freq,
        "1B": gidp_failure_outs_2b["1B"] / gidp_failure_runner_2b_freq,
        "2B": gidp_failure_outs_2b["2B"] / gidp_failure_runner_2b_freq,
    }
    gidp_failure_outs_loaded = {
        "B": gidp_failure_outs_loaded["B"] / gidp_failure_runner_loaded_freq,
        "1B": gidp_failure_outs_loaded["1B"] / gidp_failure_runner_loaded_freq,
        "2B": gidp_failure_outs_loaded["2B"] / gidp_failure_runner_loaded_freq,
        "3B": gidp_failure_outs_loaded["3B"] / gidp_failure_runner_loaded_freq,
    }
    return (
        weighted_stats,
        sb,
        xbt_attempt_rate,
        xbt_succcess_rate,
        gidp_count / gidp_opportunities,
        groundout_frequency / (groundout_frequency + flyout_frequency + lineout_frequency),
        flyout_frequency / (groundout_frequency + flyout_frequency + lineout_frequency),
        lineout_frequency / (groundout_frequency + flyout_frequency + lineout_frequency),
        gidp_failure_outs_no_2b,
        gidp_failure_outs_2b,
        gidp_failure_outs_loaded,
    )


def main(start_year: int, end_year: int):
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-file", "-o", help="Output file", type=str, default="stats.json")
    args = parser.parse_args(sys.argv[1:])
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
    (
        stats,
        sb,
        xbt_attempt_rate,
        xbt_succcess_rate,
        gidp_rate,
        groundout_rate,
        flyout_rate,
        lineout_rate,
        gidp_failure_outs,
        gidp_failure_outs_2b,
        gidp_failure_outs_loaded,
    ) = generate_stats(plays)
    with open(args.out_file, "w") as f:
        json.dump(
            {
                "stats": stats,
                "sb": sb,
                "xbt_attempt_rate": xbt_attempt_rate,
                "xbt_success_rate": xbt_succcess_rate,
                "gidp_rate": gidp_rate,
                "groundout_rate": groundout_rate,
                "flyout_rate": flyout_rate,
                "lineout_rate": lineout_rate,
                "gidp_failure_outs": gidp_failure_outs,
                "gidp_failure_outs_2b": gidp_failure_outs_2b,
                "gidp_failure_outs_loaded": gidp_failure_outs_loaded,
            },
            f,
            indent=4,
        )


if __name__ == "__main__":
    main(start_data_year, end_data_year)
