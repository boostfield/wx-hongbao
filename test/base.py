import sys
import os

cdir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(cdir, '..'))


class AnyThing:
    def __eq__(self, other):
        return True

def anything():
    return AnyThing()
