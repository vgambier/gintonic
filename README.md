# gintonic

gintonic is a lightweight emulation front-end that works in a terminal. It is designed to be fast, to be comfortable for keyboard users, and to work through ssh. This allows you to have a unified text-based interface for browsing and launching all of your games using any emulator. You can use any emulator you want as long as you specify the command in the configuration file yourself.

## Features

* Support of vim-style keys
* Search history
* Script based confguration

## Requirements

* Python 3. Tested with Python 3.10.12
* Only tested on Linux

## Installation

* Clone this repository
* Place a config file named `config.json` into `~/.config/gintonic`. You can copy the example found in `config_template/` for this purpose. That file has working commands for many popular emulators - feel free to tweak the commands, flags, and system/folder names.

## Configuration

Example:
```
{
  "paths_to_games": [
    "/home/user/foobar/games1",
    "/home/user/foobar/games2"
  ],
  "systems": {
    "Sony - Amiga DS": "aMIG0S {0} --fullscreen",
    "Arcade": "mame {0}",
    "Sega - Dreamcast": "./flycast.sh {0}"
  }
}
```

`paths_to_games` - each path in this list is a path to a directory with games that should have the following structure:
```
├── System1
│   ├── Game1
│   ├── Game2
│   └── Game3
└── System2
    └── Game1
```
Where: 
  SystemX - is the name of a system/folder (DOS, NES, etc).<br>
  GameX - is the name of a game. Can be file or a folder, depending on the system.<br>

`systems` - allows you to specify a command to run a game on a particular system. `{0}` (or `{}`) is substituted by the absolute path of the game you are launching.

`Arcade` is a special case. The entry also specifies which command will be used to launch arcade games with MAME, but you do not need a game folder called `Arcade`. gintonic uses MAME's internal database to list available games - this assumes you don't have missing MAME roms. Note: this only works with MAME.

## Running gintonic

* `./gintonic.py`
<br>
To exit, press `q`.

## Desktop entry
.desktop and .svg files are provided. To add gintonic as a desktop entry, edit gintonic.desktop to reflect the directory in which gintonic.py is located
then run the following commands:
* `cp gintonic.desktop ~/.local/share/applications/`
* `cp gintonic.svg ~/.icons/`

This uses gnome-terminal as the terminal emulator. If you want to use a different terminal emulator, you have two options:
* edit the Exec line to explicitly state your terminal emulator of choice (e.g.: `kgx ./gintonic.py`)
* edit the Exec line to remove gnome-console (`Exec=./gintonic.py`) and add the following line: `Terminal=true`)
