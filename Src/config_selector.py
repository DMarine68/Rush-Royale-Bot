import tkinter as tk
from tkinter import messagebox
import shutil
import os

root = tk.Tk()
root.title('Deck')
# Set dark background
root.configure(background='#575559')
# Set window icon to png
root.iconbitmap('calculon.ico')
root.geometry('100x200')


def move_window(event):
    root.geometry('+{0}+{1}'.format(event.x_root, event.y_root))


var = tk.StringVar(value='deck2') # hardcode a deck or something....

tk.Label(root, text='Select Deck').pack()
for i in range(1, 6):
    tk.Radiobutton(root, text=f'Deck {i}', variable=var, value=f'deck{i}').pack()


# Define the copy_file function here
def copy_file():
    try:
        selection = var.get()
        src_file = os.path.join('.', 'configs', f'{selection}.ini')
        dst_file = os.path.join(',', 'config.ini')

        shutil.copy(src_file, dst_file)
        messagebox.showinfo('Copied', f'Copied {selection}.ini')
    except FileNotFoundError:
        messagebox.showwarning('Warning', 'No such file.')


# Create the "Submit" button with the copy_file command
tk.Button(root, text='Submit', command=copy_file).pack()

root.mainloop()
