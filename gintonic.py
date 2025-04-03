#!/usr/bin/env python

import os
import sys
import curses
import curses.textpad as textpad
import collections
import configparser
import logging
import time
import threading
import subprocess

LOG_FORMAT = '%(asctime)s %(message)s'
logging.basicConfig(stream=sys.stderr, level=logging.INFO, format=LOG_FORMAT)

WORK_DIR = os.path.join(os.path.expanduser('~'), '.config/gintonic')
CONFIG_FILE = os.path.join(WORK_DIR, 'config')

SECTION = 'CONFIG'
PATHS_TO_GAMES = 'paths_to_games'

ALL_SYSTEMS = "All systems"
ARCADE = "Arcade"

TOTAL_WIDTH = 160
SYSTEM_WIDTH = 40
GAME_WIDTH = TOTAL_WIDTH - SYSTEM_WIDTH

exited = False

config = configparser.ConfigParser()

mainwindow = curses.initscr()

systems = []
data = []
arcade_dict = {}


def read_config():
    logging.info('Reading config: ' + CONFIG_FILE)
    config.read(CONFIG_FILE)
    global paths_to_games
    paths_to_games = config.get(SECTION, PATHS_TO_GAMES)


def check_find_system(word, item):
    return word.upper() in item.upper()


def check_find_game(word, item):
    if item[1] == ARCADE and item[2].split(".")[0] in arcade_dict:
        return word.upper() in arcade_dict[item[2].split(".")[0]].upper()
    else:
        return word.upper() in item[2].upper()


def fill_arcade_dictionary():
    global arcade_dict

    mame_list = subprocess.run(['mame', '-listfull'], stdout=subprocess.PIPE).stdout.decode('utf-8')
    for line in mame_list.split('\n')[1:-1]:
        file_name = line[:line.index(" ")]
        human_name = line[line.index(" "):].lstrip()[1:-1]
        arcade_dict[file_name] = human_name


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
                dat = (' ' + systems[pos][1] + ' ' * TOTAL_WIDTH)[:self.syswin.getmaxyx()[1] - 3] + ' '
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
            if check_find_system(word, systems[i][1]):
                return i
        for i in range(pos):
            if check_find_system(word, systems[i][1]):
                return i
        return -1

    def find_next(self, word):
        pos = self.list_pos() + 1
        if pos >= len(systems):
            pos = 0
        for i in range(pos, len(systems)):
            if check_find_system(word, systems[i][1]):
                return i
        for i in range(pos):
            if check_find_system(word, systems[i][1]):
                return i
        return -1

    def find_prev(self, word):
        if len(systems) == 0:
            return -1
        pos = self.list_pos() - 1
        if pos < 0:
            pos = len(systems) - 1
        for i in range(pos, -1, -1):
            if check_find_system(word, systems[i][1]):
                return i
        for i in range(len(systems) - 1, pos, -1):
            if check_find_system(word, systems[i][1]):
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
        if data:
            return data[self.list_pos()]

    def draw(self):
        pos = self.offset
        for i in range(self.syswin.getmaxyx()[0]-2):
            style = 0
            if pos == self.list_pos():
                style = curses.A_STANDOUT
            if pos < len(data):
                if data[pos][1] == ARCADE and data[pos][2].split(".")[0] in arcade_dict:
                    dat = (' ' + arcade_dict[data[pos][2].split(".")[0]] + ' ' * 100)[:self.gameswin.getmaxyx()[1] - 3] + ' '
                else:
                    dat = (' ' + data[pos][2] + ' ' * 100)[:self.gameswin.getmaxyx()[1] - 3] + ' '
                self.gameswin.addstr(i + 1, 1, dat, style)
                dat = (' ' + data[pos][1] + ' ' * 100)[:self.syswin.getmaxyx()[1] - 3] + ' '
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
        if self.list_pos() < len(data) - 1:
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
        if (pos >= 0) and (pos < len(data)):
            half = self.syswin.getmaxyx()[0] // 2
            self.offset = max(pos - half, 0)
            self.pos = pos - self.offset
        self.draw()

    def find_word(self, word):
        pos = self.list_pos()
        for i in range(pos, len(data)):
            if check_find_game(word, data[i]):
                return i
        for i in range(pos):
            if check_find_game(word, data[i]):
                return i
        return -1

    def find_next(self, word):
        pos = self.list_pos() + 1
        if pos >= len(data):
            pos = 0
        for i in range(pos, len(data)):
            if check_find_game(word, data[i]):
                return i
        for i in range(pos):
            if check_find_game(word, data[i]):
                return i
        return -1

    def find_prev(self, word):
        if len(data) == 0:
            return -1
        pos = self.list_pos() - 1
        if pos < 0:
            pos = len(data) - 1
        for i in range(pos, -1, -1):
            if check_find_game(word, data[i]):
                return i
        for i in range(len(data) - 1, pos, -1):
            if check_find_game(word, data[i]):
                return i
        return -1


