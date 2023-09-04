# gintonic

gintonic is a lightweight game launcher that works in a terminal. It is designed to be fast, to be comfortable for keyboard users and to work through ssh.

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
run_dos = ./dos.sh {0}
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

## Run

* python3 gintonic.py
<br>
If you use gintonic over ssh, run ssh with -X param to have images.
For exit - press q. 

