"Main module for running pychecker a Tkinter GUI for all the options"

import sys

from OptionTypes import *

import Config

class ConfigDialog:
    "Dialog for editiong options"
    
    def __init__(self, tk):
        self._tk = tk
        self._cfg, _, _ = Config.setupFromArgs(sys.argv)

        self._opts = []
        self._optMap = {}
        for opt in Config._OPTIONS:
            field = None
            if opt:
                _, useValue, longArg, member, description = opt
                value = None
                if member:
                    value = getattr(self._cfg, member)
                    description = member + ": " + description.capitalize()
                tk.option_add('*' + longArg + ".help", description)
                if useValue:
                    if type(value) == type([]):
                        field = List(longArg, value)
                    elif type(value) == type(1):
                        field = Number(longArg, int(value))
                    elif type(value) == type(''):
                        field = Text(longArg, value)
                    else:
                        field = Boolean(longArg, value)
                else:
                    field = Boolean(longArg, value)
                self._optMap[longArg] = field
            self._opts.append(field)
        self._help = None

    def help(self, w):
        if self._help != w:
            help = w.option_get("help", "help")
            self._help.configure(text=help)

    def focus(self, ev):
        self.help(ev.widget)

    def click(self, ev):
        self.help(ev.widget)

    def main(self):
        frame = Tkinter.Frame(self._tk, name="opts")
        frame.grid()
        tk.option_readfile('Options.ad')
        self._fields = {}
        row = 0
        col = 0
        for opt in self._opts:
            if opt:
                f = opt.field(frame)
                f.grid(row=row, col=col, sticky=Tkinter.E + Tkinter.W)
                row += 1
            else:
                col += 1
                row = 0
        for c in range(col):
            frame.columnconfigure(c, weight=1)

        self._help = Tkinter.Label(tk, name="helpBox")
        self._help.grid(row)
        self._help.config(takefocus=0)
        buttons = Tkinter.Frame(tk, name="buttons")
        ok = Tkinter.Button(buttons, name="ok", command=self.ok)
        ok.grid(row=row, col=0)
        default = Tkinter.Button(buttons, name="default", command=self.default)
        default.grid(row=row, col=1)
        cancel = Tkinter.Button(buttons, name="cancel", command=self.cancel)
        cancel.grid(row=row, col=2)
        buttons.grid()
        
        tk.bind_all('<FocusIn>', self.focus)
        tk.bind_all('<Enter>', self.focus)
        tk.bind_all('<ButtonPress>', self.click)
        tk.mainloop()

    def ok(self):
        opts = []
        # Pull command-line args
        for opt in self._opts:
            if opt:
                arg = opt.arg()
                if arg:
                    opts.append(arg)
        print 'opts', opts

        # Calculate config
        self._cfg, _, _ = Config.setupFromArgs(opts)

        # Set controls based on new config
        for opt in Config._OPTIONS:
            if opt:
                _, _, longArg, member, _ = opt
                if member:
                    self._optMap[longArg].set(getattr(self._cfg, member))

    def default(self):
        self._cfg, _, _ = Config.setupFromArgs(sys.argv)
        for opt in Config._OPTIONS:
            if opt:
                _, _, longArg, member, _ = opt
                if member:
                    self._optMap[longArg].set(getattr(self._cfg, member))
                else:
                    self._optMap[longArg].set(0)

    def cancel(self):
        sys.exit(0)


if __name__=='__main__':
    tk = Tkinter.Tk()
    tk.title('PyChecker')
    ConfigDialog(tk).main()
