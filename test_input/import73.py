class AbstractLib:
    ""
    def __init__(self):
        pass

    def abstract(self):
        "This is doc"
        "this is an expression, sneaky"
        raise SystemError("This method must be overridden")
