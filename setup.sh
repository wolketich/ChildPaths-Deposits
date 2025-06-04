#!/bin/bash

# Set root folder
ROOT="childpaths-deposit-cli"

# Create directories
mkdir -p $ROOT/{src/utils,data}
cd $ROOT

# Create base files
touch .env README.md deposit_tool.log requirements.txt

# Create Python module files
touch src/deposit_tool.py
touch src/utils/{__init__.py,cli.py,login.py,branch.py,account.py,transactions.py}

# Create data and config files
touch data/{billpayers_cache.json,settings.json}

echo "Project structure created in $ROOT"

