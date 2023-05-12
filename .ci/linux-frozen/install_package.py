#!/usr/bin/python

import sys
import re
import subprocess
from launchpadlib.launchpad import Launchpad

if sys.version_info[0] > 2:
    xrange = range

cachedir = '/.launchpadlib/cache/'
launchpad = Launchpad.login_anonymously(
    'grab build info', 'production', cachedir, version='devel')

processed_packages = []
deb_file_list = []


def get_url(pkg, distro):
    build_ref = (
        launchpad.archives.getByReference(reference='ubuntu')
        .getPublishedBinaries(
            binary_name=pkg[0],
            distro_arch_series=f'https://api.launchpad.net/devel/ubuntu/{distro}/amd64',
            version=pkg[1],
            exact_match=True,
            order_by_date=True,
        )
        .entries[0]
    )
    build_link = build_ref['build_link']
    deb_name = f"{pkg[0]}_{pkg[1]}_{'amd64' if build_ref['architecture_specific'] else 'all'}.deb"
    deb_link = f'{build_link}/+files/{deb_name}'
    return [deb_link, deb_name]


def list_dependencies(deb_file):
    t = subprocess.check_output(
        [
            'bash',
            '-c',
            f'(dpkg -I {deb_file} | grep -oP "^ Depends\: \K.*$") || true',
        ]
    )
    deps = [i.strip() for i in t.split(',')]
    equals_re = re.compile(r'^(.*) \(= (.*)\)$')
    return [equals_re.sub(r'\1=\2', i).split('=') for i in filter(equals_re.match, deps)]


def get_package(pkg, distro):
    if pkg in processed_packages:
        return
    print(f'Getting {pkg[0]}...')
    url = get_url(pkg, distro)
    subprocess.check_call(['wget', '--quiet', url[0], '-O', url[1]])
    for dep in list_dependencies(url[1]):
        get_package(dep, distro)
    processed_packages.append(pkg)
    deb_file_list.append(f'./{url[1]}')


for i in xrange(1, len(sys.argv), 3):
    get_package([sys.argv[i], sys.argv[i + 1]], sys.argv[i + 2])

subprocess.check_call(
    ['apt-get', 'install', '-y', '--force-yes'] + deb_file_list)
