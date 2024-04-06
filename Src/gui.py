import configparser
import os
import threading
import traceback
from tkinter import *

import cv2
import numpy as np

# internal
import bot_handler
import bot_logger

placeholder_epic = "Request epic unit"
placeholder_common_rare = "Request common/rare unit"


class Constants:
    BG_COLOR = '#575559'
    FG_COLOR = '#ffffff'


# GUI Class
class RR_bot:

    def __init__(self):

        self.root = create_base()
        self.selected_units = []

        # Option vars
        self.ads_var = IntVar()
        self.pve_var = IntVar()
        self.clan_collect_var = IntVar()
        self.clan_tournament_var = IntVar()
        self.request_epic_var = StringVar()
        self.request_common_rare_var = StringVar()
        self.shaman_var = IntVar()
        self.treasure_map_green_var = IntVar()
        self.treasure_map_gold_var = IntVar()
        self.mana_vars = [IntVar()]
        self.shop_vars = [IntVar()]
        self.floor = StringVar()

        self.grid_dump = None
        self.unit_dump = None
        self.merge_dump = None
        self.logger_feed = None
        self.bot_instance = None

        # State variables
        self.stop_flag = False
        self.running = False
        self.info_ready = threading.Event()
        # Read config file
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        # Create tkinter window base

        # Add frames
        self.setup_options_frame()
        self.setup_combat_frame()
        self.setup_action_frame()
        self.setup_logger_frame()

        self.logger = bot_logger.create_log_feed(self.logger_feed)

        self.logger.debug('GUI started!')
        self.root.mainloop()

    # Clear loggers, collect threads, and close window
    def __exit__(self, exc_type, exc_value, traceback):
        self.logger.info('Exiting GUI')
        self.logger.handlers.clear()
        self.thread_run.join()
        # self.thread_init.join() # I don't think this is valid?
        self.root.destroy()
        try:
            self.bot_instance.client.stop()
        except:
            pass

    def setup_options_frame(self):
        frame = Frame(self.root)
        create_options(self, frame, self.config)
        frame.pack(padx=0, pady=0, side=TOP, anchor=NW)

    def setup_combat_frame(self):
        frame = Frame(self.root)
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        bg = Constants.BG_COLOR
        fg = Constants.FG_COLOR

        # Create text widgets
        self.grid_dump = Text(frame, height=18, width=60, bg=bg, fg=fg)
        self.grid_dump.grid(row=0, sticky=S)

        self.unit_dump = Text(frame, height=10, width=30, bg=bg, fg=fg)
        self.unit_dump.grid(row=1, column=0, sticky=W)

        self.merge_dump = Text(frame, height=10, width=30, bg=bg, fg=fg)
        self.merge_dump.grid(row=1, column=0, sticky=E)

        frame.pack(padx=10, pady=10, side=RIGHT, anchor=SE)

    def setup_action_frame(self):
        bg = Constants.BG_COLOR

        frame = Frame(self.root, bg=bg)
        frame.grid_columnconfigure(0, weight=1)

        start_button = Button(frame, text='Start Bot', command=self.start_command)
        start_button.grid(row=0, column=1, padx=10)

        stop_button = Button(frame, text='Stop Bot', command=self.stop_bot, padx=20)
        stop_button.grid(row=0, column=2, padx=5)

        bg2 = '#ff0000'
        fg2 = '#000000'
        leave_dungeon = Button(frame, text='Quit Floor/PvP', command=self.leave_game, bg=bg2, fg=fg2)
        leave_dungeon.grid(row=0, column=3, padx=5)

        frame.pack(padx=10, pady=10, side=BOTTOM, anchor=SW)

    def setup_logger_frame(self):
        frame = Frame(self.root)
        bg = Constants.BG_COLOR
        fg = Constants.FG_COLOR

        self.logger_feed = Text(frame, height=30, width=38, bg=bg, fg=fg, wrap=WORD, font=('Consolas', 9))
        self.logger_feed.grid(row=0, sticky=S)
        # Setup & Connect logger to text widget

        frame.pack(padx=10, pady=10, side=LEFT, anchor=SW)

    # Initialize the thread for main bot
    def start_command(self):
        self.stop_flag = False
        self.save_config()
        if self.running:
            return
        self.running = True
        # Start main thread
        self.thread_run = threading.Thread(target=self.start_bot, args=())
        self.thread_run.start()

    # Update config file
    def save_config(self):
        # Update config
        card_level = np.array([var.get() for var in self.mana_vars]) * np.arange(1, 6)
        card_level = card_level[card_level != 0]
        shop_item = np.array([var.get() for var in self.shop_vars]) * np.arange(1, 7)
        shop_item = shop_item[shop_item != 0]

        self.config.read('config.ini')
        self.config['bot']['floor'] = str(self.floor.get())
        self.config['bot']['mana_level'] = np.array2string(card_level, separator=',')[1:-1]
        self.config['bot']['shop_item'] = np.array2string(shop_item, separator=',')[1:-1]
        self.config['bot']['pve'] = str(bool(self.pve_var.get()))
        self.config['bot']['clan_collect'] = str(bool(self.clan_collect_var.get()))
        self.config['bot']['clan_tournament'] = str(bool(self.clan_tournament_var.get()))
        self.config['bot']['request_epic'] = "" if self.request_epic_var.get() == placeholder_epic else str(
            self.request_epic_var.get())
        self.config['bot'][
            'request_common_rare'] = "" if self.request_common_rare_var.get() == placeholder_common_rare else str(
            self.request_common_rare_var.get())
        self.config['bot']['watch_ad'] = str(bool(self.ads_var.get()))
        self.config['bot']['require_shaman'] = str(bool(self.shaman_var.get()))
        self.config['bot']['treasure_map_green'] = str(bool(self.treasure_map_green_var.get()))
        self.config['bot']['treasure_map_gold'] = str(bool(self.treasure_map_gold_var.get()))
        with open('config.ini', 'w') as configfile:
            self.config.write(configfile)
        self.logger.info('Stored settings to config!')

    # Update unit selection
    def update_units(self):
        self.selected_units = self.config['bot']['units'].replace(' ', '').split(',')
        self.logger.info(f'Selected units: {", ".join(self.selected_units)}')
        self.selected_units = bot_handler.select_units([unit + '.png' for unit in self.selected_units])

        # if not bot_handler.select_units([unit + '.png' for unit in self.selected_units]):
        #     valid_units = ' '.join(os.listdir("all_units")).replace('.png', '').split(' ')
        #     self.logger.info(f'Invalid units in config file! Valid units: {valid_units}')

    # Run the bot
    def start_bot(self):
        # Run startup of bot instance
        self.logger.warning('Starting bot...')
        self.bot_instance = bot_handler.start_bot_class(self.logger)
        path = os.path.join('src', 'startup_message.txt')
        os.system(f'type {path}')

        self.update_units()
        infos_ready = threading.Event()

        # Pass gui info to bot
        self.bot_instance.bot_stop = False
        self.bot_instance.logger = self.logger
        self.bot_instance.config = self.config
        self.bot_instance.selected_units = self.selected_units

        bot = self.bot_instance
        # Start bot thread
        thread_bot = threading.Thread(target=bot_handler.bot_loop, args=([bot, infos_ready]))
        thread_bot.start()

        # Dump infos to gui whenever ready
        while True:
            infos_ready.wait(timeout=5)
            self.update_text(bot.combat_step, bot.combat, bot.output, bot.grid_df, bot.unit_series, bot.merge_series,
                             bot.info)
            infos_ready.clear()

            if self.stop_flag:
                self.bot_instance.bot_stop = True
                self.logger.warning('Exiting main loop...')
                thread_bot.join()
                self.bot_instance.client.stop()
                self.logger.info('Bot stopped!')
                self.logger.critical('Safe to close gui')
                return

    # Raise stop flag to threads
    def stop_bot(self):
        self.running = False
        self.stop_flag = True
        self.bot_instance.stop_flag = True
        self.logger.info('Stopping bot!')

    # Leave current game
    def leave_game(self):
        # check if bot_instance exists
        if hasattr(self, 'bot_instance'):
            thread_bot = threading.Thread(target=self.bot_instance.restart_rr, args=([True]))
            thread_bot.start()
        else:
            self.logger.warning('Bot has not been started yet!')

    # Update text widgets with latest info
    def update_text(self, i, combat, output, grid_df, unit_series, merge_series, info):
        # info + general info
        if grid_df is not None:
            grid_df['unit'] = grid_df['unit'].apply(lambda x: x.replace('.png', ''))
            grid_df['unit'] = grid_df['unit'].apply(lambda x: x.replace('empty', '-'))
            avg_age = str(grid_df['Age'].mean().round(2))
            write_to_widget(
                self.root, self.grid_dump,
                f'{combat}, {i + 1}/8 {output}, {info}\n{grid_df.to_string()}\nAverage age: {avg_age}'
            )
        if unit_series is not None:
            # unit_series['unit'] = unit_series['unit'].apply(lambda x: x.replace('.png',''))
            write_to_widget(self.root, self.unit_dump, unit_series.to_string())
        if merge_series is not None:
            # merge_series['unit'] = merge_series['unit'].apply(lambda x: x.replace('.png',''))
            write_to_widget(self.root, self.merge_dump, merge_series.to_string())


