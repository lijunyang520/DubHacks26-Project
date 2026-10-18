"""
seed.py - builds volunteer.db (tables included) and fills it with FAKE demo data
(10 organizations, 100 jobs).

Put this file in Backend/ and run it from the project root with the venv active:

    python Backend/seed.py

Running it again deletes the old database and rebuilds it, so you always get clean demo data.
Everything below is invented for a demo. Call it "sample data" when you present.
"""
import json
import os
import sqlite3
from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash  # installed with Flask

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "volunteer.db")
# The table definitions. organizations must come first because jobs points to it.
SCHEMA = """
PRAGMA foreign_keys = ON;   -- SQLite only enforces foreign keys when this is on

CREATE TABLE IF NOT EXISTS organizations (
    org_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    org_name      TEXT NOT NULL,
    contact_name  TEXT,
    email         TEXT NOT NULL UNIQUE,   -- used to sign in
    password_hash TEXT NOT NULL           -- never the plain password
);

CREATE TABLE IF NOT EXISTS jobs (
    job_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id        INTEGER NOT NULL,
    title         TEXT NOT NULL,          -- e.g. 'Food bank sorting'
    description   TEXT,                   -- the job description
    zip_code      TEXT,                   -- TEXT so leading zeros are kept
    latitude      REAL,                   -- looked up once from the ZIP code
    longitude     REAL,
    start_time    TEXT,                   -- e.g. '2026-11-07 09:00'
    end_time      TEXT,                   -- e.g. '2026-11-07 12:00'
    skills_needed TEXT,                   -- JSON list as text, e.g. '["lifting", "Spanish"]'
    FOREIGN KEY (org_id) REFERENCES organizations (org_id)
);
"""

DEMO_PASSWORD = "demo1234"   # every demo organization signs in with this

# (org_name, contact_name, email) - all invented
ORGS = [
    ("Evergreen Neighbors Pantry",     "Dana Reyes",     "pantry@demo.example"),     # 0
    ("Lakeview Tutoring Collective",   "Marcus Lee",     "tutoring@demo.example"),   # 1
    ("Puget Green Stewards",           "Priya Shah",     "parks@demo.example"),      # 2
    ("Sound Seniors Companions",       "Tom Okafor",     "seniors@demo.example"),    # 3
    ("Paws and Whiskers Shelter",      "Elena Rossi",    "animals@demo.example"),    # 4
    ("Harbor Hands Community Kitchen", "Sam Nguyen",     "kitchen@demo.example"),    # 5
    ("Salmon Run Watershed Alliance",  "Jo Kimura",      "watershed@demo.example"),  # 6
    ("Second Chance Bike Co-op",       "Andre Williams", "bikes@demo.example"),      # 7
    ("Open Page Literacy Project",     "Mei Tan",        "literacy@demo.example"),   # 8
    ("Warm Layers Clothing Closet",    "Carla Mendes",   "clothing@demo.example"),   # 9
]

# Approximate ZIP-area coordinates (good enough for distance demos).
# zip: (latitude, longitude)
ZIPS = {
    "98101": (47.610, -122.337),   # Downtown
    "98103": (47.673, -122.342),   # Fremont / Wallingford
    "98104": (47.601, -122.327),   # Pioneer Square / International District
    "98105": (47.661, -122.299),   # U District
    "98107": (47.669, -122.376),   # Ballard
    "98108": (47.539, -122.321),   # Georgetown
    "98109": (47.632, -122.346),   # Queen Anne / South Lake Union
    "98112": (47.629, -122.296),   # Madison Park / Capitol Hill
    "98115": (47.686, -122.298),   # Northeast Seattle
    "98116": (47.572, -122.398),   # West Seattle (Alki)
    "98117": (47.687, -122.374),   # North Ballard / Crown Hill
    "98118": (47.544, -122.272),   # Columbia City
    "98122": (47.612, -122.306),   # Central District
    "98125": (47.717, -122.295),   # Lake City
    "98126": (47.549, -122.373),   # Delridge
    "98133": (47.734, -122.344),   # North Seattle
    "98136": (47.537, -122.393),   # West Seattle (Fauntleroy)
    "98144": (47.587, -122.299),   # Mount Baker
    "98199": (47.650, -122.402),   # Magnolia
    "98004": (47.617, -122.202),   # Bellevue
    "98033": (47.677, -122.190),   # Kirkland
    "98052": (47.674, -122.122),   # Redmond
}

