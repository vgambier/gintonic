#!/usr/bin/env python3

import os
import sys
import curses
import curses.textpad as textpad
import collections
import logging
import time
import threading
import subprocess
import json


LOG_FORMAT = '%(asctime)s %(message)s'
logging.basicConfig(stream=sys.stderr, level=logging.INFO, format=LOG_FORMAT)

WORK_DIR = os.path.join(os.path.expanduser('~'), ".config/gintonic")
CONFIG_FILE = os.path.join(WORK_DIR, "config.json")

CONFIG_ENTRY_PATHS_TO_GAMES = "paths_to_games"
CONFIG_ENTRY_PLATFORMS = "platforms"
ALL_SYSTEMS = "All systems"
ARCADE = "Arcade"

TOTAL_WIDTH = 160
SYSTEM_WIDTH = 40
GAME_WIDTH = TOTAL_WIDTH - SYSTEM_WIDTH
exited = False

config = None
mainwindow = curses.initscr()

systems = []
games = []


def read_config():
    logging.info('Reading config: ' + CONFIG_FILE)
    with open(CONFIG_FILE, 'r') as file:
        global config
        config = json.load(file)

def check_find_system(word, item):
    return word.casefold() in item.casefold()


def check_find_game(word, item):
    return word.casefold() in item.name.casefold()


class System:
    def __init__(self, path, name):
        self.path = path
        self.name = name

class Game:
    def __init__(self, path, system, name):
        self.path = path
        self.system = system
        self.name = name

class SearchWindow(object):

    def __init__(self):
        self.swin = curses.newwin(4, 59, 0, 0)
        self.inp = curses.newwin(1, 55, 2, 2)
        self.text = textpad.Textbox(self.inp, insert_mode=False)
        self.history_point = 0
        self.search_history = collections.deque(maxlen=100)

    def resize(self):
        self.swin.resize(4, 158)
        self.inp.resize(1, 55)

    def draw(self):
        self.swin.addstr(1, 80, 'Search')
        self.swin.border()
        self.swin.refresh()
        self.inp.refresh()

    def _handle_key(self, x):
        if x == curses.KEY_UP:
            if self.history_point < len(self.search_history):
                self.history_point += 1
                self.inp.erase()
                self.inp.addstr(0, 0, self.search_history[-self.history_point])
        if x == curses.KEY_DOWN:
            if self.history_point > 1:
                self.history_point -= 1
                self.inp.erase()
                self.inp.addstr(0, 0, self.search_history[-self.history_point])
        if x == 27:
            self.canceled = True
            return 7
        if x == 10:
            return 7
        return x

    def enter(self):
        self.history_point = 0
        curses.curs_set(1)
        curses.setsyx(2, 2)
        curses.doupdate()
        self.inp.erase()
        self.canceled = False
        res = self.text.edit(self._handle_key).strip()
        curses.curs_set(0)
        if self.canceled:
            self.inp.erase()
            self.inp.refresh()
            return ''
        elif (not(self.search_history) or self.search_history[-1] != res):
                self.search_history.append(res)
        return res

