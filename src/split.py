import json
import sys


file = json.load(open(sys.argv[1]))

for i, cell in enumerate(file['cells']):
    if cell['cell_type'] == 'code':
        with open(f'./pys/{i}.py', mode="w") as f:
            f.write("".join(cell['source']))
