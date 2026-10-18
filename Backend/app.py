from dotenv import load_dotenv
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from datetime import datetime
import anthropic
import json
import sqlite3

#-------SETUP-------
load_dotenv()
claudeAI = anthropic.Anthropic(timeout=30.0)
geolocator = Nominatim(user_agent="dubhacks-volunteerApp")

# --------FUNCTIONS---------

#returns latitude and longitude of the user, or None if the lookup fails
def zip_to_coords(zip_code):
    try:
        location = geolocator.geocode({"postalcode": zip_code, "country": "US"}, timeout=5)
        if location is None:
            return None
        return location.latitude, location.longitude
    except Exception as e:
        print("Lookup error:", repr(e))     # shows the real problem
        return None

#returns up to 100 of the closest upcoming jobs within the max distance
def jobProximinity(user_lat, user_lon, max_miles, limit=100):
    database = sqlite3.connect("Backend/volunteer.db")
    database.row_factory = sqlite3.Row
    currDate = datetime.now().strftime("%Y-%m-%d %H:%M")
    rows = database.execute(
        """
        SELECT j.*, o.org_name
        FROM jobs j
        JOIN organizations o ON j.org_id = o.org_id
        WHERE j.start_time >= ?
        """,
        (currDate,),
    ).fetchall()
    database.close()

    nearbyJobs = []
    for row in rows:
        distMiles = geodesic((user_lat, user_lon), (row["latitude"], row["longitude"])).miles
        if distMiles <= max_miles:
            job = dict(row)
            job["distAway"] = round(distMiles, 1)
            job["skills_needed"] = json.loads(job["skills_needed"] or "[]")
            nearbyJobs.append(job)
    nearbyJobs.sort(key=lambda j: j["distAway"])
    return nearbyJobs[:limit]

#returns the jobs as one block of text, one job per line
def shiftsInString(jobs):
    lines = []
    for j in jobs:
        day = datetime.strptime(j["start_time"], "%Y-%m-%d %H:%M").strftime("%A")
        lines.append(
            f"{j['job_id']}. {j['title']} at {j['org_name']} - {j['description']} "
            f"| {j['distAway']} miles away | {day} {j['start_time']} to {j['end_time']} "
            f"| skills: {', '.join(j['skills_needed'])}"
        )
    return "\n".join(lines)


#-------User and Ai prompting-------

userZipcode = input("What is your zipcode? ").strip()
maxDist = int(input("What is the max distance you would travel (miles)? "))
datesFree = input("What time are you usually free throughout the week? (format: Sunday 8am-10am, 3pm-5pm; Monday 1pm-4pm) ")
skillSet = input("Any skills? ")

userCoords = zip_to_coords(userZipcode)
if userCoords is None:
    print("Couldn't find that ZIP code.")
    raise SystemExit

possNearbyJobs = jobProximinity(userCoords[0], userCoords[1], maxDist)
if not possNearbyJobs:
    print("No shifts found within that distance. Try a bigger number.")
    raise SystemExit

availableShifts = shiftsInString(possNearbyJobs)
print(f"\nFound {len(possNearbyJobs)} shifts nearby:\n{availableShifts}\n")

#Calls AI
claudePrompt = f"""A volunteer is described:
Skill-set: {skillSet}
Availability: {datesFree}

Available shifts:
{availableShifts}

Only recommend shifts that fall inside the volunteer's availability (check the weekday and
time). Which shift fits best? Then rank the top 5 from most to least compatible, one short
sentence of reasoning each. Use bullet points."""


response = claudeAI.messages.create(
    model="claude-haiku-5-5",
    max_tokens=5000,
    messages=[{"role": "user", "content": claudePrompt}],
)
for block in response.content:
    if block.type == "text":
        print(block.text)