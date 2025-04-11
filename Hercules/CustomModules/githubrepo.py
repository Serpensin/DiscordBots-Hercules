import gc
import git
import hashlib
import logging
import os
import pathlib
import random
import re
import shutil
import subprocess
import sys
import time
from github import Github
from pathlib import Path
from uuid import uuid4



if sys.version_info < (3, 7):
    raise ImportError("Python 3.7 or higher is required to run this script.")



class GitHubRepo:
    def __init__ (self, temp_folder: Path, github_pat: str, org_name: str, logger: logging.Logger = None):
        self.logger = (logger or logging.getLogger("null")).getChild(__name__)
        self.logger.addHandler(logging.NullHandler()) if logger is None else None

        self.org_name = org_name
        self.temp_folder = temp_folder
        if not os.path.exists(self.temp_folder):
            os.makedirs(self.temp_folder)

        self.github_instance = Github(github_pat)
        if not self._isVallidPAT():
            raise ValueError("Invalid GitHub Personal Access Token (PAT) or insufficient permissions to access the organization.")

        self.logger.info(f"Module {__name__} has been set up.")




    def get_lua_files(self, repo_url) -> list:
        if not self._isVallidRepo(repo_url):
            raise ValueError("Invalid repository URL provided.")

        fork = self._fork_repository(repo_url=repo_url)

        local_repo_path = self._clone_repo(repo=fork)

        lua_files = []
        for root, _, files in os.walk(local_repo_path):
            for file in files:
                if file.endswith(".lua"):
                    lua_files.append(os.path.join(root, file))

        return lua_files



    def bar(self, local_repo_path):
        repo = git.Repo(local_repo_path)
        repo.git.add(all=True)
        if repo.index.diff("HEAD") or repo.untracked_files:
            repo.index.commit("Automated commit: Obfuscated .lua files")
            origin = repo.remote(name='origin')
            try:
                origin.push()
            except git.exc.GitCommandError as e:
                raise git.exc.GitCommandError(f"Failed to push changes: {e}")
        else:
            self.logger.info("No changes to commit.")
        self.logger.info("Cleaning up temporary files...")
        repo.close()
        del repo
        gc.collect()
        self._unlock_git_folder(local_repo_path)
        shutil.rmtree(local_repo_path)



    def _isVallidPAT(self) -> bool:
        try:
            self.github_instance.get_user().login
            org = self.github_instance.get_organization(self.org_name)
            org.get_teams()
            return True
        except Exception as e:
            self.logger.error(f"Invalid PAT: {e}")
            return False




    def _isVallidRepo(self, repo_url: str, branch: str = None) -> bool:
        try:
            if not branch:
                subprocess.run(["git", "ls-remote", repo_url], check=True)
            else:
                subprocess.run(["git", "ls-remote", repo_url, "-b", branch], check=True)
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error checking repository: {e}")
            return False



    def _fork_repository(self, repo_url):
        repo_url = self._extractRepoName(repo_url, True)
        custom_name = self._create_random_hash()

        try:
            repo = self.github_instance.get_repo(repo_url)
            fork = repo.create_fork(self.org_name)
            
            org = self.github_instance.get_organization(self.org_name)
            forked_repo = org.get_repo(fork.name)
            forked_repo.edit(name=custom_name)
            
            return forked_repo
        except Exception as e:
            self.logger.error(f"Error forking repository: {e}")
            return None



    def _clone_repo(self, repo):
        if not self._isVallidRepo(repo.clone_url):
            raise ValueError("Invalid repository URL")

        repo_name = self._extractRepoName(repo.clone_url, False)
        repo_path = os.path.join(self.temp_folder, repo_name)

        repo = git.Repo.clone_from(repo.clone_url, repo_path)
        if repo.bare:
            raise ValueError("Cloning failed, repository is bare")
        self.logger.info(f"Cloned repository to {repo_path}")
        return repo_path



    def _extractRepoName(self, repo_input: str, full_name: bool):
        repo_input = repo_input.strip()
        if repo_input.endswith('.git'):
            repo_input = repo_input[:-4]
        
        if full_name:
            regex = r"(?:https?://(?:www\.)?github\.com/)?([^/]+)/([^/]+)"
            match = re.search(regex, repo_input)
            if match:
                owner, repo = match.groups()
                return f"{owner}/{repo}"
            else:
                raise ValueError("Invalid repository URL format")
        else:
            parts = repo_input.split('/')
            if len(parts) < 2:
                raise ValueError("Invalid repository URL format")
            return parts[-1]



    def _create_random_hash(self) -> str:
        parts = [
            str(time.time_ns()),
            str(uuid4()),
            str(random.randint(0, 1_000_000))
        ]
        random.shuffle(parts)
        combined = ''.join(parts)

        unique_id = hashlib.sha512(combined.encode()).hexdigest()
        return unique_id[:100]
    



       
    def _unlock_git_folder(self, repo_path):
        git_dir = pathlib.Path(repo_path) / '.git'
        if git_dir.exists():
            for root, dirs, files in os.walk(git_dir):
                for name in files:
                    try:
                        os.chmod(os.path.join(root, name), 0o777)
                    except Exception:
                        pass
    
    
    











if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()
    github_pat = os.getenv("GITHUB_PAT")
    org_name = "HerculesObfuscatorBot"
    GitHubRepo = GitHubRepo(temp_folder='./Hercules-Bot/Buffer', github_pat=github_pat, org_name=org_name)
    print(GitHubRepo.get_lua_files(repo_url="https://github.com/Serpensin/hercules-obfuscator"))
else:
    __name__ = "GitHubRepo"