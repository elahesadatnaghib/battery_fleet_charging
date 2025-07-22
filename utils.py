# print project structure

import os

def list_files(startpath):
    for root, dirs, files in os.walk(startpath):
        if (
            './.venv' not in root 
            and '.DS_Store' not in files
            and '__pycache__' not in root):
            level = root.replace(startpath, '').count(os.sep)
            indent = ' ' * 4 * (level)
            print('{}{}/'.format(indent, os.path.basename(root)))
            subindent = ' ' * 4 * (level + 1)
            for f in files:
                print('{}{}'.format(subindent, f))

list_files('.')

