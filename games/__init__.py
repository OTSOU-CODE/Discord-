from typing import Dict, Type, Any

GAMES_REGISTRY: Dict[str, Dict[str, Any]] = {
    "xo": {
        "name": "XO",
        "min_players": 2,
        "max_players": 2,
        "rules": "3x3 board. Align 3 to win.",
        "cog_path": "games.xo.commands"
    },
    "dice": {
        "name": "Dice Battle",
        "min_players": 2,
        "max_players": 100,
        "rules": "Highest roll wins! Unlimited players support.",
        "cog_path": "games.dice.commands"
    },
    "roulette": {
        "name": "Roulette",
        "min_players": 1,
        "max_players": 10,
        "rules": "Bet on numbers or colors and spin!",
        "cog_path": "games.roulette.commands"
    },
    "mafia": {
        "name": "Mafia",
        "min_players": 5,
        "max_players": 20,
        "rules": "Day/Night social deduction!",
        "cog_path": "games.mafia.commands"
    },
    "rps": {
        "name": "Rock Paper Scissors",
        "min_players": 2,
        "max_players": 2,
        "rules": "Classic Rock Paper Scissors.",
        "cog_path": "games.rps.commands"
    },
    "chairs": {
        "name": "Musical Chairs",
        "min_players": 3,
        "max_players": 10,
        "rules": "Be the first to sit when the music stops!",
        "cog_path": "games.chairs.commands"
    },
    "guesscountry": {
        "name": "Guess The Country",
        "min_players": 1,
        "max_players": 10,
        "rules": "Guess the country from clues!",
        "cog_path": "games.guesscountry.commands"
    },
    "deathwheel": {
        "name": "Death Wheel",
        "min_players": 2,
        "max_players": 10,
        "rules": "Pick safe boxes and survive!",
        "cog_path": "games.deathwheel.commands"
    },
    "hideseek": {
        "name": "Hide and Seek",
        "min_players": 3,
        "max_players": 10,
        "rules": "Seeker finds hiders!",
        "cog_path": "games.hideseek.commands"
    },
    "replica": {
        "name": "Replica",
        "min_players": 3,
        "max_players": 10,
        "rules": "Submit funny answers and vote!",
        "cog_path": "games.replica.commands"
    },
    "hotxo": {
        "name": "HotXO Tournament",
        "min_players": 2,
        "max_players": 20,
        "rules": "XO Tournament with move deletion!",
        "cog_path": "games.hotxo.commands"
    },
    "fastclick": {
        "name": "Fast Click",
        "min_players": 2,
        "max_players": 10,
        "rules": "Be the first to click!",
        "cog_path": "games.minigames.fastclick.commands"
    },
    "fasttype": {
        "name": "Fast Type",
        "min_players": 2,
        "max_players": 10,
        "rules": "Be the first to type the word! (10s timer)",
        "cog_path": "games.minigames.fasttype.commands"
    },
    "textsplit": {
        "name": "Text Split",
        "min_players": 2,
        "max_players": 10,
        "rules": "Reconstruct the split word!",
        "cog_path": "games.minigames.textsplit.commands"
    },
    "mergetext": {
        "name": "Merge Text",
        "min_players": 2,
        "max_players": 10,
        "rules": "Merge the text fragments!",
        "cog_path": "games.minigames.mergetext.commands"
    },
    "textreverse": {
        "name": "Text Reverse",
        "min_players": 2,
        "max_players": 10,
        "rules": "Reverse the word correctly!",
        "cog_path": "games.minigames.textreverse.commands"
    },
    "findletter": {
        "name": "Find Letter",
        "min_players": 2,
        "max_players": 10,
        "rules": "Find the target letter! (Hard, 10s)",
        "cog_path": "games.minigames.findletter.commands"
    },
    "correctletter": {
        "name": "Correct Letter",
        "min_players": 2,
        "max_players": 10,
        "rules": "Identify the different character!",
        "cog_path": "games.minigames.correctletter.commands"
    },
    "guesstheflag": {
        "name": "Guess The Flag",
        "min_players": 2,
        "max_players": 10,
        "rules": "Guess the country from the flag!",
        "cog_path": "games.minigames.guesstheflag.commands"
    },
    "guessthecolor": {
        "name": "Guess The Color",
        "min_players": 2,
        "max_players": 10,
        "rules": "Guess the color name! (Image-based, 10s)",
        "cog_path": "games.minigames.guessthecolor.commands"
    },
    "findemoji": {
        "name": "Find The Emoji",
        "min_players": 2,
        "max_players": 10,
        "rules": "Find the hidden emoji! (Hard, 10s)",
        "cog_path": "games.minigames.findemoji.commands"
    },
    "sortnumbers": {
        "name": "Sort Numbers",
        "min_players": 2,
        "max_players": 10,
        "rules": "Sort the numbers correctly! (Hard, 10s)",
        "cog_path": "games.minigames.sortnumbers.commands"
    },
    "textreveal": {
        "name": "Text Reveal",
        "min_players": 2,
        "max_players": 10,
        "rules": "Guess the word as it reveals!",
        "cog_path": "games.minigames.textreveal.commands"
    }
}
