import pandas as pd

team = pd.DataFrame(
    [
        dict(name="Brad Westcott", start_date="11/8/21", end_date=""),
        dict(name="Tim Mahoney", start_date="2/14/22", end_date=""),
        dict(name="Cody Gradoville", start_date="7/18/22", end_date="10/21/22"),
        dict(name="Eric Wetzel", start_date="2/22/23", end_date="7/15/24"),
        dict(name="Miles Murphy", start_date="3/27/23", end_date=""),
        dict(name="Austin Carter", start_date="4/3/23", end_date=""),
        dict(name="Edgar Perez", start_date="5/15/23", end_date="1/15/24"),
        dict(name="Jeff Vander Voort", start_date="5/22/23", end_date=""),
        dict(name="Justin Lenz", start_date="7/3/23", end_date=""),
        dict(name="Brian Huffman", start_date="4/8/24", end_date=""),
        dict(name="Christian Janse", start_date="6/1/24", end_date=""),
        dict(name="Genevieve Baumann", start_date="7/29/24", end_date=""),
        dict(name="Mariñe Rodriguez Saiz", start_date="8/5/24", end_date=""),
        dict(name="Sam Webster", start_date="8/26/24", end_date=""),
    ]
)

team[["start_date", "end_date"]] = team[["start_date", "end_date"]].apply(
    pd.to_datetime, format="%m/%d/%y"
)

team["active"] = team["end_date"].isnull()
team['ramped_date'] = team['start_date'] + pd.DateOffset(months=6)
