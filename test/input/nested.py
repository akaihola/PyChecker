# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

class Result:
    def __init__(self):
        self.x = True

def outside():
    result = Result()

    def first():
        result = dict()

    def second():
        # 0.8.19 triggers Object (result) has no attribute (x)
        assert result.x

    first()
    second()

if __name__ == '__main__':
    outside()