# (org index, title, description, zip, days from today, start hour, hours long, skills)
JOBS = [
    # --- Evergreen Neighbors Pantry (0) ---
    (0, "Food pantry sorting shift",
        "Sort and box donated groceries for weekend distribution. Includes lifting up to 25 lbs.",
        "98107", 3, 9, 3, ["lifting", "teamwork"]),
    (0, "Grocery delivery driver",
        "Deliver grocery boxes to homebound neighbors using your own car.",
        "98133", 5, 10, 3, ["driving", "friendly"]),
    (0, "Pantry intake desk (Spanish speakers welcome)",
        "Greet visitors, help them sign in, and answer basic questions.",
        "98103", 6, 13, 3, ["Spanish", "customer service"]),
    (0, "Saturday produce distribution",
        "Help neighbors pick out fresh produce at our weekly outdoor market. Mostly standing and bagging.",
        "98133", 10, 9, 3, ["customer service", "teamwork"]),
    (0, "Warehouse stocking helper",
        "Unload delivery pallets and shelve canned goods. Includes lifting up to 30 lbs.",
        "98107", 12, 8, 4, ["lifting", "organization"]),

    # --- Lakeview Tutoring Collective (1) ---
    (1, "After-school math tutor",
        "Help grades 4-6 with homework. No teaching experience needed.",
        "98115", 4, 15, 2, ["tutoring", "math", "patience"]),
    (1, "ESL conversation partner",
        "Practice everyday English with adult learners in a relaxed small group.",
        "98105", 7, 18, 2, ["English", "listening", "tutoring"]),
    (1, "Weekend coding club helper",
        "Assist middle schoolers with beginner Scratch and Python projects.",
        "98122", 8, 10, 2, ["Python", "coding", "tutoring"]),
    (1, "College essay reader",
        "Give friendly, constructive feedback on high school students' college application essays.",
        "98105", 14, 17, 2, ["writing", "feedback", "English"]),
    (1, "Homework help for newcomer families",
        "Support students who are new to the country with homework. Bilingual helpers welcome.",
        "98118", 5, 16, 2, ["tutoring", "Spanish", "patience"]),

    # --- Puget Green Stewards (2) ---
    (2, "Park cleanup and invasive weed removal",
        "Join a crew clearing invasive plants and litter. Tools and gloves provided.",
        "98116", 9, 9, 4, ["outdoors", "lifting"]),
    (2, "Native tree planting day",
        "Plant native trees and shrubs along a hillside. Training on site.",
        "98118", 10, 9, 3, ["outdoors", "gardening"]),
    (2, "Trail monitoring volunteer",
        "Walk a trail section and report hazards using a simple checklist.",
        "98144", 12, 10, 2, ["outdoors", "observation"]),
    (2, "Garden bed weeding and mulching",
        "Care for a community garden bed. Tools provided, beginners welcome.",
        "98103", 11, 10, 3, ["gardening", "outdoors"]),
    (2, "Pollinator meadow planting",
        "Plant wildflowers that support bees and butterflies.",
        "98199", 15, 9, 3, ["gardening", "outdoors"]),

    # --- Sound Seniors Companions (3) ---
    (3, "Friendly visitor for seniors",
        "Weekly conversation and card games with an older adult.",
        "98109", 5, 14, 2, ["conversation", "patience"]),
    (3, "Tech helper for older adults",
        "Help seniors set up phones and video calls.",
        "98004", 11, 11, 2, ["tech skills", "patience"]),
    (3, "Transit ride companion",
        "Accompany a senior on public transit to a medical appointment.",
        "98122", 13, 9, 3, ["transit", "reliability"]),
    (3, "Phone call buddy (from home)",
        "Make a friendly weekly call to an older adult who lives alone. Done from home.",
        "98115", 3, 17, 1, ["conversation", "reliability"]),
    (3, "Senior center bingo helper",
        "Help run a Friday bingo afternoon and serve snacks.",
        "98126", 8, 13, 2, ["teamwork", "friendly"]),

    # --- Paws and Whiskers Shelter (4) ---
    (4, "Dog walking",
        "Walk shelter dogs. Training provided on your first visit.",
        "98052", 4, 8, 2, ["animals", "walking"]),
    (4, "Cat socializing hour",
        "Spend time with shelter cats to help them get used to people.",
        "98115", 6, 16, 1, ["animals", "gentle"]),
    (4, "Adoption event greeter",
        "Welcome visitors at a weekend adoption event and answer basic questions.",
        "98033", 9, 11, 3, ["animals", "customer service"]),
    (4, "Kennel cleaning crew",
        "Clean kennels and refill water bowls. Gloves and boots provided.",
        "98052", 7, 7, 3, ["animals", "lifting"]),
    (4, "Photographer for adoptable pets",
        "Take clear, friendly photos of adoptable pets for the shelter website.",
        "98004", 13, 12, 2, ["photography", "animals", "patience"]),

    # --- Harbor Hands Community Kitchen (5) ---
    (5, "Meal prep kitchen shift",
        "Chop, cook and pack meals for community dinners.",
        "98118", 5, 8, 4, ["cooking", "food safety", "lifting"]),
    (5, "Dinner service and cleanup",
        "Serve dinner, then help clean up the dining room and kitchen.",
        "98144", 7, 16, 3, ["teamwork", "customer service"]),
    (5, "Weekend brunch server",
        "Serve brunch to guests and keep the dining room tidy.",
        "98104", 9, 9, 3, ["customer service", "teamwork"]),
    (5, "Dishwashing and kitchen cleanup",
        "Run the dish station during dinner service.",
        "98101", 6, 17, 3, ["teamwork", "lifting"]),
    (5, "Menu planning volunteer",
        "Help plan weekly menus around donated ingredients. Cooking or nutrition background welcome.",
        "98112", 16, 18, 2, ["cooking", "planning", "nutrition"]),

    # --- Salmon Run Watershed Alliance (6) ---
    (6, "Creek water-quality sampling",
        "Collect and record water samples with a trained team lead.",
        "98125", 10, 9, 3, ["outdoors", "observation", "science"]),
    (6, "Salmon stream habitat cleanup",
        "Remove trash and invasive plants along a salmon-bearing stream.",
        "98108", 12, 9, 4, ["outdoors", "lifting"]),
    (6, "Storm drain marking",
        "Place small markers by storm drains to remind neighbors that drains flow to the creek.",
        "98136", 4, 10, 2, ["outdoors", "walking"]),
    (6, "Watershed education table",
        "Staff an info table at a neighborhood fair and talk with families about local streams.",
        "98117", 15, 11, 3, ["public speaking", "customer service", "science"]),
    (6, "Beach naturalist helper",
        "Help visitors find tide pool creatures and learn about them.",
        "98116", 17, 8, 3, ["outdoors", "education", "patience"]),

    # --- Second Chance Bike Co-op (7) ---
    (7, "Bike repair helper",
        "Help fix donated bikes alongside an experienced mechanic. Training provided.",
        "98108", 6, 11, 3, ["mechanical", "patience"]),
    (7, "Kids bike safety clinic",
        "Teach basic helmet fitting and riding safety to kids.",
        "98122", 14, 10, 3, ["teaching", "patience", "biking"]),
    (7, "Bike donation sorting",
        "Sort donated bikes and parts by condition.",
        "98144", 3, 14, 2, ["organization", "lifting"]),
    (7, "Earn-a-bike workshop assistant",
        "Support teens building their own bike, step by step.",
        "98118", 18, 15, 3, ["mechanical", "tutoring", "patience"]),

    # --- Open Page Literacy Project (8) ---
    (8, "Story time reader",
        "Read picture books aloud to preschoolers at the library.",
        "98103", 5, 10, 1, ["reading aloud", "kids", "friendly"]),
    (8, "Adult literacy tutor",
        "Help adults build reading and writing skills one-on-one.",
        "98104", 9, 18, 2, ["tutoring", "patience", "English"]),
    (8, "Book sorting and shelving",
        "Sort donated books by reading level and shelve them.",
        "98105", 4, 13, 3, ["organization", "lifting"]),
    (8, "Bilingual story time (Spanish)",
        "Read and sing in Spanish with families.",
        "98118", 11, 11, 1, ["Spanish", "reading aloud", "kids"]),
    (8, "Writing workshop helper",
        "Support a teen creative-writing workshop with prompts and encouragement.",
        "98122", 16, 16, 2, ["writing", "mentoring", "English"]),

    # --- Warm Layers Clothing Closet (9) ---
    (9, "Clothing closet sorting",
        "Sort donated clothes by size and season.",
        "98133", 7, 10, 3, ["organization", "teamwork"]),
    (9, "Personal shopper for guests",
        "Help guests find clothing that fits their needs, with kindness and respect.",
        "98125", 13, 12, 3, ["customer service", "empathy"]),
    (9, "Winter coat drive helper",
        "Collect and tag coats at a drop-off table.",
        "98004", 19, 10, 4, ["teamwork", "organization"]),
    (9, "Mending and alterations",
        "Do simple repairs like sewing on buttons and fixing hems on donated clothing.",
        "98109", 8, 14, 3, ["sewing", "patience"]),

    # ===== More shifts, so every organization has 10 =====

    # --- Evergreen Neighbors Pantry (0) ---
    (0, "Evening meal box packing",
        "Pack boxes of shelf-stable meals for families. Light lifting, music on, good for groups.",
        "98133", 2, 17, 2, ["teamwork", "organization"]),
    (0, "Bilingual phone line helper",
        "Answer calls about pantry hours and call back neighbors who left messages. Done on site.",
        "98103", 14, 10, 3, ["Spanish", "customer service", "phone skills"]),
    (0, "Holiday meal box assembly",
        "Assemble holiday meal boxes with turkey, sides and pantry staples.",
        "98107", 22, 9, 4, ["lifting", "teamwork"]),
    (0, "Neighborhood food drive organizer",
        "Set up and staff a collection table at a local grocery store.",
        "98117", 17, 11, 3, ["public speaking", "organization"]),
    (0, "Inventory counting helper",
        "Count and log pantry stock using a simple spreadsheet. Laptop provided.",
        "98133", 18, 13, 2, ["spreadsheets", "attention to detail"]),

    # --- Lakeview Tutoring Collective (1) ---
    (1, "Saturday reading buddy",
        "Read one-on-one with an early reader at a community center.",
        "98118", 6, 10, 2, ["reading aloud", "kids", "patience"]),
    (1, "Science fair mentor",
        "Help students plan and test an experiment for the school science fair.",
        "98115", 20, 16, 2, ["science", "mentoring", "tutoring"]),
    (1, "Robotics club helper",
        "Support a beginner middle school robotics team with building and basic programming.",
        "98105", 11, 15, 3, ["robotics", "coding", "teaching"]),
    (1, "Practice test helper",
        "Help run a Saturday practice test and hand out materials.",
        "98122", 15, 8, 4, ["reliability", "organization"]),
    (1, "Study skills workshop helper",
        "Lead small-group activities on note-taking and time management.",
        "98126", 9, 17, 2, ["teaching", "organization", "friendly"]),

    # --- Puget Green Stewards (2) ---
    (2, "Rain garden maintenance",
        "Weed and mulch a street-side rain garden that filters stormwater.",
        "98126", 13, 9, 3, ["gardening", "outdoors"]),
    (2, "Forest trail restoration",
        "Rebuild steps and drainage on a muddy trail section with a crew lead.",
        "98199", 19, 9, 4, ["outdoors", "lifting", "teamwork"]),
    (2, "Community orchard picking",
        "Pick apples and pears to donate to local pantries.",
        "98136", 4, 10, 3, ["outdoors", "gardening"]),
    (2, "Park bench and sign painting",
        "Repaint park benches and signs. Supplies provided.",
        "98112", 21, 10, 3, ["painting", "outdoors"]),
    (2, "Street tree watering crew",
        "Water newly planted street trees along a walking route.",
        "98104", 2, 16, 2, ["walking", "outdoors"]),

    # --- Sound Seniors Companions (3) ---
    (3, "Morning walking group leader",
        "Lead a gentle neighborhood walk for older adults. Slow pace, friendly chatting.",
        "98109", 10, 9, 2, ["walking", "conversation"]),
    (3, "Grocery shopping assistant",
        "Help a senior with weekly grocery shopping, including carrying bags.",
        "98115", 7, 10, 2, ["driving", "lifting", "patience"]),
    (3, "Memory care music hour",
        "Play music or sing along with residents at an assisted-living home.",
        "98033", 12, 14, 1, ["music", "patience", "friendly"]),
    (3, "Holiday card writing party",
        "Write cards to isolated seniors for the holidays. Supplies provided.",
        "98004", 24, 15, 2, ["writing", "friendly"]),
    (3, "Home safety checklist visitor",
        "Walk through a senior's home with a checklist for trip hazards and smoke alarms. Training included.",
        "98126", 16, 10, 2, ["observation", "reliability"]),

    # --- Paws and Whiskers Shelter (4) ---
    (4, "Cat room cleaning and laundry",
        "Wash blankets and clean cat rooms before adoption hours.",
        "98115", 3, 7, 3, ["animals", "organization"]),
    (4, "Foster family orientation helper",
        "Help new foster families with paperwork and a tour of the shelter.",
        "98033", 18, 13, 2, ["customer service", "animals"]),
    (4, "Pet food bank sorting",
        "Sort donated pet food for families who need help feeding their pets.",
        "98052", 8, 10, 3, ["lifting", "organization", "animals"]),
    (4, "Dog training game helper",
        "Assist a trainer with basic manners games for shelter dogs.",
        "98004", 15, 9, 2, ["animals", "patience"]),
    (4, "Social media content helper",
        "Write short, friendly posts and captions about adoptable pets.",
        "98112", 20, 18, 2, ["writing", "social media", "animals"]),

    # --- Harbor Hands Community Kitchen (5) ---
    (5, "Early morning bread baking",
        "Bake bread for dinner service in a commercial kitchen. Starts at 6 AM.",
        "98104", 11, 6, 4, ["cooking", "food safety"]),
    (5, "Dining room greeter",
        "Welcome guests, hand out numbers, and make sure everyone feels at ease.",
        "98101", 4, 16, 3, ["customer service", "empathy"]),
    (5, "Grocery rescue pickup driver",
        "Pick up surplus food from stores and deliver it to the kitchen.",
        "98108", 9, 8, 3, ["driving", "lifting"]),
    (5, "Kitchen garden helper",
        "Harvest herbs and vegetables from the rooftop garden for the kitchen.",
        "98122", 14, 9, 2, ["gardening", "cooking"]),
    (5, "Community dinner setup crew",
        "Set up and decorate tables for a monthly community dinner.",
        "98144", 21, 15, 3, ["teamwork", "creativity"]),

    # --- Salmon Run Watershed Alliance (6) ---
    (6, "Culvert and stream mapping",
        "Walk a stream and note culverts and barriers on a map using a phone app.",
        "98125", 12, 10, 3, ["outdoors", "observation", "tech skills"]),
    (6, "Native plant nursery helper",
        "Pot and label native seedlings for restoration projects.",
        "98117", 6, 9, 3, ["gardening", "organization"]),
    (6, "Rain barrel workshop assistant",
        "Help neighbors assemble rain barrels at a community workshop.",
        "98108", 19, 11, 3, ["teaching", "mechanical"]),
    (6, "Riparian planting day",
        "Plant live stakes along a stream bank to prevent erosion.",
        "98136", 25, 9, 4, ["outdoors", "lifting", "teamwork"]),
    (6, "Citizen science data entry (from home)",
        "Enter water test results from field sheets into a shared spreadsheet from home.",
        "98133", 5, 17, 2, ["spreadsheets", "attention to detail"]),

    # --- Second Chance Bike Co-op (7) ---
    (7, "Tire and tube repair station",
        "Patch tubes and swap tires at a free community repair day.",
        "98118", 10, 10, 3, ["mechanical", "patience"]),
    (7, "Bike valet at community event",
        "Check and guard bikes at a neighborhood festival.",
        "98103", 17, 11, 4, ["customer service", "reliability"]),
    (7, "Bike route planning volunteer",
        "Help map safe, low-traffic routes for new riders.",
        "98115", 13, 18, 2, ["planning", "biking", "tech skills"]),
    (7, "Helmet donation fitting",
        "Fit donated helmets to kids and adults at a giveaway.",
        "98108", 7, 12, 2, ["customer service", "patience"]),
    (7, "Tools and shop organization",
        "Sort wrenches and parts bins so volunteers can find what they need.",
        "98144", 22, 14, 3, ["organization", "mechanical"]),
    (7, "Bike library check-in desk",
        "Run the check-out desk for a free neighborhood bike loan program.",
        "98122", 2, 10, 3, ["customer service", "reliability"]),

    # --- Open Page Literacy Project (8) ---
    (8, "Teen book club helper",
        "Help lead a lively monthly book club for teens.",
        "98122", 12, 17, 2, ["reading aloud", "mentoring", "English"]),
    (8, "Library card sign-up helper",
        "Help families sign up for library cards at a community event.",
        "98118", 5, 11, 3, ["customer service", "Spanish"]),
    (8, "Little free library stocker",
        "Refill neighborhood little free libraries with sorted donated books.",
        "98117", 20, 10, 2, ["organization", "walking"]),
    (8, "Third grade reading club",
        "Read together and complete short activities with third graders.",
        "98126", 8, 15, 2, ["tutoring", "kids", "patience"]),
    (8, "ESL reading circle facilitator",
        "Lead a gentle reading circle for adults learning English.",
        "98101", 15, 18, 2, ["English", "tutoring", "listening"]),

    # --- Warm Layers Clothing Closet (9) ---
    (9, "Shoe and sock sorting",
        "Sort donated shoes and socks by size, then pair them up.",
        "98125", 4, 10, 3, ["organization", "teamwork"]),
    (9, "Back-to-school clothing fair helper",
        "Help families choose clothing at a back-to-school giveaway.",
        "98133", 23, 11, 4, ["customer service", "empathy"]),
    (9, "Interview clothes stylist",
        "Help job seekers find professional outfits for interviews.",
        "98104", 11, 13, 3, ["customer service", "empathy", "fashion"]),
    (9, "Laundry and steaming helper",
        "Wash and steam donated items so they are ready for guests.",
        "98109", 6, 9, 3, ["organization", "attention to detail"]),
    (9, "Kids clothing closet organizer",
        "Sort children's clothing by size and arrange it for easy shopping.",
        "98004", 18, 10, 3, ["organization", "kids"]),
    (9, "Donation drop-off greeter",
        "Greet donors, thank them, and sort items quickly at the drop-off door.",
        "98133", 3, 12, 3, ["customer service", "friendly"]),
]


