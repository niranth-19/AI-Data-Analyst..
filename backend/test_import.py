import sys
print("Python path:", sys.path)
import os
print("CWD:", os.getcwd())
import app
print("app imported successfully")
print("app location:", app.__file__)