system_menu = None
game_menu = None
current_menu_is_systems = True
search_window = None


def open_system(selected_system_tuple):
    close_curses()

    # TODO move this make_index, and within make_index, use similar logic to fill the arcade list with the first part of the output of mame -listfull. but also make sure it's ordered according to the display name?
    global arcade_dict
    if not arcade_dict:
        if selected_system_tuple[1] in [ALL_SYSTEMS, ARCADE]:
            fill_arcade_dictionary()

    make_index(*selected_system_tuple)
    init_curses()
    curses.flushinp()
    search_window.draw()
    global current_menu_is_systems
    current_menu_is_systems = False
    game_menu.reset_pos()
    game_menu.draw()


def launch_game(game_tuple):
    close_curses()
    print(f"RUNNING: {game_tuple}")
    path = game_tuple[0]
    system = game_tuple[1]
    game = game_tuple[2]
    run_option = "run_mame" if system == ARCADE else 'run_'+system
    full_path = os.path.join(path, game) if system == ARCADE else os.path.join(path, system, game)
    args = config.get(SECTION, run_option).format(full_path)
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
        make_systems(paths_to_games)
        global systems
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


def is_config_option_valid(option):
    return config.has_option(SECTION, option) and config.get(SECTION, option) != ""


def make_systems(paths):
    global systems
    
    for path in paths.split(";"):
        sys_list = [(path, system) for system in os.listdir(path)]
        # Only display systems that have a valid launcher in the config file
        systems.extend(list(filter(lambda sys_tuple: is_config_option_valid('run_'+sys_tuple[1]), sys_list)))
    systems.sort(key=lambda sys_tuple: sys_tuple[1])

    systems.insert(0, ("", ALL_SYSTEMS))

    if is_config_option_valid('path_to_mame') and is_config_option_valid('run_mame'):
        systems.insert(1, (config.get(SECTION, 'path_to_mame'), ARCADE))


def make_index(path, selected_system):
    global data
    global systems

    data.clear()

    if selected_system == ALL_SYSTEMS:
        system_list = systems[1:] # removing ALL_SYSTEMS
        for system in system_list:
            if system[1] == ARCADE:
                games = os.listdir(system[0])
                for game in games:
                    data.append((system[0], system[1], game))
            else:
                games = os.listdir(system[0] + os.sep + system[1])
                for game in games:
                    data.append((system[0], system[1], game))
    elif selected_system == ARCADE:
        games = os.listdir(path)
        for game in games:
            data.append((path, selected_system, game))
            #data.sort(key=lambda game_tuple: arcade_dict[game_tuple[2].split(".")[0]] if game_tuple[2].split(".")[0] in arcade_dict else game_tuple[2])
    else:
        games = os.listdir(path + os.sep + selected_system)
        for game in games:
            data.append((path, selected_system, game))


if __name__ == '__main__':
    main()
