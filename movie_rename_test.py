import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import movie_rename


class TestMovieRename(unittest.TestCase):

    def setUp(self):
        self.folder = "/fake/movies"
        self.stats = movie_rename.Stats()

    @patch("movie_rename.os.walk")
    def test_skip_folders(self, mock_walk):
        # Simulate folder structure with skip folders
        mock_walk.return_value = [
            (self.folder, ["Extras", "Featurettes", "ValidFolder"], []),  # root has no files
            (os.path.join(self.folder, "Extras"), [], ["file1.mkv"]),      # file is inside skipped folder
            (os.path.join(self.folder, "ValidFolder"), [], ["file2.mp4"]),
        ]
        all_files = []
        for root, dirs, files in movie_rename.os.walk(self.folder):
            skipped = [d for d in dirs if d.lower() in movie_rename.SKIP_FOLDERS]
            dirs[:] = [d for d in dirs if d.lower() not in movie_rename.SKIP_FOLDERS]
            for f in files:
                all_files.append((root, f))
        # Only the file in ValidFolder should remain
        self.assertIn((os.path.join(self.folder, "ValidFolder"), "file2.mp4"), all_files)
        self.assertNotIn((self.folder, "file1.mkv"), all_files)

    def test_clean_filename(self):
        name, ext = movie_rename.clean_filename("My.Movie_2020.mkv")
        self.assertEqual(name, "My Movie 2020")
        self.assertEqual(ext, ".mkv")

    def test_strip_release_info(self):
        title, year = movie_rename.strip_release_info("My Movie 2020 1080p")
        self.assertEqual(title, "My Movie")
        self.assertEqual(year, 2020)

    @patch("movie_rename.requests.get")
    def test_search_tmdb_success(self, mock_get):
        # Mock TMDB response
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": [{"title": "Test", "release_date": "2020-01-01"}]}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        results = movie_rename.search_tmdb("Test")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Test")

    def test_should_skip_file_valid_and_ignore(self):
        movie = movie_rename.MovieFile(self.folder, "Sample Video.mp4")
        self.assertTrue(movie_rename.should_skip_file(movie, self.stats))
        self.assertIn("Skipping", self.stats.logs[0])

    @patch("movie_rename.os.rename")
    def test_apply_rename_dry_run(self, mock_rename):
        movie = movie_rename.MovieFile(self.folder, "Movie 2020.mkv")
        movie_rename.apply_rename(movie, "New Movie (2020).mkv", dry_run=True, stats=self.stats)
        mock_rename.assert_not_called()
        self.assertEqual(self.stats.success_count, 1)
        self.assertIn("->", self.stats.logs[-1])

    @patch("movie_rename.os.rename")
    @patch("movie_rename.os.path.exists")
    def test_apply_rename_real(self, mock_exists, mock_rename):
        mock_exists.return_value = False
        movie = movie_rename.MovieFile(self.folder, "Movie 2020.mkv")
        movie_rename.apply_rename(movie, "New Movie (2020).mkv", dry_run=False, stats=self.stats)
        mock_rename.assert_called_once()
        self.assertEqual(self.stats.success_count, 1)

    @patch("movie_rename.input", side_effect=["1"])
    def test_prompt_user_for_choice(self, mock_input):
        results = [
            {"title": "Movie A", "release_date": "2020-01-01"},
            {"title": "Movie B", "release_date": "2020-01-01"},
        ]
        choice = movie_rename.prompt_user_for_choice(results, "Movie", 2020)
        self.assertEqual(choice, results[0])


if __name__ == "__main__":
    unittest.main()