import sys
import os

cdir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(cdir)
from main import app as application
