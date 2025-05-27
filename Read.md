# Transfermarkt A-League Men Lineup Scraper

This Python script uses SeleniumBase to scrape match lineup data from the Transfermarkt website for the A-League Men competition. It extracts detailed player information (name, age, position, market value, nationality) for both home and away teams, for every match in a given season, and saves the data as CSV files.

## Features
- Scrapes all matches from the A-League Men season schedule page.
- Extracts starting XI and substitutes for both teams.
- Saves each match's data to a separate CSV file in the `match_csvs/` folder.
- Tracks progress to avoid re-scraping matches (using `match_csvs/progress.json`).
- Handles various date formats and sanitizes filenames.

## Requirements
- Python 3.7+
- [SeleniumBase](https://github.com/seleniumbase/SeleniumBase)
- Google Chrome (or Chromium-based browser)

Install dependencies:
```bash
pip install seleniumbase
```

## Usage
1. Make sure you have Chrome installed.
2. Run the script:
   ```bash
   python main.py
   ```
3. The script will open a browser, navigate to the A-League Men schedule, and process each match.
4. CSV files will be saved in the `match_csvs/` directory.

## Output
- Each match is saved as a CSV file named with the match date and teams, e.g.:
  `2024-10-19_Auckland FC_vs_Brisbane Roar.csv`
- Progress is tracked in `match_csvs/progress.json` to skip already-scraped matches.

## Customization
- To limit the number of matches processed (for testing), uncomment and adjust the line:
  ```python
  # match_links = match_links[:3]
  ```
- To change the season or competition, modify the URL in the script.

## Notes
- The script uses a 2-second delay between matches to avoid overloading the server.
- If the page structure changes, you may need to update the XPaths in the script.

## License
This project is for educational and personal use. Please respect Transfermarkt's terms of service when scraping data.
