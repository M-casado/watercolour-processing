import os

def find_git_root(start_path=None):
    """
    Traverses upward from start_path (or the current file's directory)
    until it finds a .git folder, signifying a Git repository root.
    Returns the absolute path to that repository root,
    or None if not found.
    """
    if start_path is None:
        # Default: directory of this file
        start_path = os.path.abspath(os.path.dirname(__file__))

    current_dir = start_path
    while True:
        if os.path.isdir(os.path.join(current_dir, ".git")):
            return current_dir
        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:
            # we've reached the filesystem root, no .git found
            return None
        current_dir = parent_dir

def get_repo_root():
    """
    Wrapper to ensure we handle 'None' gracefully or raise an error if .git isn't found.
    """
    root = find_git_root()
    if not root:
        raise RuntimeError("Unable to find .git folder! Run the code from within the watercolour Git repo!")
    return root

def get_db_path():
    """
    Returns an absolute path to 'data/watercolours.db' at the repo root.
    """
    repo_root = get_repo_root()
    return os.path.join(repo_root, "data", "watercolours.db")

def get_thumbnails_dir():
    """
    Returns an absolute path to 'data/thumbnails' at the repo root.
    """
    repo_root = get_repo_root()
    thumb_dir = os.path.join(repo_root, "data", "thumbnails")
    return thumb_dir

def get_db_schema_path():
    """
    Returns an absolute path to 'src/watercolour_processing/database/db_schema.sql' at the repo root.
    """
    repo_root = get_repo_root()
    return os.path.join(repo_root, "src", "watercolour_processing", "database", "db_schema.sql")

def get_data_raw_path():
    """
    Returns an absolute path to 'data/raw' at the repo root.
    """
    repo_root = get_repo_root()
    return os.path.join(repo_root, "data", "raw")