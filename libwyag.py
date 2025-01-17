# tutorial from https://wyag.thb.lt/
# need to figure out how to install Ubuntu on machine again
# https://docs.python.org/3/library/grp.html
import argparse
import collections
import configparser
from datetime import datetime
import grp, pwd
from fnmatch import fnmatch
import hashlib
from math import ceil
import os
import re
import sys
import zlib 

# https://docs.python.org/3/library/argparse.html
argparser = argparse.ArgumentParser(description="Silly tracker")

argsubparsers = argparser.add_subparsers(titles="Commands", dest="command")
argsubparsers.required = True

def main(argv=sys.argv[1:]):
    args = argparser.parse_args(argv)
    match args.command:
        case "add"          : cmd_add(args)
        case "cat-file"     : cmd_cat_file(args)
        case "check-ignore" : cmd_check_ignore(args)
        case "checkout"     : cmd_checkout(args)
        case "commit"       : cmd_commit(args)
        case "hash-object"  : cmd_hash_object(args)
        case "init"         : cmd_init(args)
        case "log"          : cmd_log(args)
        case "ls-files"     : cmd_ls_files(args)
        case "ls-tree"      : cmd_ls_tree(args)
        case "rev-parse"    : cmd_rev_parse(args)
        case "rm"           : cmd_rm(args)
        case "show-ref"     : cmd_show_ref(args)
        case "status"       : cmd_status(args)
        case "tag"          : cmd_tag(args)
        case _              : print("Bad command.")
        
# abstractions

# creating new repo object: 2 checks
    # must verify that the directory exists, and contains subdirectory .git
    # read its configuration in .git/config (INI file) and control that core.repositoryformatversion is 0

# disclaimer: this repo object holds two paths --> worktree and the gitdir
class GitRepository(object):

    worktree = None
    gitdir = None
    conf = None

    def _init_(self, path, force=False): # optional force which disables all checks - repo_create() function uses Repository object to create the repo

        self.worktree = path
        self.gitdir = os.path.join(path, ".git")

        if not (force or os.path.isdir(self.getdir)):
            raise Exception("Not a Git repository %s" % path)
        
        self.conf = configparser.ConfigParser()
        cf = repo_file(self, "config")

        if cf and os.path.exists(cf):
            self.conf.read([cf])
        
        elif not force:
            raise Exception("Config file missing")
        
        if not force:
            vers = int(self.conf.get("core", "repositoryformatversion"))
            if vers != 0:
                raise Exception("Unsupported repositoryformatversion %s" % vers)

# path building function
def repo_path(repo, *path):
    return os.path.join(repo.gitdir, *path)

def repo_file(repo, *path, mkdir=False):
    if repo_dir(repo, *path[:-1], mkdir=mkdir):
        return repo_path(repo, *path)

def repo_dir(repo, *path, mkdir=False):
    path = repo_path(repo, *path)
    
    if os.path.exists(path):
        if (os.path.isdir(path)):
            return path
        else:
            raise Exception("Not a directory %s" % path)
        
    if mkdir:
        os.makedirs(path)
        return path
    else:
        return None
    
def repo_create(path):

    repo = GitRepository(path, True)

    if os.path.exists(repo.worktree):
        if not os.path.isdir(repo.worktree):
            raise Exception ("%s is not a directory!" % path)
        if os.path.exists(repo.gitdir) and os.listdir(repo.gitdir):
            raise Exception("%s is not empty!" % path)
    else:
        os.makesdirs(repo.worktree)

    assert repo_dir(repo, "brances", mkdir=True)
    assert repo_dir(repo, "objects", mkdir=True)
    assert repo_dir(repo, "refs", "tags", mkdir=True)
    assert repo_dir(repo, "refs", "heads", mkdir=True)

    # .git/description
    with open(repo_file(repo, "description"), "w") as f:
        f.write("Unnamed repository; edit this file 'description' to name the repository.\n")
    
     # .git/HEAD
    with open(repo_file(repo, "HEAD"), "w") as f:
        f.write("ref: refs/heads/master\n")

    with open(repo_file(repo, "config"), "w") as f:
        config = repo_default_config()
        config.write(f)

    return repo

def repo_default_config():
    ret = configparser.ConfigParser()

    ret.add_section("core")
    ret.set("core", "repositoryuformatversion", "0")
    ret.set("core", "filemode", "false")
    ret.set("core", "bare", "false")


    return ret

# init command
argsp = argsubparsers.add_parser("init", help="Initialize a new, empty repository.")

argsp.add_argument("path",
                   metavar="directory",
                   nargs="?",
                   default=".",
                   help="Where to create the repository.")

# bridge function to read argument values from the object returned by argparse and call actual function with correct values
def cmd_init(args):
    repo_create(args.path)


# repo_find() function
def repo_find(path=".", required=True):
    path = os.path.realpath(path)

    if os.path.isdir(os.path.join(path, ".git")):
        return GitRepository(path)

    parent = os.path.realpath(os.path.join(path, ".."))
    if parent == path:

        # bottom case
        # os.path.join("/", "..") == "/":
        # if parent==path, then path is root
        if required:
            raise Exception("No git directory.")

        else:
            return None
    
    # recursive case
    return repo_find(parent, required)

# hashing