def build_database():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    # 1. Create the tables
    conn.executescript(SCHEMA)

    # 2. Insert the organizations
    password_hash = generate_password_hash(DEMO_PASSWORD, method="pbkdf2:sha256")
    org_ids = []
    for org_name, contact_name, email in ORGS:
        cur = conn.execute(
            "INSERT INTO organizations (org_name, contact_name, email, password_hash) "
            "VALUES (?, ?, ?, ?)",
            (org_name, contact_name, email, password_hash),
        )
        org_ids.append(cur.lastrowid)

    # 3. Insert the jobs, with dates counted from today so they are always upcoming
    today = datetime.now().replace(minute=0, second=0, microsecond=0)
    for org_index, title, description, zip_code, days, hour, hours, skills in JOBS:
        latitude, longitude = ZIPS[zip_code]
        start = (today + timedelta(days=days)).replace(hour=hour)
        end = start + timedelta(hours=hours)
        conn.execute(
            "INSERT INTO jobs (org_id, title, description, zip_code, latitude, longitude, "
            "start_time, end_time, skills_needed) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                org_ids[org_index], title, description, zip_code, latitude, longitude,
                start.strftime("%Y-%m-%d %H:%M"), end.strftime("%Y-%m-%d %H:%M"),
                json.dumps(skills),
            ),
        )

    conn.commit()

    # 4. Show a quick summary so you know it worked
    org_count = conn.execute("SELECT COUNT(*) FROM organizations").fetchone()[0]
    job_count = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    print(f"Built {DB_PATH}")
    print(f"  {org_count} organizations, {job_count} jobs")
    print("  Sample rows:")
    rows = conn.execute(
        "SELECT jobs.title, organizations.org_name, jobs.zip_code, jobs.start_time "
        "FROM jobs JOIN organizations ON jobs.org_id = organizations.org_id "
        "ORDER BY jobs.start_time LIMIT 3"
    ).fetchall()
    for title, org_name, zip_code, start_time in rows:
        print(f"    {start_time} | {title} | {org_name} | {zip_code}")

    conn.close()


if __name__ == "__main__":
    build_database()