class SystemMenu(object):

    def __init__(self, mainwindow):
        self.main = mainwindow
        size = mainwindow.getmaxyx()
        self.syswin = curses.newwin(size[0]-5, TOTAL_WIDTH, 4, 0)
        self.offset = 0
        self.pos = 0
        self.search_pos = 0

    def resize(self):
        size = self.main.getmaxyx()
        if (size[0] > 10) and (size[1] > 20):
            self.syswin.resize(size[0]-5, min(TOTAL_WIDTH, size[1]))
            self.syswin.mvwin(4, 0)

    def list_pos(self):
        return self.offset + self.pos

    def current_item(self):
        if systems:
            return systems[self.list_pos()]

    def draw(self):
        pos = self.offset
        for i in range(self.syswin.getmaxyx()[0]-2):
            style = 0
            if pos == self.list_pos():
                style = curses.A_STANDOUT
            if pos < len(systems):
                dat = (' ' + systems[pos].name + ' ' * TOTAL_WIDTH)[:self.syswin.getmaxyx()[1] - 3] + ' '
                self.syswin.addstr(i + 1, 1, dat, style)
            else:
                self.syswin.addstr(i + 1, 1, (' '*TOTAL_WIDTH)[:self.syswin.getmaxyx()[1] - 2])
            pos += 1
        self.main.addstr(self.main.getmaxyx()[0] - 1, 0,
                         '(q)uit, l or Enter launch, / search, (n)ext, N prev. Navigate with j/k/up/down/wheel. Navigate search history with up/down.'[:self.main.getmaxyx()[1]-1])
        self.main.refresh()
        self.syswin.border()
        self.syswin.refresh()

    def move_down(self):
        if self.list_pos() < len(systems) - 1:
            if self.pos < self.syswin.getmaxyx()[0]-3:
                self.pos += 1
            else:
                self.offset += 1
        self.draw()

    def move_up(self):
        if self.list_pos() > 0:
            if self.pos > 0:
                self.pos -= 1
            else:
                self.offset -= 1
        self.draw()

    def center(self, pos):
        if (pos >= 0) and (pos < len(systems)):
            half = self.syswin.getmaxyx()[0] // 2
            self.offset = max(pos - half, 0)
            self.pos = pos - self.offset
        self.draw()

    def find_word(self, word):
        pos = self.list_pos()
        for i in range(pos, len(systems)):
            if check_find_system(word, systems[i].name):
                return i
        for i in range(pos):
            if check_find_system(word, systems[i].name):
                return i
        return -1

    def find_next(self, word):
        pos = self.list_pos() + 1
        if pos >= len(systems):
            pos = 0
        for i in range(pos, len(systems)):
            if check_find_system(word, systems[i].name):
                return i
        for i in range(pos):
            if check_find_system(word, systems[i].name):
                return i
        return -1

    def find_prev(self, word):
        if len(systems) == 0:
            return -1
        pos = self.list_pos() - 1
        if pos < 0:
            pos = len(systems) - 1
        for i in range(pos, -1, -1):
            if check_find_system(word, systems[i].name):
                return i
        for i in range(len(systems) - 1, pos, -1):
            if check_find_system(word, systems[i].name):
                return i
        return -1


