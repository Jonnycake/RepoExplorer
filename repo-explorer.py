#!/usr/bin/python3
import argparse
import configparser
import difflib
import pathlib
import json
import sys
import git

class Analyzer:
    repo_dir = "."
    config = None
    data = {}
    differ = None
    def __init__(self, path="."):
        self.repo_dir = path
        self.differ = difflib.Differ()

    def loadConfigs(self, path):
        config = configparser.ConfigParser()
        config.read(path)
        self.config = config

    def collectData(self, from_cache=False):
        """
            Collect list of commits and list of files
            For each commit - identify "author", "files changed", "date", and
              "impact" (based on changeset)
            For each file - identify file type and the current content
        """
        data = {}
        cache_path = pathlib.Path("%s/%s" % (self.repo_dir, self.config.get('Caching', 'cache_file')))
        if from_cache and cache_path.is_file():
            try:
                with open(cache_file, "r") as f:
                    data = json.load(f)
            except:
                print(sys.exc_info()[0])
        else:
            data = self.loadLiveData()

        self.data = data

    def getDiffStats(self, commit):
        files = {}
        for change in commit.diff():
            files[change.b_path] = {"add": 0, "del": 0, "type": "A"}
            files[change.b_path]['type'] = change.change_type
            try:
                orig = change.a_blob.data_stream.read().decode('utf-8').splitlines(1)
                new = change.b_blob.data_stream.read().decode('utf-8').splitlines(1)
                for diff in list(self.differ.compare(orig, new)):
                    if diff.startswith('+'):
                        files[change.b_path]['add'] += 1
                    elif diff.startswith('-'):
                        files[change.b_path]['del'] += 1
            except:
                pass
        return files

    def loadLiveData(self):
        repo = git.Repo(self.repo_dir)

        data = {"authors": {}, "commits": {}, "files": {}}
        commits = {}
        for commit in repo.iter_commits():
            tmp_commit_data = {
                "author": commit.author,
                "files": {},
                "date": "unknown"
            }
            tmp_commit_data['files'] = self.getDiffStats(commit)
            commits[str(commit)] = tmp_commit_data

        data['commits'] = commits

        return data

    def doAnalysis(self):
        print(self.data)

    def output(self):
        pass

    def aggregateBasicInfo(self):
        """
            Total number of commits
            First commit date & Author
            Last commit date & Author
        """
        pass

analyzer = Analyzer()
analyzer.loadConfigs("conf/repo-explorer.ini")
analyzer.collectData()
analyzer.doAnalysis()
