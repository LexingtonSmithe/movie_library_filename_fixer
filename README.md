# Movie Library Filename Fixer

A Python tool to normalize and rename movie files in your library using TMDB metadata.  
Supports **recursive folder traversal**, **in-place renaming**, **dry runs**, and skipping unwanted folders/files.

---

## Features

- **Recursive file processing**: Walks through all subfolders of a given directory.
- **In-place renaming**: Renames files without moving them, preserving folder structure.
- **Dry run mode**: Preview changes without touching your files.
- **TMDB integration**: Uses The Movie Database API to fetch official titles and release years.
- **Skip rules**:
  - Folders like `Extras`, `Featurette`, `Deleted Scenes`, etc., are skipped recursively.
  - Non-video files or files with ignored keywords like `sample` or `trailer`.
  - Already normalized filenames are skipped.
- **Detailed logging**: Logs all actions, skipped files, and summary to `movie_rename.log`.
- **Supports common video formats**: `.mp4`, `.mkv`, `.avi`, `.mov`, `.wmv`, `.flv`, `.webm`, `.m4v`.

---

# 📦 Requirements

* Python 3.9+
* A free TMDB API key

Python dependencies:

```
pip install -r requirements.txt
```

---

#  Getting a TMDB API Key

1. Create an account at https://www.themoviedb.org
2. Go to **Settings → API**
3. Request an API key 
4. Copy the key (not Read Only)

---

# ⚙️ Setup
## Create your environment file:

```
cp .env.example .env
```

Edit `.env` and add your API key:

--- 

# Usage

## Dry run (recommended)

Logs what will change without renaming anything:

```python movie_rename.py /path/to/movies```

See movie_rename.log once run for a breakdown of the run 


## Apply changes

Actually rename the files:

``` python movie_rename.py /path/to/movies --apply ```

See movie_rename.log once run for a breakdown of the run 
---

#  Notes

* Always run the script in **dry-run mode first**
* If a movie cannot be matched it will be skipped
* Conflicting filenames will not be overwritten

---
