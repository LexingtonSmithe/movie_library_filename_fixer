import os
import re
import argparse
import requests
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY")  # Put your TMDB API key in a .env file

VALID_FILENAME_PATTERN = re.compile(r'^[^\\/:*?"<>|]+ \(\d{4}\)\.[^\\/:*?"<>|]+$')
VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
RESOLUTIONS = {"480", "576", "720", "1080", "2160"}
IGNORE_WORDS = {"sample", "trailer"}
SKIP_FOLDERS = {"extras", "featurette", "featurettes", "behind the scenes", "deleted scenes"}

class Stats:
    def __init__(self):
        self.logs = []
        self.skipped_files = []
        self.skipped_no_year = []
        self.skipped_no_results = []
        self.user_skipped_files = []
        self.success_count = 0
        self.skipped_count = 0

    def log(self, message):
        self.logs.append(message)

    def skip(self, file):
        self.skipped_files.append(file)
        self.skipped_count += 1

    def success(self):
        self.success_count += 1

class MovieFile:
    def __init__(self, folder, filename):

        self.folder = folder
        self.filename = filename
        self.full_path = os.path.join(folder, filename)

        self.cleaned_name, self.ext = clean_filename(filename)
        self.title, self.year = strip_release_info(self.cleaned_name)

    def target_path(self, new_name):
        return os.path.join(self.folder, sanitize_filename(new_name))
    
def clean_filename(filename):
    name, ext = os.path.splitext(filename)
    cleaned = re.sub(r'[\._]', ' ', name).strip()
    return cleaned, ext

def strip_release_info(name):
    # Replace dots/underscores with spaces
    name = re.sub(r'[._()]', ' ', name)
    parts = name.split()
    title_parts = []
    year = ""
    for part in parts:
        
        if re.fullmatch(r'\d{3,4}p', part.lower()):
            break

        if re.fullmatch(r'\d{4}', part):
            if part in RESOLUTIONS: 
                break

            year = int(part)
            break

        title_parts.append(part)
        title = ' '.join(title_parts).strip()
        
    return title, year
    
def search_tmdb(title):
    url = "https://api.themoviedb.org/3/search/movie"
    params = {"api_key": TMDB_API_KEY, "query": title}
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    return data.get("results", [])

def filter_results_by_year(results, year):
    if year is None:
        return results
    return [r for r in results if r.get("release_date", "").startswith(str(year))]

def prompt_user_for_choice(results, title, year):
    year = year or "?"
    print(f"\nMultiple results found for '{title}'" + (f" ({year})" if year else ""))
    for idx, r in enumerate(results, start=1):
        r_year = r.get("release_date", "????")[:4]
        print(f"{idx}. {r['title']} ({r_year})")
    print("0. Skip this file")

    while True:
        choice = input("Choose a result to accept (number): ").strip()
        if choice.isdigit():
            choice = int(choice)
            if choice == 0:
                return None
            elif 1 <= choice <= len(results):
                return results[choice - 1]
        print("Invalid input, try again.")

def sanitize_filename(name):
    # Replace illegal Windows characters with dash or space
    return re.sub(r'[<>:"/\\|?*]', ' -', name)

def should_skip_file(movie, stats):

    if movie.ext not in VIDEO_EXTENSIONS:
        stats.log(f"Skipping '{movie.filename}': Not a video file")
        stats.skip(movie.filename)
        return True

    if VALID_FILENAME_PATTERN.match(movie.filename):
        stats.log(f"Skipping '{movie.filename}': Already valid filename")
        stats.skip(movie.filename)
        return True

    if any(word in movie.filename.lower() for word in IGNORE_WORDS):
        stats.log(f"Skipping '{movie.filename}': contains ignored keyword")
        stats.skip(movie.filename)
        return True

    return False

def search_movie(movie, stats):

    try:
        stats.log(f"Searching for title: '{movie.title}'")
        results = search_tmdb(movie.title)
        stats.log(f"Found {len(results)} result(s) for title '{movie.title}'")
        return results

    except requests.RequestException as e:
        stats.log(f"TMDB query failed for '{movie.title}': {e}")
        return None

