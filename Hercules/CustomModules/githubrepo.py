import git
import hashlib
import logging
import os
import random
import re
import subprocess
import sys
import time
from github import Github
from pathlib import Path
from uuid import uuid4



if sys.version_info < (3, 7):
    raise RuntimeError("Python 3.7 or higher is required to run this script.")



class GitHubRepo:
    def __init__ (self, temp_folder: Path, logger: logging.Logger = None, github_pat: str = None):
        self._logger = (logger or logging.getLogger("null")).getChild(__name__)
        self._logger.addHandler(logging.NullHandler()) if logger is None else None

        self._temp_folder = temp_folder
        if not os.path.exists(self._temp_folder):
            os.makedirs(self._temp_folder)

        self.github_instance = Github(github_pat)

        self._logger.info(f"Module {__name__} has been set up.")



    def isVallidPAT(self, pat: str) -> bool:
        """Check if the provided GitHub Personal Access Token (PAT) is valid.
        Args:
            pat (str): The GitHub Personal Access Token.
        Returns:
            bool: True if the PAT is valid, False otherwise.
        """
        try:
            self.github_instance.get_user().login
            return True
        except Exception as e:
            self._logger.error(f"Invalid PAT: {e}")
            return False



    def isVallidRepo(self, repo_url: str, branch: str = None) -> bool:
        """Check if the given repository URL is valid and accessible.
        Args:
            repo_url (str): The URL of the GitHub repository.
            branch (str, optional): The branch to check. Defaults to None.
        Returns:
            bool: True if the repository is valid, False otherwise.
        """
        try:
            if not branch:
                subprocess.run(["git", "ls-remote", repo_url], check=True)
            else:
                subprocess.run(["git", "ls-remote", repo_url, "-b", branch], check=True)
            return True
        except subprocess.CalledProcessError as e:
            self._logger.error(f"Error checking repository: {e}")
            return False



    def fork_repository(self, github_instance, repo_url, org_name) -> str:
        repo_url = self.extractRepoFullName(repo_url)
        custom_name = self.create_random_hash()

        try:
            repo = github_instance.get_repo(repo_url)
            fork = repo.create_fork(org_name)
            
            org = github_instance.get_organization(org_name)
            forked_repo = org.get_repo(fork.name)
            forked_repo.edit(name=custom_name)
            
            return True
        except Exception as e:
            self._logger.error(f"Error forking repository: {e}")
            return False



    def clone_repo(self, repo_url: str, branch: str = None):
        if not self.isVallidRepo(repo_url, branch):
            raise ValueError("Invalid repository URL or branch")

        if not branch:
            subprocess.run(["git", "clone", repo_url, os.path.join(str(self._temp_folder), str(uuid4()))])
        else:
            subprocess.run(["git", "clone", repo_url, "-b", branch, os.path.join(str(self._temp_folder), str(uuid4()))])



    def extractRepoFullName(self, repo_input: str):
        repo_input = repo_input.strip()
        if repo_input.endswith('.git'):
            repo_input = repo_input[:-4]
        
        regex = r"(?:https?://(?:www\.)?github\.com/)?([^/]+)/([^/]+)"
        match = re.search(regex, repo_input)
        if match:
            owner, repo = match.groups()
            return f"{owner}/{repo}"
        else:
            raise ValueError("Invalid repository URL format")



    def create_random_hash(self) -> str:
        parts = [
            str(time.time_ns()),
            str(uuid4()),
            str(random.randint(0, 1_000_000))
        ]
        random.shuffle(parts)
        combined = ''.join(parts)

        unique_id = hashlib.sha512(combined.encode()).hexdigest()
        return unique_id[:100]
    


















if __name__ == '__main__':
    github_pat = ""
    org_name = "HerculesObfuscatorBot"
    GitHubRepo = GitHubRepo(temp_folder='./Hercules-Bot/Buffer', github_pat=github_pat)
    GitHubRepo.fork_repository(github_instance=GitHubRepo.github_instance, repo_url="https://github.com/zeusssz/hercules-obfuscator", org_name=org_name)
    # GitHubRepo.clone_repo(repo_url="https://github.com/zeusssz/hercules-obfuscator", branch="beta-testin")
else:
    __name__ = "GitHubRepo"