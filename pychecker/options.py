"Main module for running pychecker a Tkinter GUI for all the options"

import sys

from OptionTypes import *
from string import capitalize, strip

import Config

MAX_SUBBOX_ROWS = 7
MAX_BOX_COLS = 3

class ConfigDialog:
    "Dialog for editiong options"
    
    def __init__(self, tk):
        self._tk = tk
        self._cfg, _, _ = Config.setupFromArgs(sys.argv)

        self._optMap = {}
        self._opts = []
        for name, group in Config._OPTIONS:
          opts = []
          for _, useValue, longArg, member, description in group:
              value = None
              if member:
                  value = getattr(self._cfg, member)
                  description = member + ": " + capitalize(description)
                  description = strip(description)
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
              opts.append(field)
          self._opts.append( (name, opts))
        self._help = None

    def help(self, w):
        if self._help != w:
            help = w.option_get("help", "help")
            self._help.configure(text=help)

    def focus(self, ev):
        self.help(ev.widget)

    def click(self, ev):
        self.help(ev.widget)

    def add_fields(self, w, opts):
        count = 0
        for opt in opts:
            f = opt.field(w)
            c, r = divmod(count, MAX_SUBBOX_ROWS)
            f.grid(row=r, col=c, sticky=Tkinter.NSEW)
            count = count + 1

    def add_group(self, w, name, opts):
        colFrame = Tkinter.Frame(w)
        
        label = Tkinter.Label(colFrame, text=name + ":")
        label.grid(row=0, col=0, sticky=Tkinter.NSEW)
        
        gframe = Tkinter.Frame(colFrame, relief=Tkinter.GROOVE, borderwidth=2)
        gframe.grid(row=1, col=0, sticky=Tkinter.NSEW)
        self.add_fields(gframe, opts)
        
        label = Tkinter.Label(colFrame)
        label.grid(row=2, col=0, sticky=Tkinter.NSEW)
        colFrame.rowconfigure(2, weight=1)
        return colFrame

    def main(self):
        frame = Tkinter.Frame(self._tk, name="opts")
        frame.grid()
        tk.option_readfile('Options.ad')
        self._fields = {}
        row, col = 0, 0
        rowFrame = Tkinter.Frame(frame)
        rowFrame.grid(row=row)
        row = row + 1
        for name, opts in self._opts:
            w = self.add_group(rowFrame, name, opts)
            w.grid(row=row, col=col, sticky=Tkinter.NSEW)
            col = col + 1
            if col >= MAX_BOX_COLS:
                rowFrame=Tkinter.Frame(frame)
                rowFrame.grid(row=row, sticky=Tkinter.NSEW)
                col = 0
                row = row + 1

        self._help = Tkinter.Label(tk, name="helpBox")
        self._help.grid(row=row)
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
        for name, group in self._opts:
            for opt in group:
                arg = opt.arg()
                if arg:
                    opts.append(arg)
        print 'opts', opts

        # Calculate config
        self._cfg, _, _ = Config.setupFromArgs(opts)

        # Set controls based on new config
        for name, group in Config._OPTIONS:
            for _, _, longArg, member, _ in group:
                if member:
                    self._optMap[longArg].set(getattr(self._cfg, member))

    def default(self):
        self._cfg, _, _ = Config.setupFromArgs(sys.argv)
        for _, group in Config._OPTIONS:
            for _, _, longArg, member, _ in group:
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
