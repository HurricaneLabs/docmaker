import os
import re

import git

from docmaker.hooks import Hook, StopProcessing


class GitRepo:
    @classmethod
    def is_valid_git_repo(cls, path):
        try:
            git.Repo(path)
        except git.exc.InvalidGitRepositoryError:
            return False
        return True

    @Hook("pre_initialize", predicate=(
        lambda ctx: GitRepo.is_valid_git_repo(os.path.dirname(ctx.srcfile)),
    ))
    def check_file_is_dirty(self, ctx):
        repo = git.Repo(os.path.dirname(ctx.srcfile))
        commit = repo.head.commit
        parent = commit.parents[0]

        try:
            commit_hexsha = commit.tree.join(ctx.srcfile).hexsha
        except KeyError:
            # Can't find this file in the current commit?????
            # Play it safe
            return True

        try:
            parent_hexsha = parent.tree.join(ctx.srcfile).hexsha
        except KeyError:
            # Can't find this file in the parent??? It's new.
            return True

        # File changed between parent and current commit
        if commit_hexsha != parent_hexsha:
            return True

        # File is modified and uncommitted
        modified_files = [item.a_path for item in repo.index.diff(None)]
        if os.path.relpath(ctx.srcfile, repo.working_dir) in modified_files:
            return True

        # Option to force a rebuild generally
        if ctx.get_as_boolean("git_repo.force", False):
            return True

        # Option to force a rebuild when running from a manual Gitlab CI run
        if ctx.get_as_boolean("git_repo.force_on_gitlab_ci_web", True):
            if os.environ.get("CI_PIPELINE_SOURCE", "") in ("web",):
                return True

        # Option to force a rebuild based on the git commit message
        if ctx.get("git_repo.force_on_git_commit_message"):
            matchstr = ctx["git_repo.force_on_git_commit_message"]
            if matchstr in commit.message:
                return True

        # Option to compare the parent commit time of ctx.srcfile to timestamps
        if ctx.get("git_repo.timestamps_to_compare"):
            for ts in ctx["git_repo.timestamps_to_compare"]:
                if re.match(r"^\d+$", ts):
                    ts = int(ts)
                elif re.match(r"^\d+\.\d+$", ts):
                    ts = float(ts)

                if parent.committed_date < ts:
                    return True

        # No reason to re-run, as best as we can tell
        print(f"{ctx.srcfile} does not need rebuilt")
        raise StopProcessing
