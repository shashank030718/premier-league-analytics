
import requests
import pandas as pd
from bs4 import BeautifulSoup


URL = "https://www.bbc.co.uk/sport/football/premier-league/table"


def fetch_page(url):
    """Retrieve and parse a webpage."""
    response = requests.get(
        url,
        timeout=20,
        headers={
            "User-Agent": "Mozilla/5.0 PremierLeagueAnalytics/1.0"
        }
    )
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def extract_table(soup):
    """Extract the HTML table into a DataFrame."""
    table = soup.find("table")

    if table is None:
        raise ValueError("No HTML table found.")

    rows = []

    for tr in table.find_all("tr"):
        cells = tr.find_all(["th", "td"])

        if cells:
            rows.append([
                cell.get_text(" ", strip=True)
                for cell in cells
            ])

    if len(rows) < 2:
        raise ValueError("The table has insufficient data.")

    headers = rows[0]
    records = [
        row for row in rows[1:]
        if len(row) == len(headers)
    ]

    return pd.DataFrame(records, columns=headers)


def transform_data(df):
    """Clean and transform the extracted football statistics."""

    # Rename columns consistently.
    df = df.rename(columns={
        "Team": "team",
        "Played": "played",
        "Won": "won",
        "Drawn": "drawn",
        "Lost": "lost",
        "Goals For": "goals_for",
        "Goals Against": "goals_against",
        "Goal Difference": "goal_difference",
        "Points": "points",
        "Form, Last 6 games, Oldest first": "form"
    })

    # Extract league position from the team field.
    df["position"] = pd.to_numeric(
        df["team"].str.extract(r"^\s*(\d+)\s+")[0],
        errors="coerce"
    )

    df["team"] = df["team"].str.replace(
        r"^\s*\d+\s+", "", regex=True
    ).str.strip()

    # Convert statistics into numeric values.
    numeric_columns = [
        "position",
        "played",
        "won",
        "drawn",
        "lost",
        "goals_for",
        "goals_against",
        "goal_difference",
        "points"
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    # Fail if required values are missing.
    required_columns = ["team"] + numeric_columns

    if df[required_columns].isnull().any().any():
        raise ValueError(
            "Missing or invalid values found in required columns."
        )

    # These columns represent whole-number statistics.
    df[numeric_columns] = df[numeric_columns].astype(int)

    # Remove duplicate records.
    df = df.drop_duplicates(subset=["team"]).copy()

    # Validate the data.
    if df["team"].str.strip().eq("").any():
        raise ValueError("An empty team name was found.")

    if df["team"].duplicated().any():
        raise ValueError("Duplicate team names were found.")

    if (df[["played", "won", "drawn", "lost",
            "goals_for", "goals_against"]] < 0).any().any():
        raise ValueError("Negative statistics were found.")

    if not (
        df["won"] + df["drawn"] + df["lost"]
        == df["played"]
    ).all():
        raise ValueError(
            "Wins + draws + losses do not equal matches played."
        )

    if not (
        df["goals_for"] - df["goals_against"]
        == df["goal_difference"]
    ).all():
        raise ValueError("Goal difference validation failed.")

    if not (
        3 * df["won"] + df["drawn"] == df["points"]
    ).all():
        raise ValueError("Points validation failed.")

    # Keep only the columns needed for analytics.
    columns = [
        "position",
        "team",
        "played",
        "won",
        "drawn",
        "lost",
        "goals_for",
        "goals_against",
        "goal_difference",
        "points"
    ]

    return df[columns].sort_values("position").reset_index(drop=True)




def save_data(df):
    """Save the validated DataFrame as CSV and Parquet."""

    import os

    os.makedirs("data", exist_ok=True)

    csv_path = "data/premier_league.csv"
    parquet_path = "data/premier_league.parquet"

    df.to_csv(csv_path, index=False)
    df.to_parquet(parquet_path, index=False)

    print("\nFiles saved successfully!")
    print("CSV:", csv_path)
    print("Parquet:", parquet_path)


def verify_saved_data():
    """Read both files and verify their shape."""

    csv_df = pd.read_csv("data/premier_league.csv")
    parquet_df = pd.read_parquet("data/premier_league.parquet")

    print("\nCSV shape:", csv_df.shape)
    print("Parquet shape:", parquet_df.shape)

    if csv_df.shape != parquet_df.shape:
        raise ValueError("CSV and Parquet shapes do not match.")

    print("Both files verified successfully!")


def main():
    print("Fetching Premier League statistics...")

    try:
        soup = fetch_page(URL)
        raw_df = extract_table(soup)

        print("Raw rows extracted:", len(raw_df))

        clean_df = transform_data(raw_df)
        save_data(clean_df)
        verify_saved_data()

        print("\nTransformation successful!")
        print("Clean dataset shape:", clean_df.shape)
        print("\nClean column names:")
        print(clean_df.columns.tolist())

        print("\nFirst five cleaned rows:")
        print(clean_df.head().to_string(index=False))

        print("\nData types:")
        print(clean_df.dtypes)

    except (requests.RequestException, ValueError) as error:
        print("Pipeline failed:", error)


if __name__ == "__main__":
    main()
