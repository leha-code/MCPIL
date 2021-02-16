# -*- coding: utf-8 -*-
#
#  mcpil.py
#  
#  Copyright 2020 Alvarito050506 <donfrutosgomez@gmail.com>
#  Copyright 2020 StealthHydrac/StealthHydra179/a1ma
#  Copyright 2020 JumpeR6790
#  Copyright 2021 LEHAtupointow <pezleha@gmail.com>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; version 2 of the License.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#

import signal

from typing import Dict

from proxy.proxy import Proxy

import launcher
import config

from os import kill, killpg, getpid, getpgid
import platform # this is needed to detemine if you have Linux look lower to get it
import threading # useful, needed for music and other thread things.

from subprocess import Popen

from tkinter import * #importing tkinter for the windows
from tkinter import ttk
from tkinter.messagebox import showerror

from random import choice, randint

import webbrowser

from datetime import date

from PIL import Image, ImageTk

from pydub import AudioSegment
from pydub.playback import play


'''
    Global variables.
'''
background ='cyan'

window: Tk

splashfile = open('spla.shes', 'r')

splashes_list = splashfile.readlines()

SPLASHES = list()

for x in splashes_list:
    x.rstrip('\n')
    SPLASHES.append(x)

SPLASH = choice(SPLASHES)

DESCRIPTIONS = [
    'Classic Minecraft Pi Edition. (Not Recommended)\nNo mods.',
    'Modded Minecraft Pi Edition.\nDefault MCPI-Reborn mods without Touch GUI.',
    'Minecraft Pocket Edition. (Recommended)\nDefault MCPI-Reborn mods.',
    'Custom Profile.\nModify its settings in the Features tab.',
]
current_selection = 0
description_text: Label

launch_button: Button

RENDER_DISTANCES = [
    'Far',
    'Normal',
    'Short',
    'Tiny',
]
current_render_distance: StringVar
current_username: StringVar
current_features = []
feature_widgets: Dict[str, ttk.Checkbutton] = {}

current_process: Popen = None

current_config = {}

proxy_lock = threading.Lock()
proxy_thread: threading.Thread = None
proxy = Proxy()
current_ip: StringVar
current_port: StringVar



'''
    Helper classes.
'''

