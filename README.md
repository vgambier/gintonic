# gintonic

gintonic is a lightweight game launcher that works in a terminal. It is designed to be fast, to be comfortable for keyboard users and to work through ssh. You can use any emulator you want as long as you specify the command in the configuration file yourself.

## Features

  * Support of VIM-style keys
  * Search history
  * Script based confguration

## Requirements

* python

## Installation

* Download gintonic
* Place a config file named config into ~/.config/gintonic. You can use the example config_template folder for this purpose.

Example:
```
[CONFIG]
paths_to_games = /home/user/games;/home/user2/games
path_to_mame = /home/user/mame_roms
run_dos = ./dos.sh {0}
run_mame = 
```
paths_to_games - each semicolon-separated path is a path to a directory with games that should have the following structure:
```
System1
      |- Game1
      |- Game2
      |- Game3
System2
      |- Game1
```
Where: 
  SystemX - is the name of a system/folder (DOS, NES, etc).<br>
  GameX - is the name of a game.<br>
<br>
run_system - specifies a command to run a game on a particular system. {0} is substituted by an absolute path of a game.
In the config file, run_system should be lower-case even if the folder contained upper-case letters.
run_mame is a special case which will be used to launch arcade games with MAME, regardless of the name of the folder.

## Run

* ./gintonic.py
<br>
For exit - press q. 

## Desktop entry
.desktop and .svg files are provided. To add gintonic as a desktop entry, edit gintonic.desktop to reflect the directory in which gintonic.py is located
then run the following commands:
* `cp gintonic.desktop ~/.local/share/applications/`
* `cp gintonic.svg ~/.icons/`

This uses gnome-terminal as the terminal emulator. If you want to use a different terminal emulator, you have two options:
* edit the Exec line to explicitly state your terminal emulator of choice (e.g.: kgx ./gintonic.py)
* edit the Exec line to remove gnome-console (Exec=./gintonic.py) and add the following line: `Terminal=true`)
