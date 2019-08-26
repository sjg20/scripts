#! /usr/bin/python

# Simple script to list commits for an author across all repos

from datetime import datetime
import fnmatch
import operator
import os
import re
import subprocess

# Where is your '.repo' directory?
base = '/home/sjg/cosarm'

# Which author do you want to search for?
author = 'sjg'

# Set this to None if you want to scan all repos
dirs = ['src/scripts.git',
    'src/platform/crash-reporter.git',
    'src/third_party/atheros.git',
    'src/overlays.git',
    'chromite.git',
    'src/third_party/u-boot/files.git',
    'src/third_party/autotest/files.git',
    'src/platform/u-boot-config.git',
    'src/platform/power_manager.git',
    'src/platform/login_manager.git',
    'src/third_party/chromiumos-overlay.git',
    'src/third_party/kernel/files.git',
    'src/platform/dev.git'
    ]
dirs = None

#Specify a start date, or None for all commits
start = datetime(2012, 2, 1)
#start = None



def locate(pattern, root=os.curdir):
    '''Locate all dirs matching supplied filename pattern in and below
    supplied root directory.

    # Modified from from Simon Brunning
    # http://code.activestate.com/recipes/
    #           499305-locating-files-throughout-a-directory-tree/
    '''
    for path, dirs, files in os.walk(os.path.abspath(root)):
        for dirname in fnmatch.filter(dirs, pattern):
            yield os.path.join(path, dirname)


def get_stat(reponame, commit):
    args = ['git']
    args += ['--git-dir', reponame]
    args += ['show', '--numstat', commit['hash']]
    pipe = subprocess.Popen(args, stdout=subprocess.PIPE)
    stdout = pipe.communicate()[0]
    if not stdout:
        print 'Cannot find commit? - how odd...'
        sys.exit(1)

    commit['stat'] = stdout
    re_review = re.compile(' *(Reviewed-on|Review URL): (.*)')
    re_lines = re.compile('(\d+)\s+(\d+)\s+(\S*)')
    re_date = re.compile('Date:\s*\S+ (\S+ \S+ \S+ \S+)')
    commit['review'] = None
    files = {}
    for line in stdout.splitlines():
        m = re_review.match(line)
        if m:
            commit['review'] = m.group(2)
        m = re_lines.match(line)
        if m:
            files[m.group(3)] = [int(m.group(1)), int(m.group(2))]
        m = re_date.match(line)
        if m:
            commit['date'] = datetime.strptime(m.group(1), '%b %d %H:%M:%S %Y')

    commit['files'] = files

    plus = 0
    minus = 0
    for stats in files.itervalues():
        plus += stats[0]
        minus += stats[1]
    commit['plus'] = plus
    commit['minus'] = minus

def list_commits(base, author, dirs=None, start_date=None):
    projects = os.path.join(base, '.repo', 'projects')

    re_commit = re.compile('(\w+) (.*)')
    repo_info = {}
    if dirs:
        dirs = [os.path.join(projects, name) for name in dirs]
    else:
        dirs = locate('*.git', projects)
    for reponame in dirs:
        name = os.path.splitext(os.path.basename(reponame))[0]
        if name == 'files':
            name = os.path.basename(os.path.dirname(reponame))
        if name in ['u-boot-v1', 'u-boot-next', 'kernel-next']:
            continue

        args = ['git']
        args += ['--git-dir', reponame]
        branch = 'm/master'
        if name in ['u-boot']:
          branch = 'cros/chromeos-v2011.12'

        args += ['log', '--oneline', '--author', author, branch]
        pipe = subprocess.Popen(args, stdout=subprocess.PIPE)
        stdout = pipe.communicate()[0]
        if stdout:
            commits = {}
            plus = minus = 0
            for line in stdout.splitlines():
                m = re_commit.match(line)
                commit = {
                    'hash' : m.group(1),
                    'title' : m.group(2)
                }

                get_stat(reponame, commit)
                plus += commit['plus']
                minus += commit['minus']
                date = commit['date']
                if not start_date or date > start_date:
                    commits[m.group(1)] = commit

            if commits:
                repo_info[name] = {
                    'name' : name,
                    'path' : reponame,
                    'commits' : commits,
                    'plus': plus,
                    'minus' : minus
                }
    return repo_info


def colour(col, str):
    return '<font color="%s">%s</font>' % (col, str)


repo_info = list_commits(base, author, dirs, start)
plus = minus = 0
print '<h1>Rough Summary for %s</h1>' % author

repo_list = repo_info.values()
repo_list = sorted(repo_list, key=operator.itemgetter('plus'), reverse=True)

for repo in repo_list:
    print '<h2>%s</h2>' % repo['name']
    commits = len(repo['commits'])
    print '<p>%d commit%s: %+d lines added, %d lines deleted</p>' % (
            commits, 's' if commits > 1 else '', repo['plus'], repo['minus'])
    print '<table border="1" cellspace="2">'
    cols = ['Add', 'Remove', 'Files', 'Date', 'Code review']
    print '<th>%s</th>' % '</th><th>'.join(cols)
    list = repo['commits'].values()
    for commit in sorted(list, key=operator.itemgetter('date')):
        print '<tr>'
        #print commit
        review = commit['review']
        if review:
            title = '<a href="%s">%s</a>' % (review, commit['title'])
        else:
            title = commit['title']
        cols = [colour('green', str(commit['plus'])),
                colour('red', str(-commit['minus'])),
                str(len(commit['files'])),
                commit['date'].strftime('%d-%b-%Y'), title]
        start = '<td align="right">'
        print '%s%s</td>' % (start, ('</td>' + start).join(cols[:-1]))
        print '<td>%s</td>' % cols[-1]
        #print '%+4d %4d: %s: %s' %
        print '</tr>'
    print '</table>'
    plus += repo['plus']
    minus += repo['minus']
    print
    print
print '<p>Total Lines: %+4d: %d</p>' % (plus, -minus)
