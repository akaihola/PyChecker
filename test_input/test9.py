
"doc"

import getopt

def test():
    "this should fail (there is no getopt.xyz)"
    try:
        print ""
    except getopt.xyz:
        pass