class GameMenu(object):

    def __init__(self, mainwindow):
        self.main = mainwindow
        size = mainwindow.getmaxyx()
        self.syswin = curses.newwin(size[0]-5, min(SYSTEM_WIDTH, size[1]), 4, 0)
        self.gameswin = curses.newwin(size[0]-5, min(GAME_WIDTH, max(0, size[1] - SYSTEM_WIDTH)), 4, SYSTEM_WIDTH)
        self.offset = 0
        self.pos = 0
        self.search_pos = 0

    def resize(self):
        size = self.main.getmaxyx()
        if (size[0] > 10) and (size[1] > 20):
            self.syswin.resize(size[0]-5, min(SYSTEM_WIDTH, size[1]))
            self.gameswin.resize(size[0]-5, min(GAME_WIDTH, max(0, size[1] - SYSTEM_WIDTH)))
            self.syswin.mvwin(4, 0)
            self.gameswin.mvwin(4, SYSTEM_WIDTH)

    def refresh_window(self):
        self.gameswin.erase()
        self.gameswin.addstr(0, 0, '')
        self.gameswin.refresh()

    def reset_pos(self):
        self.pos = 0
        self.offset = 0

    def list_pos(self):
        return self.offset + self.pos

    def current_item(self):
        if games:
            return games[self.list_pos()]

    def draw(self):
        pos = self.offset
        for i in range(self.syswin.getmaxyx()[0]-2):
            style = 0
            if pos == self.list_pos():
                style = curses.A_STANDOUT
            if pos < len(games):
                dat = (' ' + games[pos].name + ' ' * 100)[:self.gameswin.getmaxyx()[1] - 3] + ' '
                self.gameswin.addstr(i + 1, 1, dat, style)
                dat = (' ' + games[pos].system + ' ' * 100)[:self.syswin.getmaxyx()[1] - 3] + ' '
                self.syswin.addstr(i + 1, 1, dat, style)
            else:
                self.gameswin.addstr(i + 1, 1, (' '*100)[:self.gameswin.getmaxyx()[1] - 2])
                self.syswin.addstr(i + 1, 1, (' '*100)[:self.syswin.getmaxyx()[1] - 2])
            pos += 1
        self.main.addstr(self.main.getmaxyx()[0] - 1, 0,
                         '(q)uit, l or Enter launch, / search, (n)ext, N prev. Navigate with j/k/up/down/wheel. Navigate search history with up/down.'[:self.main.getmaxyx()[1]-1])
        self.main.refresh()
        self.syswin.border()
        self.gameswin.border()
        self.syswin.refresh()
        self.gameswin.refresh()

    def move_down(self):
        if self.list_pos() < len(games) - 1:
            if self.pos < self.syswin.getmaxyx()[0]-3:
                self.pos += 1
            else:
                self.offset += 1
        self.draw()

    def move_up(self):
        if self.list_pos() > 0:
            if self.pos > 0:
                self.pos -= 1
            else:
                self.offset -= 1
        self.draw()

    def center(self, pos):
        if (pos >= 0) and (pos < len(games)):
            half = self.syswin.getmaxyx()[0] // 2
            self.offset = max(pos - half, 0)
            self.pos = pos - self.offset
        self.draw()

    def find_word(self, word):
        pos = self.list_pos()
        for i in range(pos, len(games)):
            if check_find_game(word, games[i]):
                return i
        for i in range(pos):
            if check_find_game(word, games[i]):
                return i
        return -1

    def find_next(self, word):
        pos = self.list_pos() + 1
        if pos >= len(games):
            pos = 0
        for i in range(pos, len(games)):
            if check_find_game(word, games[i]):
                return i
        for i in range(pos):
            if check_find_game(word, games[i]):
                return i
        return -1

    def find_prev(self, word):
        if len(games) == 0:
            return -1
        pos = self.list_pos() - 1
        if pos < 0:
            pos = len(games) - 1
        for i in range(pos, -1, -1):
            if check_find_game(word, games[i]):
                return i
        for i in range(len(games) - 1, pos, -1):
            if check_find_game(word, games[i]):
                return i
        return -1


system_menu = None
game_menu = None
current_menu_is_systems = True
search_window = None


def open_system(selected_system):
    close_curses()
    make_index(selected_system)
    init_curses()
    curses.flushinp()
    search_window.draw()
    global current_menu_is_systems
    current_menu_is_systems = False
    game_menu.reset_pos()
    game_menu.draw()


def launch_game(game_obj):
    close_curses()
    path = game_obj.path
    system = game_obj.system
    name = game_obj.name

    print(f"RUNNING: {name}")
    if system == ARCADE:
        full_path = path
    else:
        full_path = os.path.join(path, system, name)

    args = config.get(CONFIG_ENTRY_PLATFORMS).get(system).format(full_path)
    origWD = os.getcwd()
    os.chdir(os.path.dirname(CONFIG_FILE))
    try:
        subprocess.call(args, shell=True)
    except KeyboardInterrupt:
        pass
    os.chdir(origWD)
    init_curses()
    curses.flushinp()
    search_window.draw()
    game_menu.draw()


def init_curses():
    mainwindow.keypad(1)
    curses.noecho()
    curses.cbreak()
    curses.curs_set(0)


def close_curses():
    mainwindow.keypad(0)
    curses.echo()
    curses.nocbreak()
    curses.curs_set(2)
    curses.endwin()


def do_resize():
    mainwindow.clear()

    if current_menu_is_systems:
        system_menu.resize()
        system_menu.draw()
    else:
        game_menu.resize()
        game_menu.draw()

    search_window.resize()
    search_window.draw()


def main_loop():
    while 1:
        time.sleep(0.001)
        c = mainwindow.getch()
        if current_menu_is_systems:
            if c == ord('q'):
                return
            main_loop_systems(c)
        else:
            main_loop_games(c)


