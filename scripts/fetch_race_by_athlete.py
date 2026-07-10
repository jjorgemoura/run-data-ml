import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.scrappers.duv.duv import DUVService

def main():
    event_name = "South Downs Way 100"
    athlete_name = "Jorge Moura"

    duv = DUVService()
    sdw100_event = duv.find_event_by_name(event_name)
    
    asdasd = duv.fetch_all_athletes_of_event(111)
    
    races = duv.fetch_races_from_athlete(123)


    for race in races:
        # print(f"Athlete {athlete_name} ran: {race.title}, {race.year}, {race.finishTime}")
        print(f"Athlete {athlete_name} ran: {race}")

if __name__ == "__main__":
    main()