###
### END OF GUI CLASS
###

def save_grid(self):
    if self.bot_instance is None:
        self.logger.info('Bot isn\'t started!')
        return

    if not os.path.isdir('debug'):
        os.mkdir('debug')

    for name, img in self.bot_instance.selected_units_crop.items():
        cv2.imwrite(f'debug/{name}.png', img)
    self.logger.info('Done saving images!')


def create_options(self, frame, config):
    frame.grid_rowconfigure(0, weight=1)
    frame.grid_columnconfigure(0, weight=1)

    # General options
    Label(frame, text='Options', justify=LEFT).grid(row=0, column=0, sticky=W)
    self.pve_var = IntVar(value=int(config.getboolean('bot', 'pve', fallback=False)))
    self.ads_var = IntVar(value=int(config.getboolean('bot', 'watch_ad', fallback=False)))
    self.shaman_var = IntVar(value=int(config.getboolean('bot', 'require_shaman', fallback=False)))
    self.treasure_map_green_var = IntVar(value=int(config.getboolean('bot', 'treasure_map_green', fallback=False)))
    self.treasure_map_gold_var = IntVar(value=int(config.getboolean('bot', 'treasure_map_gold', fallback=False)))
    self.clan_tournament_var = IntVar(value=int(config.getboolean('bot', 'clan_tournament', fallback=False)))
    self.clan_collect_var = IntVar(value=int(config.getboolean('bot', 'clan_collect', fallback=False)))
    self.request_epic_var = StringVar(value=str(config.get('bot', 'request_epic', fallback='')))
    self.request_common_rare_var = StringVar(value=str(config.get('bot', 'request_common_rare', fallback='')))

    Checkbutton(frame, text='PvE', variable=self.pve_var, justify=LEFT).grid(row=0, column=1, sticky=W)
    Checkbutton(frame, text='ADs', variable=self.ads_var, justify=LEFT).grid(row=0, column=2, sticky=W)
    Checkbutton(frame, text='Treasure map green', variable=self.treasure_map_green_var,
                justify=LEFT).grid(row=0, column=3, sticky=W)
    Checkbutton(frame, text='Treasure map gold', variable=self.treasure_map_gold_var,
                justify=LEFT).grid(row=0, column=4, sticky=W)
    Checkbutton(frame, text='Req Shaman *For PvE ONLY*', variable=self.shaman_var,
                justify=LEFT).grid(row=0, column=5,sticky=W)

    # Clan options
    Label(frame, text='Clan options', justify=LEFT).grid(row=1, column=0, sticky=W)
    Checkbutton(frame, text='Collect', variable=self.clan_collect_var,
                justify=LEFT).grid(row=1, column=1, sticky=W)
    Checkbutton(frame, text='Tourney', variable=self.clan_tournament_var,
                justify=LEFT).grid(row=1, column=2, sticky=W)

    # Dropdown menu's for clan requests
    # Get the list of .png files for epic units in a folder (replace 'your_folder_path' with your actual folder path)
    folder_path_epic = 'clan_request/epic'
    unit_files_epic = [file.replace('.png', '')
                       for file in os.listdir(folder_path_epic) if file.endswith('.png')]
    folder_path_common_rare = 'clan_request/common_rare'
    unit_files_common_rare = [file.replace('.png', '')
                              for file in os.listdir(folder_path_common_rare) if file.endswith('.png')]

    # Add a placeholder or default item to the list of options for epic units
    unit_files_epic.insert(0, placeholder_epic)
    unit_files_common_rare.insert(0, placeholder_common_rare)

    # Create the epic units dropdown menu with the modified list of options
    unit_dropdown_epic = OptionMenu(frame, self.request_epic_var, *unit_files_epic)
    unit_dropdown_epic.grid(row=1, column=4, sticky=W)
    unit_dropdown_common_rare = OptionMenu(frame, self.request_common_rare_var, *unit_files_common_rare)
    unit_dropdown_common_rare.grid(row=1, column=5, sticky=W)

    # Set the default value to the placeholder text only if request_epic_var is empty
    if not self.request_epic_var.get():
        self.request_epic_var.set(placeholder_epic)
    if not self.request_common_rare_var.get():
        self.request_common_rare_var.set(placeholder_common_rare)

    # Mana level targets
    Label(frame, text='Mana Level Targets', justify=LEFT).grid(row=2, column=0, sticky=W)
    stored_values = np.fromstring(config['bot']['mana_level'], dtype=int, sep=',')
    self.mana_vars = [IntVar(value=int(i in stored_values)) for i in range(1, 6)]
    [
        Checkbutton(frame, text=f'Card {i + 1}', variable=self.mana_vars[i], justify=LEFT).grid(row=2, column=i + 1)
        for i in range(5)
    ]

    # Shop item targets
    Label(frame, text='Shop Item Targets', justify=LEFT).grid(row=3, column=0, sticky=W)
    stored_values = np.fromstring(config['bot']['shop_item'], dtype=int, sep=',')
    self.shop_vars = [IntVar(value=int(i in stored_values)) for i in range(1, 7)]
    [
        Checkbutton(frame, text=f'Shop {i + 1}', variable=self.shop_vars[i], justify=LEFT).grid(row=3, column=i + 1)
        for i in range(6)
    ]

    # Dungeon Floor
    Label(frame, text='Dungeon Floor', justify=LEFT).grid(row=4, column=0, sticky=W)
    self.floor = StringVar(value=str(config.get('bot', 'floor', fallback="1")))
    tmp_floor = int(self.floor.get())
    if tmp_floor <= 0:
        self.floor = "1"
    elif tmp_floor > 13:
        self.floor = "13"

    Entry(frame, name='floor_entry', textvariable=self.floor, width=5).grid(row=4, column=1)

    Button(frame, text='dump imgs', command=lambda: save_grid(self)).grid(row=4, column=2)

def create_base():
    root = Tk()
    root.title('RR bot')
    root.geometry('800x600')
    root.configure(background='#575559')
    root.iconbitmap('calculon.ico')
    root.resizable(False, False)

    return root


# Function to update text widgets
def write_to_widget(root, tbox, text):
    tbox.config(state=NORMAL)
    tbox.delete(1.0, END)
    tbox.insert(END, text)
    tbox.config(state=DISABLED)
    root.update_idletasks()


# Start the actual bot
if __name__ == "__main__":
    try:
        # Your main bot code here
        bot_gui = RR_bot()
    except Exception as e:
        traceback.print_exc()  # Print the traceback including line numbers
        print(f"An error occurred: {e}")
        input("Press Enter to exit...")