def main_loop_systems(c):
    if c == ord('/'):
        word = search_window.enter()
        found = system_menu.find_word(word)
        system_menu.center(found)
    if c == ord('j') or c == curses.KEY_DOWN:
        system_menu.move_down()
    if c == ord('k') or c == curses.KEY_UP:
        system_menu.move_up()
    if c == ord('n'):
        word = search_window.text.gather().strip()
        found = system_menu.find_next(word)
        system_menu.center(found)
    if c == ord('N'):
        word = search_window.text.gather().strip()
        found = system_menu.find_prev(word)
        system_menu.center(found)
    if c == ord('\n') or c == ord('l'):
        current_system = system_menu.current_item()
        open_system(current_system)
    if c == curses.KEY_RESIZE:
        do_resize()


def main_loop_games(c):
    if c == ord('/'):
        word = search_window.enter()
        found = game_menu.find_word(word)
        game_menu.center(found)
    if c == ord('j') or c == curses.KEY_DOWN:
        game_menu.move_down()
    if c == ord('k') or c == curses.KEY_UP:
        game_menu.move_up()
    if c == ord('n'):
        word = search_window.text.gather().strip()
        found = game_menu.find_next(word)
        game_menu.center(found)
    if c == ord('N'):
        word = search_window.text.gather().strip()
        found = game_menu.find_prev(word)
        game_menu.center(found)
    if c == ord('\n') or c == ord('l'):
        cg = game_menu.current_item()
        launch_game(cg)
    if c == ord('q'):
        global current_menu_is_systems
        current_menu_is_systems = True
        init_curses()
        curses.flushinp()
        game_menu.refresh_window()
        search_window.draw()
        system_menu.draw()

    if c == curses.KEY_RESIZE:
        do_resize()

def main():
    global exited
    try:
        read_config()
        paths_to_games = config.get(CONFIG_ENTRY_PATHS_TO_GAMES)
        make_systems(paths_to_games)
        init_curses()
        global system_menu
        global game_menu
        global search_window
        search_window = SearchWindow()
        system_menu = SystemMenu(mainwindow)
        game_menu = GameMenu(mainwindow)
        do_resize()
        main_loop()
    except Exception as e:
        logging.exception(e)
    finally:
        exited = True
        close_curses()


def is_system_config_valid(option):
    return bool(config.get(CONFIG_ENTRY_PLATFORMS).get(option))


def make_systems(paths):
    for path in paths:
        sys_list = [System(path, system) for system in os.listdir(path)]
        # Only display systems that have a valid launcher in the config file
        systems.extend(list(filter(lambda sys_obj: is_system_config_valid(sys_obj.name), sys_list)))
    systems.sort(key=lambda sys_obj: sys_obj.name)

    systems.insert(0, System("", ALL_SYSTEMS))
    # for MAME, we launch arcade games without a filepath
    systems.insert(1, System("", ARCADE))

def add_regular_games(path, selected_system):
    new_games = sorted(os.listdir(path + os.sep + selected_system))
    for game in new_games:
        games.append(Game(path, selected_system, game))


def add_arcade_games(path, selected_system):

    mame_list = subprocess.run(['mame', '-listfull'], stdout=subprocess.PIPE).stdout.decode('utf-8')
    # NB: this list includes consoles
    for line in mame_list.split('\n')[1:-1]:
        file_name = line[:line.index(" ")]
        human_name = line[line.index(" "):].lstrip()[1:-1]
        games.append(Game(file_name, selected_system, human_name))
        # NB: sort is too expensive, we keep the order of mame -listfull which is already somewhat sorted
        #games.sort(key=lambda game_obj: game_obj.name)

def add_games(path, selected_system):
    if selected_system == ARCADE:
        add_arcade_games(path, selected_system)
    else:
        add_regular_games(path, selected_system)


def make_index(selected_system_obj):
    path = selected_system_obj.path
    selected_system = selected_system_obj.name

    games.clear()

    if selected_system == ALL_SYSTEMS:
        system_list = systems[1:] # removing ALL_SYSTEMS
        for system in system_list:
            add_games(system.path, system.name)
    else:
        add_games(path, selected_system)


if __name__ == '__main__':
    main()
