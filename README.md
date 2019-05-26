# Schedule Optimiser for Games Conventions.

At a games convention where there are multiple players who want to play
multiple games, and a limited number of sessions and games available, we want
to be able to build a schedule that satisfies various constraints and makes the
most people happy possible.

This tool has been designed for use for
[http://www.18xxbelgium.com](http://www.18xxbelgium.com) so there are specifics
for this use-case, but this would be a good starting point for similar
problems.

## Features

* Optimise primarily for players getting to play the games they want to, but
  also optimise for better player counts based on BGG stats.

* Supports multiple sessions, and players and games only being present for a
  subset of the available sessions.

* Supports different session lengths (restricting to shorter games in shorter
  sessions); dynamically scale player count restrictions based on session
  length (i.e. if a game supports 3-6 players with a runtime of 3-6 hours, we
  assume that a 4h session will support a max of 4 players) - again from BGG
  stats.

* Supports an overall table limit per-session

* Makes the assumption that players will only want to play each game once
  across sessions.

### Not yet supported

* Any concept of overlapping sessions/games. We schedule sessions as a whole
  and assume that a game takes the whole session, rather than trying to figure
  out game length and then packing into the available time.

## Usage

This is dockerized. To build:

    docker build -t schedule .

Before running for the first time, you need to run a script to download data
from BGG:

    docker run -v $(pwd):/app -t schedule python game_data.py

This downloads all games from BGG in the 18xx family and stores them in
games.json. Each game looks like:

    {
      "id": 193867,
      "name": "1822",
      "full_name": "1822: The Railways of Great Britain",
      "min_players": 3,
      "max_players": 7,
      "min_playtime": 300,
      "max_playtime": 420,
      "popularity": {
        "3": 0.5555555555555556,
        "4": 1.0,
        "5": 1.0,
        "6": 0.8333333333333334,
        "7": 0.6
      },
      "owned": 252
    }

For the optimiser the important keys are min and max players, min and max
playtime, the name and the popularity. The number of games `owned` is used for
generating sample data.

It is assumed that there is only one game with each short name.

For games not available on BGG (prototypes or similar) you can just directly
edit this file to add them, or the code will just assume they have a player
count of 3-4 and a flat runtime of 4 hours.

There is some sample data included - to see the outputs for that just run:

    docker run -v $(pwd):/app -t schedule

To run on real data, you need to make a sessions.json and a players.json.

The sessions.json file looks like:

    [{"name": "whatever", length=240}, ...]

The length is the length of the session in minutes. You can have as many
sessions as you like.

The players.json file looks like:

    [
      {
        "name": "Bob",
        "owns": ["1830"],
        "interests": ["1830", "1817"],
        "sessions": [0, 1, 2]}]
      },
      ...
    ]

The `sessions` contains the indexes of the sessions this player is
attending. The games that they own will only be available in those
sessions. The `interests` express which games they want to play.

Given these 2 files, the scheduler can be run with:

    docker run -v $(pwd):/app -t schedule python schedule.py --players players.json --sessions sessions.json

This outputs the schedule to STDOUT. The sample data contains 40 players each
interested in 0-10ish games, and runs in a couple of seconds - runtime is
likely to be higher for many more players. Example output looks like:

    ==== Session Friday Eve ====
    ## 1830 ##
    Declan*
    Thibault
    Marcela
    Christian*

    ## 1846 ##
    Eustachio*
    Aimé
    Edvige

    ...

For further options such as shared games or changing the table limit, see:

    docker run -v $(pwd):/app -t schedule python schedule.py --help

In addition to the two scripts mentioned above, there is a script to generate
sample data:

    docker run -v $(pwd):/app -t schedule python generate_sample.py

The scheduling code can also obviously just be called directly as a library as
well:

    s = Schedule(games, players, sessions, shared_games, table_limit)
    result = s.solve()

## Implementation

This uses [PuLP](https://pythonhosted.org/PuLP/) to solve a [Mixed Integer
Program](https://en.wikipedia.org/wiki/Integer_programming) representing the
scheduling problem. This [Coursera
course](https://www.coursera.org/learn/discrete-optimization) is a great way to
learn about discrete optimization problems in general, and explains the Mixed
Integer Programming solution in detail in weeks 5-6.

We essentially create a set of binary variables
![X_i_p_g](https://latex.codecogs.com/svg.latex?X_i_p_g): for each session `i`,
for each player `p`, for each game `g` - is the player playing this game? We
create a series of logical constraints (i.e. for any given `i` and `p` the
result must sum to 1 - a player cannot play in more than one game at a time,
and we want to enforce that no one is left without a game). There are similar
constraints and variables to deal with the player count restrictions. Given
this we then sum all of these variables if (a) the player is playing and (b)
the player is interested in the game, and let the PuLP optimiser attempt to
maximise the result. For more detail, best to look at the code in schedule.py.

## Contribution & Development

This software is licensed under the MIT License (see MIT-LICENSE). Pull
requests are welcome. To run tests, run:

    docker run -v $(pwd):/app -t schedule pytest