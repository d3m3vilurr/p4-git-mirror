import os
import sys
import re
from datetime import datetime
from P4 import P4
from git import Git, Repo
from git.exc import GitCommandError
from tzlocal import get_localzone

import config as CONFIG

p4 = P4()
p4.port = CONFIG.P4_PORT
p4.user = CONFIG.P4_USER
p4.password = CONFIG.P4_PASSWD
p4.connect()
p4.run_login()
raw_users = p4.run_users()
users = {}
for user in raw_users:
    users[user['User']] = '%s <%s>' % (user['FullName'], user['Email'])
localzone = get_localzone()

def p4_download(repo, depot_path, change_no):
    for info in p4.run('files', depot_path + '/...@' + change_no):
        if 'text' in info['type'] or 'unicode' in info['type']:
            mode = 'w'
        else:
            mode = 'wb'
        if 'delete' in info['action']:
            continue
        depot_file = info['depotFile'][len(depot_path):]
        fn = 'mirrors/' + repo + depot_file
        dirn = os.path.split(fn)[0]
        if not os.path.exists(dirn):
            os.makedirs(dirn)
        data = p4.run('print', '%s#%s' % (info['depotFile'], info['rev']))
        with open(fn, mode) as f:
            f.write(''.join(data[1:]))
    pass

def fetch_last_changes(git):
    try:
        return int(re.match('.*: change = (\d+)\]',
                            git.log('-n', 1).split('\n')[-1]).group(1))
    except GitCommandError:
        return -1

def sync_to_git(git, repo, branch):
    git_branches = map(lambda x: x.lstrip(' *').strip(),
                       git.branch().split('\n'))
    git_remote_branches = map(lambda x: x.strip(),
                              git.branch('--remotes').split('\n'))
    if branch not in git_branches:
        remote_branches = \
                filter(lambda remote_br: branch == remote_br.split('/', 1)[-1],
                       git_remote_branches)
        if not remote_branches:
            git.checkout('-f', '--orphan', branch)
        else:
            git.checkout('-f', remote_branches, '-b', branch)
    else:
        git.checkout('-f', branch)
    start = fetch_last_changes(git) + 1
    depot_path = '%s/%s/%s' % (CONFIG.DEPOT_PREFIX, branch, repo)
    changes = p4.run('changes', ('%s/...@%d,@now' % (depot_path, start)))
    if not changes:
        return
    sys.stdout.flush()
    for idx, change in enumerate(reversed(changes)):
        try:
            # all clear repo
            git.rm('-rfq', '.')
            git.clean('-fdx')
        except GitCommandError:
            pass
        print ('\rsync %s ... %s' % (depot_path, change['change'])),
        sys.stdout.flush()
        raw_change = p4.run('change', '-o', change['change'])
        p4_download(repo, depot_path, change['change'])
        #print raw_change
        msg = raw_change[0]['Description'] + '\n\n' + \
            ('[git-p4: depot-paths = "%s": change = %s]' % (depot_path,
                                                            change['change']))
        date = localzone \
                .localize(datetime.strptime(raw_change[0]['Date'],
                                            '%Y/%m/%d %H:%M:%S'),
                          is_dst=None) \
                .isoformat()
        git.add('-A')
        git.commit('--date=' + date, '--author=' + users[raw_change[0]['User']],
                   '--allow-empty', '-m', msg)
    print

def sync_repo(repo, push_remotes=None):

    def _extract_branch(name):
        if CONFIG.DEPOT_PREFIX not in name:
            return
        return name.split(CONFIG.DEPOT_PREFIX + '/')[1]

    # fetch branches
    main_branches =  map(lambda x: _extract_branch(x['Stream']),
                        p4.run('streams', '-F', 'Type=mainline'))
    dev_branches =  map(lambda x: _extract_branch(x['Stream']),
                        p4.run('streams', '-F', 'Type=development'))
    rel_branches =  map(lambda x: _extract_branch(x['Stream']),
                        p4.run('streams', '-F', 'Type=release'))
    branches = main_branches + dev_branches + rel_branches
    branches = filter(lambda x: x, branches)

    # create repo
    repo_path = 'mirrors/' + repo
    if not os.path.exists(repo_path):
        os.makedirs(repo_path)
    git = Git(repo_path)
    git.init()

    for branch in branches:
        sync_to_git(git, repo, branch)

    # automatic push to remote
    if not push_remotes:
        return

    remotes = filter(lambda x: x, git.remote().split())
    for remote in remotes:
        if remote not in push_remotes:
            continue
        git.push(remote, '--all')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print 'Using: %s <repo>' % sys.argv[0]
        sys.exit(1)

    import argparse

    parser = argparse.ArgumentParser(description='perforce-git-mirror')
    parser.add_argument('--remotes', type=str, nargs='*',
                        help='automatic push to remote servers')
    parser.add_argument('repo', type=str, nargs='+',
                        help='target repositories')
    args = parser.parse_args()
    for repo in args.repo:
        sync_repo(repo, args.remotes)
