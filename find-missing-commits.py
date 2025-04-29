#!/usr/bin/env python3
import sys
import os
from typing import List, Set

import pygit2

def find_commits_touching_path(repo: pygit2.Repository, commit_list: List[pygit2.Commit], directory_path: str) -> List[pygit2.Commit]:
    """
    Filters a list of commits to find those that modify files within a specified directory.

    Args:
        repo: The Git repository.
        commit_list: A list of pygit2.Commit objects to filter.
        directory_path: The path within the repository to check (e.g., 'src/').

    Returns:
        A list of pygit2.Commit objects that modified files in the given directory.
    """
    matching_commits = []
    for commit in commit_list:
        try:
            # Get the diff between this commit and its first parent
            parent = commit.parents[0] if commit.parents else None
            if parent:
                diff = repo.diff(parent, commit)
            else:
                # If it's the initial commit, diff against an empty tree
                tree = repo.TreeBuilder().write()
                diff = repo.diff(None, commit.tree)

            for delta in diff.deltas:
                # Check if the file path starts with the directory path
                if delta.new_file.path.startswith(directory_path) or delta.old_file.path.startswith(directory_path):
                    matching_commits.append(commit)
                    break  # No need to check other deltas in this commit
        except Exception as e:
            print(f"Error diffing commit {commit.hex}: {e}")
            continue  # Skip to the next commit

    return matching_commits


def find_missing_commits(repo_path, source_branch_name, target_branch_name, directory_path=None, exclude_matching_subjects=False):
    """
    Finds commits in the source branch that are not present in the target branch,
    optionally filtered by a directory path, and optionally excluding commits
    whose subject lines match those in the target branch.

    Args:
        repo_path (str): Path to the Git repository.
        source_branch_name (str): Name of the branch to check for missing commits (e.g., 'feature-branch').
        target_branch_name (str): Name of the branch to compare against (e.g., 'main').
        directory_path (str, optional): Path within the repository to filter commits by.
            If specified, only commits that modify files in this directory are considered.
            Defaults to None (all commits).
        exclude_matching_subjects (bool, optional): If True, exclude commits from the
            result if their subject lines (first line of commit message) match any
            commit's subject line in the target branch. Defaults to False.

    Returns:
        list: A list of pygit2.Commit objects that are in source_branch but not in target_branch.
              Returns an empty list if no missing commits are found or if an error occurs.
    """
    try:
        import pygit2
    except ImportError:
        print("Error: pygit2 is not installed. Please install it using 'pip install pygit2'.")
        return []

    try:
        repo = pygit2.Repository(repo_path)
    except pygit2.GitError as e:
        print(f"Error: Invalid Git repository path: {repo_path} - {e}")
        return []

    try:
        source_branch = repo.branches.get(source_branch_name)
        if not source_branch:
            print(f"Error: Source branch '{source_branch_name}' not found.")
            return []

        target_branch = repo.branches.get(target_branch_name)
        if not target_branch:
            print(f"Error: Target branch '{target_branch_name}' not found.")
            return []
    except KeyError:
        print("Error: Branch not found")
        return []

    # Use revwalk to get the commits in source_branch
    source_commits = []
    try:
        for commit in repo.walk(source_branch.target, pygit2.GIT_SORT_TOPOLOGICAL):
            source_commits.append(commit)
    except pygit2.GitError as e:
        print(f"Error walking source branch: {e}")
        return []

    # Use revwalk to get the commits in target_branch
    target_commits_set = set()
    target_subjects = set()
    try:
        for commit in repo.walk(target_branch.target, pygit2.GIT_SORT_TOPOLOGICAL):
            if commit.message:  # Add this check
                target_subjects.add(commit.message.splitlines()[0])
            else:
                target_subjects.add("") #add empty string to set
            target_commits_set.add(commit.id)
    except pygit2.GitError as e:
        print(f"Error walking target branch: {e}")
        return []

    # Find the commits in source_branch that are not in target_branch
    missing_commits = [commit for commit in source_commits if commit.id not in target_commits_set]

    if directory_path:
        missing_commits = find_commits_touching_path(repo, missing_commits, directory_path)

    if exclude_matching_subjects:
        missing_commits = [commit for commit in missing_commits if commit.message and commit.message.splitlines()[0] not in target_subjects] #added check for commit.message

    # Sort the missing commits by commit time (oldest to newest)
    missing_commits.sort(key=lambda c: c.commit_time, reverse=False)
    return missing_commits


def print_missing_commits(missing_commits):
    """Prints the missing commits in a user-friendly format."""
    if not missing_commits:
        print("No missing commits found.")
        return

    print("Missing commits:")
    for commit in missing_commits:
        short_sha = commit.hex[:10]  # Get the first 10 characters of the SHA
        subject = commit.message.splitlines()[0] if commit.message else "(No Subject)"  # Handle empty commit messages
        print(f"{short_sha:<12} {subject}")  # Use string formatting for aligned output
    print("-" * 80) #added separator

def main():
    """
    Main function to parse arguments and find missing commits.
    """
    import os
    import argparse
    parser = argparse.ArgumentParser(description="Find commits in one branch missing from another, optionally filtered by path and subject.")
    parser.add_argument("repo_path", type=str, help="Path to the Git repository.")
    parser.add_argument("source_branch", type=str, help="Source branch name (e.g., 'feature-branch').")
    parser.add_argument("target_branch", type=str, help="Target branch name (e.g., 'main').")
    parser.add_argument("-p", "--path", type=str, dest="directory_path",
                        help="Optional path within the repository to filter commits by (e.g., 'src/').",
                        default=None)
    parser.add_argument("-x", "--exclude-subject", action='store_true', dest="exclude_matching_subjects",
                        help="Exclude commits whose subject lines match those in the target branch.",
                        default=False)
    args = parser.parse_args()

    repo_path = args.repo_path
    source_branch_name = args.source_branch
    target_branch_name = args.target_branch
    directory_path = args.directory_path
    exclude_matching_subjects = args.exclude_matching_subjects

    if not os.path.exists(repo_path):
        print(f"Error: Repository path '{repo_path}' does not exist.")
        sys.exit(1)

    missing_commits = find_missing_commits(repo_path, source_branch_name, target_branch_name, directory_path, exclude_matching_subjects)
    print_missing_commits(missing_commits)



if __name__ == "__main__":
    main()
