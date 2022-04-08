#!/usr/bin/env python3
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Helper script for installing spyder and external-deps locally in editable mode.
"""

import argparse
import os
import re
import sys
from logging import Formatter, StreamHandler, getLogger
from pathlib import Path
from pkg_resources import DistributionNotFound, get_distribution
from subprocess import check_output

DEVPATH = Path(__file__).resolve().parent
DEPS_PATH = DEVPATH / 'external-deps'
BASE_COMMAND = [sys.executable, '-m', 'pip', 'install', '--no-deps']

REPOS = {}
for p in DEPS_PATH.iterdir():
    if p.name.startswith('.'):
        continue
    try:
        dist = Path(get_distribution(p.name).location)
    except DistributionNotFound:
        dist = None

    REPOS[p.name] = {'repo': p, 'dist': dist, 'editable': p == dist}

# ---- Setup logger
fmt = Formatter('%(asctime)s [%(levelname)s] [%(name)s] -> %(message)s')
h = StreamHandler()
h.setFormatter(fmt)
logger = getLogger('InstallLocal')
logger.addHandler(h)
logger.setLevel('INFO')


def get_python_lsp_version():
    """Get current version to pass it to setuptools-scm."""
    req_file = DEVPATH / 'requirements' / 'conda.txt'
    with open(req_file, 'r') as f:
        for line in f:
            if 'python-lsp-server' not in line:
                continue

            # Get version part of dependency line
            version = line.strip().split()[1]

            # Get lower bound
            version = version.split(',')[0]

            # Remove comparison signs and only leave version number
            version = re.search(r'\d+.*', version).group()

            break

    return version


def install_repo(repo, editable=False):
    """
    Install a single repo from source located in spyder/external-deps, ignoring
    dependencies, in standard or editable mode.

    Parameters
    ----------
    repo : str
        Must be the distribution name of a repo in spyder/external-deps.
    editable : bool (False)
        Standard install (False) or editable (True). This uses the `-e` flag.

    """
    try:
        repo_path = REPOS[repo]
    except KeyError:
        logger.warning(
            f"Distribution '{repo}' not valid. Must be one of {REPOS.keys()}")
        return

    install_cmd = BASE_COMMAND.copy()

    # PyLSP requires pretend version
    env = None
    if repo == 'python-lsp-server':
        env = {**os.environ}
        env.update({'SETUPTOOLS_SCM_PRETEND_VERSION': get_python_lsp_version()})

    msg = f"Installing '{repo}' from source in {{}} mode."
    if editable:
        # Add edit flag to install command
        install_cmd.append('-e')
        msg = msg.format('editable')
    else:
        msg = msg.format('standard')

    logger.info(msg)
    install_cmd.append(repo_path.as_posix())
    check_output(install_cmd, env=env)

    return


def main(install=tuple(REPOS.keys()), **kwargs):
    """
    Install all subrepos from source.

    Parameters
    ----------
    install : iterable (all repos in spyder/external-deps)
        Distribution names of repos to be installed from spyder/external-deps.
    **kwargs :
        Keyword arguments passed to `install_repo`.

    """
    for repo in install:
        install_repo(repo, **kwargs)


if __name__ == '__main__':
    # ---- Parse command line

    parser = argparse.ArgumentParser(
        usage="python install_subrepos.py [options]")
    parser.add_argument(
        '--install', dest='install', nargs='+',
        default=REPOS.keys(),
        help="Space-separated list of distribution names to install, e.g. "
             "spyder spyder-kernels. If option not provided, then all of the "
             "repos in spyder/external-deps are installed"
    )
    parser.add_argument(
        '--editable', dest='editable',
        action='store_true', default=False,
        help="Install in editable mode."
    )

    args = parser.parse_args()

    # ---- Install repos locally
    main(**vars(args))
