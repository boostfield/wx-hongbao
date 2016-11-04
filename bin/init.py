#! /usr/bin/env python3

import os
import sys
cdir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(cdir, '..'))
import main
main.init_db()
