# Baseball Markov Chains

Basically just simulates baseball games (and from them, generates win expectancy) using Markov chains.

A note: if I mention you can change something with command line arguments, just run `python3 script.py --help` (replacing `script.py` with the real name)

First, run `download.py` and `retrosheet_to_csv.sh` (~3.5 GB of data in total). Then, update the start and end year in `config.py` depending on how many years of data you want to use (ONLY FOR `gen_stats_and_bsr.py` AND `generate_transition_matrix.py`).

To generate win expectancy based on real stats, do this:

1. `generate_transition_matrix.py`
2. `simulate_game.py`
   That simple. It'll output the transition matrix into `transition_matrix.csv` and the win expectancies into `win_expectancy.csv`. For `simulate_game.py`, there's keyword arguments on the command line to change the name of the output file, the transition matrix input file, and the number of simulations per game start scenario (based on inning, top/bottom, and run differential) which changes how fast it will go at the expense of accuracy at lower values.

To generate a fictional transition matrix, first run `gen_stats_and_bsr.py`. That will create a file `stats.json` (you can change it with command line arguments) with a really granual control of stats that you can modify. Feel free to modify them all however you want and just run `gen_stats_and_bsr.py` again to get the real stats back. It includes the average stats between `start_year` and `end_year` from `config.py`. Then, run `generate_transition_matrix_from_stats.py` (and you can change the names of the input and output file with command line arguments, by default it's `transition_matrix_custom.csv`). Finally, run `simulate_game.py` making sure to change the name of the matrix file to whatever you named your custom one.

TODO: support lineups with multiple matrices.

Here's a quick rundown of `stats.json`:

```
"stats": {
    "1B": 0.14190374871131195,
    "2B": 0.04354120511526904,
    "3B": 0.0035260698852793435,
    "HR": 0.028597907389940554,
    "BB": 0.0814505692162583,
    "HBP": 0.011219811796705345,
    "K": 0.22380398780407554,
    "Outs": 0.4659567000811599
},
```

This stats JSON contains the probability of any given event happening. So, for a .000/1.000/.000 hitter, BB would be 1 and everything else would be 0. Everything should add up to 1. If it does not, my code will be mad.

```
"sb": {
    "SB2O": 38720,
    "SB2": 1994,
    "CS2": 492,
    "SB3O": 27145,
    "SB3": 272,
    "CS3": 60
},
```

Stolen bases! "SB2O" is the opportunities to steal second (runner on first, no runner on second). "SB2" is successful steals of second. "CS2" is unsuccessful steals of second. "SB3O" is runner on second, no runner on third. You get the point.

The next 2 fields (`xbt_attempt_rate` and `xbt_success_rate`) all relate to extra bases taken. For example, going first to third on a single. Here's the structure for a small part of it.

```
"xbt_attempt_rate": {
    "1B": {
        "1B": [
            0.2545796148426491,
            0.2685396929108135,
            0.3809827696234844
        ],
        "2B": [
            0.41938405797101447,
            0.5475218658892128,
            0.8219735503560529
        ]
    },
    "2B": {
        "1B": [
            0.3270735524256651,
            0.35477178423236516,
            0.6089266737513284
        ]
    },
    ...
}
```

Basically, the outer keys (1B and 2B) are each of the possible outcomes. So `xbt_attempt_rate["1B"]` will return the array for the attempt rate on a single. 2B is a double. Then, inside those inner dictionaries, you get where the runner was. `xbt_attempt_rate["1B"]["2B"]` returns the attempt rate for a single with a runner on 2B (runner going from 2nd to home). Then, inside that, is the number of outs AT THE TIME OF THE PLAY. This is crucial for a few other fields. So if, at the time of the single, there's 1 out, you would index into `xbt_attempt_rate["1B"]["2B"][1]` to get your attempt rate of 0.2685396929108135 (or 26.8% of the time a runner from 2nd base with 1 out will attempt to score on a single)

The other events are FOut, GOut, and LOut. Flyouts, groundouts, and lineouts respectively. For these, it accounts for runners on first, second and third but only for 0 and 1 outs. If there's 2 outs at the time of the play, you can't have an advance on an out.

The success rate is basically just "when the runner attempts to take an extra base, how often are they safe".

The next is `gidp_rate`. This is the least self explanatory. It's basically `gidp/groundballs with at least 1 out`. So the denominator is added to if there's a groundout with one or more outs. This isn't the rate of `gidp/PA` as the name might suggest.

`groundout_rate`, `flyout_rate`, and `lineout_rate` are just how often groundouts, flyouts, and lineouts are. These add up to 1.

```
"gidp_failure_outs": {
    "B": 0.40893203883495144,
    "1B": 0.5910679611650486
},
```

`gidp_failure-outs` is a dictionary of this situation: runner on first, groundball, only one out is achieved, what is the probability of the out being the batter (`B`) or the runner on first (`1B`). These add up to 1.

`gidp_failure_outs_2b` is the exact same thing but if there's runners on first and second so it includes a runner on second. `gidp_failure_outs_loaded` is the same thing but the bases loaded.