class Checkbox(ttk.Checkbutton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state = BooleanVar(self)
        self.configure(variable=self.state)

    def checked(self):
        return self.state.get()

    def check(self, val):
        return self.state.set(val)

class HyperLink(Label):
    def __init__(self, parent, url, text=None, fg=None, cursor=None, *args, **kwargs):
        self.url = url
        super().__init__(parent, text=(text or url), fg=(fg or 'blue'), cursor=(cursor or 'hand2'), *args, **kwargs)
        self.bind('<Button-1>', self.web_open)

    def web_open(self, event):
        return webbrowser.open(self.url)

class ScrollableFrame(Frame):
    def __init__(self, root):
        Frame.__init__(self, root)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.canvas = Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.grid(row=0, column=1, sticky='NSE')
        self.canvas.grid(row=0, column=0, sticky='NSEW')

        self.scrollable_frame = ttk.Frame(self.canvas)
        scrollable_frame_id = self.canvas.create_window(0, 0, window=self.scrollable_frame, anchor='nw')

        def configure_scrollable_frame(event):
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        self.scrollable_frame.bind('<Configure>', configure_scrollable_frame)

        def configure_canvas(event):
            self.canvas.itemconfig(scrollable_frame_id, width=event.width)

        self.canvas.bind('<Configure>', configure_canvas)

'''
    Helper functions and back-end.
'''


def playmusic():
    dust_clears = AudioSegment.from_wav("JimHall_thedustclears.wav")
    elsewhere = AudioSegment.from_wav("JimHall_elsewhere.wav")
    boss_theme = AudioSegment.from_wav("swsqr_BossTheme.wav")
    songs = [boss_theme,elsewhere,dust_clears]
    #songs = [dust_clears]
    while True:
        play(choice(songs))

def basename(path):
    return path.split('/')[-1]

# Convert Dict Of Features To List Of Enabled Features
def features_dict_to_list(features: Dict[str, bool]):
    out = []
    for key in features:
        if features[key]:
            out.append(key)
    return out

# Get Features From Selected Mode
def get_features() -> list:
    global current_selection, current_features
    if current_selection == 0:
        # No Mods
        return []
    elif current_selection == 1:
        # Default Mods Minus Touch GUI
        mods = launcher.AVAILABLE_FEATURES.copy()
        mods['Touch GUI'] = False
        return features_dict_to_list(mods)
    elif current_selection == 2:
        # Default Mods
        return features_dict_to_list(launcher.AVAILABLE_FEATURES.copy())
    elif current_selection == 3:
        # Custom Features (Use Features Tab)
        return current_features

# Launch Minecraft
def launch():
    global current_render_distance, current_username, current_process
    launch_button.config(state=DISABLED)
    if current_process is None or current_process.poll() is not None:
        current_process = launcher.run(get_features(), current_render_distance.get(), current_username.get())
    return 0

# Update Launch Button
def update_launch_button():
    global launch_button
    if (current_process is None or current_process.poll() is not None) and launch_button['state'] == DISABLED:
        launch_button.config(state=NORMAL)
    launch_button.after(10, update_launch_button)

# Close MCPIL
def quit():
    global current_process
    if current_process is not None and current_process.poll() is None:
        killpg(getpgid(current_process.pid), signal.SIGTERM)

    window.destroy()
    kill(getpid(), signal.SIGTERM)
    return 0

# Start/Stop Proxy
def update_proxy():
    global proxy, proxy_thread, proxy_lock, current_ip, current_port
    proxy_lock.acquire()
    if proxy_thread is not None:
        proxy.stop()
        proxy_thread.join()
    try:
        proxy.set_option("src_addr", current_ip.get())
        proxy.set_option("src_port", int(current_port.get()))
        proxy_thread = threading.Thread(target=lambda *args: proxy.run())
        proxy_thread.start()
    except ValueError:
        # Invalid Port
        pass
    proxy_lock.release()

# Save/Load Config
def load():
    global current_config, current_render_distance, current_username, current_features, feature_widgets
    current_config = config.load()
    current_render_distance.set(current_config['general']['render-distance'])
    current_username.set(current_config['general']['username'])
    current_features = current_config['general']['custom-features'].copy()
    for key in feature_widgets:
        feature_widgets[key].state(['!alternate'])
        if key in current_features:
            feature_widgets[key].state(['selected'])
        else:
            feature_widgets[key].state(['!selected'])
    current_ip.set(current_config['server']['ip'])
    current_port.set(current_config['server']['port'])
    update_proxy()
def save():
    global current_config, current_render_distance, current_username, current_features
    current_config['general']['render-distance'] = current_render_distance.get()
    current_config['general']['username'] = current_username.get()
    current_config['general']['custom-features'] = current_features.copy()
    current_config['server']['ip'] = current_ip.get()
    current_config['server']['port'] = current_port.get()
    config.save(current_config)

# Update Features From Widgets
def update_features():
    global current_features, feature_widgets
    current_features = []
    for key in feature_widgets:
        if feature_widgets[key].instate(['selected']):
            current_features.append(key)

'''
    Event handlers.
'''

def select_version(version: int):
    global current_selection
    try:
        current_selection = version
        description_text['text'] = DESCRIPTIONS[current_selection]
    except IndexError:
        pass
    except Exception as err:
        return 'Critical error {}'.format(err)
def on_select_versions(event):
    select_version(event.widget.curselection()[0])
    return 0

'''
    Tabs.
'''

def play_tab(parent):
    global description_text, launch_button

    tab = Frame(parent)
    
    '''canvas = Canvas(tab, width=1300, height=700)
    canvas.pack(fill="both", expand=True)

    #canvas.configure(bg='black')

    bgImg = PhotoImage(file="Background.jpg")

    canvas.create_image(1000, 330, image=bgImg)'''
    

    

    title = Label(tab, text='Minecraft Pi Launcher', font=('Minercraftory'))
    title.config(font=('Minercraftory', 24))
    title.grid(row=0)

    
    splash = Label(tab, text=SPLASH.rstrip('\n'), fg="#FFFF19", font=('minecraft',10), borderwidth=2, relief='sunken')
    splash.grid(row=1)

    choose_text = Label(tab, text='Choose a Minecraft version to launch', font=('minecraft',10))
    choose_text.grid(row=2)

    versions_frame = Frame(tab)

    tab.columnconfigure(0, weight=1)
    versions_frame.columnconfigure(0, weight=1)
    tab.rowconfigure(3, weight=1)
    versions_frame.rowconfigure(0, weight=1)

    description_text = Label(versions_frame, text='', wraplength=256, font=('minecraft',10))

    versions = Listbox(versions_frame, selectmode=SINGLE, exportselection=False, font=('minecraft',10))
    versions.insert(0, ' Classic MCPI ')
    versions.insert(1, ' Modded MCPI ')
    versions.insert(2, ' Classic MCPE ')
    versions.insert(3, ' Custom Profile ')
    versions.bind('<<ListboxSelect>>', on_select_versions)
    versions.grid(row=0, column=0, sticky='NSEW')
    if not SPLASH == 'Classic':
        versions.selection_set(2)

    else:
        versions.selection_set(0)
    select_version(versions.curselection()[0])

    description_text.grid(row=0, column=1, pady=48, padx=48, sticky='NSE')

    versions_frame.grid(row=3, sticky='NSEW')

    launch_frame = Frame(tab)
    launch_button = Button(launch_frame, text='Launch', command=launch, font=('minecraft',10))
    launch_button.pack(side=RIGHT, anchor=S)
    launch_frame.grid(row=3, sticky='SE')

    launch_button.after(0, update_launch_button)

    return tab

def settings_tab(parent):
    global current_render_distance, current_username

    tab = Frame(parent)

    tab.rowconfigure(0, weight=1)
    tab.columnconfigure(0, weight=1)

    main_frame = Frame(tab)

    main_frame.columnconfigure(1, weight=1)

    render_distance_label = Label(main_frame, text='Render Distance:')
    render_distance_label.grid(row=0, column=0, padx=6, pady=6, sticky='W')
    current_render_distance = StringVar(main_frame)
    render_distance = ttk.Combobox(main_frame, textvariable=current_render_distance, values=RENDER_DISTANCES, width=24)
    render_distance.state(['readonly'])
    render_distance.grid(row=0, column=1, padx=6, pady=6, sticky='EW')

    username_label = Label(main_frame, text='Username:')
    username_label.grid(row=1, column=0, padx=6, pady=6, sticky='W')
    current_username = StringVar(main_frame)
    username = Entry(main_frame, width=24, textvariable=current_username)
    username.grid(row=1, column=1, padx=6, pady=6, sticky='EW')

    main_frame.grid(row=0, sticky='NEW')

    save_frame = Frame(tab)
    save_button = Button(save_frame, text='Save', command=save)
    save_button.pack(side=RIGHT, anchor=S)
    save_frame.grid(row=1, sticky='SE')

    return tab

def features_tab(parent):
    global feature_widgets

    tab = Frame(parent)

    tab.rowconfigure(0, weight=1)
    tab.columnconfigure(0, weight=1)

    main_frame = ScrollableFrame(tab)

    main_frame.scrollable_frame.columnconfigure(1, weight=1)

    row = 0
    for key in launcher.AVAILABLE_FEATURES:
        check = ttk.Checkbutton(main_frame.scrollable_frame, command=update_features)
        check.grid(row=row, column=0, padx=6, pady=6, sticky='W')
        feature_widgets[key] = check
        label = Label(main_frame.scrollable_frame, text=key)
        label.grid(row=row, column=1, padx=6, pady=6, sticky='W')

        row += 1

    main_frame.grid(row=0, sticky='NSEW')

    save_frame = Frame(tab)
    save_button = Button(save_frame, text='Save', command=save)
    save_button.pack(side=RIGHT, anchor=S)
    save_frame.grid(row=1, sticky='SE')

    return tab

def multiplayer_tab(parent):
    global current_ip, current_port, background

    tab = Frame(parent)

    tab.rowconfigure(0, weight=1)
    tab.columnconfigure(0, weight=1)

    main_frame = Frame(tab)

    main_frame.columnconfigure(1, weight=1)

    ip_label = Label(main_frame, text='IP:')
    ip_label.grid(row=0, column=0, padx=6, pady=6, sticky='W')
    current_ip = StringVar(main_frame)
    current_ip.trace('w', lambda *args: update_proxy())
    ip = Entry(main_frame, width=24, textvariable=current_ip)
    ip.grid(row=0, column=1, padx=6, pady=6, sticky='EW')

    port_label = Label(main_frame, text='Port:')
    port_label.grid(row=1, column=0, padx=6, pady=6, sticky='W')
    current_port = StringVar(main_frame)
    current_port.trace('w', lambda *args: update_proxy())
    port = Entry(main_frame, width=24, textvariable=current_port)
    port.grid(row=1, column=1, padx=6, pady=6, sticky='EW')

    main_frame.grid(row=0, sticky='NEW')

    save_frame = Frame(tab)
    save_button = Button(save_frame, text='Save', command=save)
    save_button.pack(side=RIGHT, anchor=S)
    save_frame.grid(row=1, sticky='SE')

    return tab

def launcher_appearance_tab(parent):
    global current_render_distance, current_username

    tab = Frame(parent)

    tab.rowconfigure(0, weight=1)
    tab.columnconfigure(0, weight=1)

    main_frame = Frame(tab)

    main_frame.columnconfigure(1, weight=1)

    theme_label = Label(main_frame, text='Theme:', font=('minecraft',10))
    theme_label.grid(row=0, column=0, padx=6, pady=6, sticky='W')
    theme = ttk.Combobox(main_frame, textvariable='Choose One', values=['Dark minecraft','Light_minecraft','Banana','Creepy Cyan'], width=24)
    theme.state(['readonly'])
    theme.grid(row=0, column=1, padx=6, pady=6, sticky='EW')


    main_frame.grid(row=0, sticky='NEW')

    save_frame = Frame(tab)
    save_button = Button(save_frame, text='Save', command=None)
    save_button.pack(side=RIGHT, anchor=S)
    save_frame.grid(row=1, sticky='SE')

    return tab

# Get Version
def get_version() -> str:
    try:
        with open('/opt/mcpil/VERSION', 'r') as file:
            return 'v' + file.readline().strip()
    except OSError:
        # File Does Not Exists Or Is Inaccessible
        pass
    return 'Unknown Version'

def about_tab(parent):
    tab = Frame(parent)

    main_frame = Frame(tab)

    main_frame.columnconfigure(0, weight=1)

    title = Label(main_frame, text='Minecraft Pi Launcher', font=('Minercraftory',24))
    title.grid(row=0, sticky='NSEW')

    version = Label(main_frame, text=get_version(), font=('minecraft',10))
    version.grid(row=1, sticky='NSEW')
    
    version = Label(main_frame, text='Music by Jim Hall and sawsquarenoise\n and is Licensed under Creative Commons 4.0', font=('minecraft',10))
    version.grid(row=1, sticky='NSEW')
    

    authors = HyperLink(main_frame, 'https://github.com/MCPI-Revival/MCPIL/graphs/contributors', text='MCPIL is made by all its contributors',
                        fg='black', font=('minecraft',10))
    authors.grid(row=2, sticky='NSEW')

    if randint(1,100) == 11:
        url = HyperLink(main_frame, choice(['https://lehatupointow.blogspot.com',
                                            'https://mcpi.tk',
                                            'https://corgiorgi.com']), font=('minecraft',10))
    else:
        url = HyperLink(main_frame, 'https://github.com/MCPI-Revival/MCPIL', font=('minecraft',10))
    url.grid(row=3, sticky='NSEW')

    main_frame.pack(expand=True)

    return tab
#the function that runs if the __name__ variable is  __main__. This means it runs only if the program is the main module
def main():
    if platform.system() != 'Linux':
        showerror('Error', 'Linux Is Required')
        return 1

    global window

    

    time_now = date.today()
    
    
    window = Tk(className='mcpil')#initialize window
    window.title('MCPIL - Minecraft Pi launcher')#change the window title
    window.geometry('550x512')#make it the specific size
    window.resizable(True, True)#make it rezisable

    theme = ttk.Style()
    theme.theme_create("Minecraft", parent="alt", settings={
        "TNotebook": {"configure": {"tabmargins": [0, 0, 0, 0] } },
        "TNotebook.Tab": {"configure": {"padding": [5, 5],
                                        "font" : ('minecraft', '10')},}})

    theme.theme_create("Minecraft-dark", parent="alt", settings={
        "TNotebook": {"configure": {"tabmargins": [0, 0, 0, 0] } },
        "TNotebook.Tab": {"configure": {"padding": [5, 5],
                                        "font" : ('minecraft', '10'),
                                        'bg' : 'black'},}})
    
    theme.theme_use("Minecraft-dark")


    if not time_now.day == 1 and not time_now.month == 4: #The month and the day isn't the Aprils's fools day
        window.call('wm', 'iconphoto', window._w, PhotoImage(file='mcpil.png'))#set the icon to MCPIL logo
    else:
       window.call('wm', 'iconphoto', window._w, PhotoImage(file='banana.png'))#else it is. Set the icon to a banana


    
    tabs = ttk.Notebook(window)#ibnitialize the Notebook tabs thing
    tabs.add(play_tab(tabs), text='Play')#add the tabs
    tabs.add(features_tab(tabs), text='Features')# the tab functions are making
    tabs.add(multiplayer_tab(tabs), text='Multiplayer')# the tab look specific
    tabs.add(settings_tab(tabs), text='Settings')
    #tabs.add(launcher_appearance_tab(tabs), text='Appearance')
    tabs.add(about_tab(tabs), text='About')
    tabs.pack(fill=BOTH, expand=True)
    load()
    save()

    
    music = threading.Thread(target=playmusic)#add the thread thing
    
    window.wm_protocol('WM_DELETE_WINDOW', quit)
    signal.signal(signal.SIGINT, lambda *args: quit())
    try:
        music.start()#start the music
        window.mainloop()
    except KeyboardInterrupt:
        music.stop()
        quit()

    return 0
#run the main loop
if __name__ == '__main__':
    sys.exit(main())