def resolve_movie_match(results, movie, stats):

    if movie.year:
        filtered = filter_results_by_year(results, movie.year)

        if len(filtered) == 1:
            match = filtered[0]
            new_name = f"{match['title']} ({movie.year}){movie.ext}"
            stats.log(f"Match found for: {new_name}")
            return new_name

        elif len(filtered) > 1:
            match = prompt_user_for_choice(filtered, movie.title, movie.year)

            if match is None:
                stats.log(
                    f"Skipping '{movie.filename}': User couldn't decide"
                )
                stats.user_skipped_files.append(movie.title)
                stats.skip(movie.filename)
                return None

            new_name = f"{match['title']} ({movie.year}){movie.ext}"
            stats.log(f"Match found for: {new_name}")
            return new_name

        else:
            stats.log(f"Skipping '{movie.filename}': no results using year {movie.year}")
            stats.skipped_no_results.append(f"{movie.title} ({movie.year})")
            stats.skip(movie.filename)
            return None

    else:

        if len(results) == 1:
            match = results[0]
            match_year = match.get("release_date", "????")[:4]
            new_name = f"{match['title']} ({match_year}){movie.ext}"
            stats.log(f"Match found for: {new_name}")
            return new_name

        elif len(results) > 1:
            match = prompt_user_for_choice(results, movie.title, None)

            if match is None:
                stats.log(f"Skipping - User Skipped - '{movie.filename}'")
                stats.user_skipped_files.append(movie.title)
                stats.skip(movie.filename)
                return None

            match_year = match.get("release_date", "????")[:4]
            new_name = f"{match['title']} ({match_year}){movie.ext}"
            stats.log(f"Match found for: {new_name}")
            return new_name

        else:
            stats.log(f"Skipping '{movie.filename}': no results and no year")
            stats.skipped_no_year.append(movie.filename)
            stats.skip(movie.filename)
            return None
        
def apply_rename(movie, new_name, dry_run, stats):

    target_path = movie.target_path(new_name)

    if dry_run:
        stats.log(f"{movie.filename} -> {new_name}")
        stats.success()
        return

    if os.path.exists(target_path):
        stats.log(f"Skipping '{movie.filename}': target already exists")
        stats.skip(movie.filename)
        return

    os.rename(movie.full_path, target_path)

    stats.log(f"Renamed '{movie.filename}' -> '{new_name}'")
    stats.success()

def normalize_files(folder, dry_run=True):
    stats = Stats()

    # Collect all files recursively
    all_files = []
    for root, dirs, files in os.walk(folder):

        skipped = [d for d in dirs if d.lower() in SKIP_FOLDERS]
        if skipped:
            skipped_paths = [os.path.join(root, d) for d in skipped]
            stats.log(f"Skipping folder(s): {', '.join(skipped_paths)}")
        
        dirs[:] = [d for d in dirs if d.lower() not in SKIP_FOLDERS]

        for f in files:
            all_files.append((root, f))  # store folder + filename

    # Progress bar
    all_files = tqdm(all_files, desc="Processing files", unit="file")

    for folder_path, filename in all_files:
        movie = MovieFile(folder_path, filename)

        if should_skip_file(movie, stats):
            continue

        stats.log(
            f"Cleaned filename from '{movie.filename}' "
            f"to '{movie.title}' and year '{movie.year}'"
        )

        results = search_movie(movie, stats)
        if results is None:
            stats.skip(movie.filename)
            continue

        new_name = resolve_movie_match(results, movie, stats)
        if not new_name:
            continue

        apply_rename(movie, new_name, dry_run, stats)

    # Write log once at the end
    write_log(folder, stats)    


def write_log(folder, stats):

    log_path = os.path.join(os.getcwd(), "movie_rename.log")

    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"Movie folder processed: {folder}\n")
        f.write(f"Results: Success {stats.success_count}, Skipped {stats.skipped_count}\n\n")

        f.write("\nSkipped Filename Clean Failure:\n")
        for s in stats.skipped_no_year:
            f.write(s + "\n")

        f.write("\nSkipped No Results:\n")
        for s in stats.skipped_no_results:
            f.write(s + "\n")

        f.write("\nUser Skipped Files:\n")
        for s in stats.user_skipped_files:
            f.write(s + "\n")

        f.write("\nSkipped files:\n")
        for s in stats.skipped_files:
            f.write(f"- {s}\n")

        f.write("\nDetailed logs:\n")
        for line in stats.logs:
            f.write(line + "\n")

    print(f"Summary: Success {stats.success_count}, Skipped {stats.skipped_count}")
    print(f"Detailed log written to {log_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rename movies using TMDB metadata.")
    parser.add_argument("--apply", action="store_true", help="Apply the renames, otherwise just dry run")
    parser.add_argument("folder", nargs="?", default=".", help="Folder containing movie files")
    args = parser.parse_args()

    normalize_files(args.folder, dry_run=not args.apply)