#!/bin/bash

set -euo pipefail

if [ ! -d "./.git" ]; then
    echo "Error: current working directory isn't checked out from git"
    exit 1
fi

# Check that python modules 'venv' and 'ensurepip' are available.
# These are required to successfully create the python virtual environment.
py_venv_status=0
python3 -c "import venv" 2> /dev/null || py_venv_status=$?
py_ensurepip_status=0
python3 -c "import ensurepip" 2> /dev/null || py_ensurepip_status=$?
if [[ $py_venv_status -ne 0 || $py_ensurepip_status -ne 0 ]]; then
    if [ $py_venv_status -ne 0 ]; then echo "Error: missing python module 'venv'"; fi
    if [ $py_ensurepip_status -ne 0 ]; then echo "Error: missing python module 'ensurepip'"; fi
    echo "Please install python3-venv:"
    echo "  sudo apt-get install -y python3-venv"
    exit 1
fi

ansible_dir="${HOME}/.ansible"
PATH="${ansible_dir}/venv/bin:${PATH}"

# Create python virtual environment and install python requirements
echo "==================== Preparing python virtual environment ===================="
if [ -d "${ansible_dir}/venv" ]; then
    /usr/bin/python3 -m venv --upgrade "${ansible_dir}/venv"
else
    /usr/bin/python3 -m venv "${ansible_dir}/venv"
fi

pip install --upgrade setuptools wheel pip
pip install --upgrade --requirement requirements.txt

echo "==================== Updating ansible roles ===================="

ansible-galaxy install --force --roles-path "${ansible_dir}/roles" -r requirements.yml

echo "==================== Updating ansible collections ===================="

ansible-galaxy collection install --force --force-with-deps --collections-path "${ansible_dir}/collections" -r requirements.yml

# Write a stamp so we can monitor when boot.sh was last run
git log -n 1 --pretty=format:%H -- requirements.yml > "${ansible_dir}/.stamp"
git log -n 1 --pretty=format:%H -- requirements.txt > "${ansible_dir}/venv/.stamp"

echo ""
echo "To use the python virtual environment run one of these commands:"
echo "  1. source ${ansible_dir}/venv/bin/activate"
echo "  2. export PATH=\"${ansible_dir}/venv/bin:\$PATH\""
echo "     or add it to ~/.profile or ~/.bashrc"
echo "  3. ./venv [ansible command] [arguments]"
