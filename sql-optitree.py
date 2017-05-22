#!/usr/bin/env python

import tkinter
from tkinter import ttk

class App:
    def __init__(self, root):
        self.root = root
        self.root.title('SQL Optitree')
        ttk.Frame(self.root, width=800, height=600).pack()
        ttk.Label(self.root, text='SQL Optitree').place(x=10, y=10)

if __name__ == '__main__':
    root = tkinter.Tk()
    App(root)
    root.mainloop()
