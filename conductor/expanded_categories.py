"""
Expanded Product Categories for High-Entropy Testing

This module provides 350+ unique product categories to dramatically reduce
collision rates during high-concurrency testing.

Categories are organized hierarchically with realistic subcategories to ensure
agents work on distinct data segments during concurrent operations.
"""

# 350+ Product Categories organized by major domains
PRODUCT_CATEGORIES = [
    # Electronics & Technology (50 categories)
    "Smartphones", "Laptops", "Desktop Computers", "Tablets", "E-readers",
    "Smart Watches", "Fitness Trackers", "Gaming Consoles", "VR Headsets", "AR Glasses",
    "Digital Cameras", "Action Cameras", "Camera Lenses", "Tripods", "Camera Bags",
    "Headphones", "Earbuds", "Bluetooth Speakers", "Sound Bars", "Home Theater Systems",
    "4K TVs", "OLED TVs", "Projectors", "TV Mounts", "Streaming Devices",
    "Computer Monitors", "Graphics Cards", "RAM Memory", "SSDs", "Hard Drives",
    "Motherboards", "CPU Processors", "Computer Cases", "Power Supplies", "Cooling Fans",
    "Keyboards", "Gaming Mice", "Mousepads", "Webcams", "Microphones",
    "USB Hubs", "Charging Cables", "Power Banks", "Wireless Chargers", "Phone Cases",
    "Screen Protectors", "Laptop Sleeves", "Docking Stations", "Network Routers", "WiFi Extenders",
    
    # Clothing & Fashion (50 categories)
    "Men's T-Shirts", "Men's Dress Shirts", "Men's Polo Shirts", "Men's Jeans", "Men's Chinos",
    "Men's Suits", "Men's Blazers", "Men's Sweaters", "Men's Hoodies", "Men's Jackets",
    "Women's Blouses", "Women's Dresses", "Women's Skirts", "Women's Jeans", "Women's Leggings",
    "Women's Cardigans", "Women's Coats", "Women's Sweaters", "Women's Jackets", "Women's Pants",
    "Athletic Wear", "Yoga Pants", "Sports Bras", "Running Shorts", "Compression Shirts",
    "Swimwear", "Beach Cover-ups", "Underwear", "Socks", "Ties",
    "Scarves", "Gloves", "Winter Hats", "Baseball Caps", "Sun Hats",
    "Belts", "Suspenders", "Cufflinks", "Bow Ties", "Pocket Squares",
    "Rain Jackets", "Windbreakers", "Vests", "Thermal Underwear", "Pajamas",
    "Robes", "Slippers", "Sandals", "Flip Flops", "Ballet Flats",
    
    # Footwear (30 categories)
    "Running Shoes", "Cross Training Shoes", "Basketball Shoes", "Soccer Cleats", "Tennis Shoes",
    "Hiking Boots", "Work Boots", "Chelsea Boots", "Combat Boots", "Ankle Boots",
    "Dress Shoes", "Oxfords", "Loafers", "Boat Shoes", "Moccasins",
    "High Heels", "Pumps", "Wedges", "Platform Shoes", "Kitten Heels",
    "Espadrilles", "Sneakers", "Slip-On Shoes", "Clogs", "Mary Janes",
    "Winter Boots", "Rain Boots", "Snow Boots", "Steel Toe Boots", "Desert Boots",
    
    # Home & Furniture (40 categories)
    "Sofas", "Sectionals", "Loveseats", "Recliners", "Accent Chairs",
    "Dining Tables", "Dining Chairs", "Bar Stools", "Kitchen Islands", "Coffee Tables",
    "End Tables", "Console Tables", "TV Stands", "Entertainment Centers", "Bookcases",
    "Beds", "Mattresses", "Bed Frames", "Headboards", "Nightstands",
    "Dressers", "Wardrobes", "Armoires", "Vanities", "Mirrors",
    "Desks", "Office Chairs", "File Cabinets", "Desk Lamps", "Coat Racks",
    "Outdoor Furniture", "Patio Sets", "Hammocks", "Gazebos", "Fire Pits",
    "Bean Bags", "Floor Cushions", "Ottomans", "Benches", "Storage Cabinets",
    
    # Kitchen & Dining (35 categories)
    "Cookware Sets", "Frying Pans", "Saucepans", "Stock Pots", "Dutch Ovens",
    "Baking Sheets", "Muffin Tins", "Cake Pans", "Mixing Bowls", "Measuring Cups",
    "Kitchen Knives", "Knife Sets", "Cutting Boards", "Can Openers", "Peelers",
    "Blenders", "Food Processors", "Stand Mixers", "Hand Mixers", "Toasters",
    "Coffee Makers", "Espresso Machines", "Electric Kettles", "Slow Cookers", "Pressure Cookers",
    "Air Fryers", "Rice Cookers", "Waffle Makers", "Griddles", "Deep Fryers",
    "Dinnerware Sets", "Glassware", "Flatware Sets", "Serving Platters", "Salt Shakers",
    
    # Home Decor & Bedding (30 categories)
    "Throw Pillows", "Decorative Pillows", "Curtains", "Blinds", "Shades",
    "Area Rugs", "Runner Rugs", "Bath Mats", "Door Mats", "Wall Art",
    "Picture Frames", "Wall Clocks", "Table Lamps", "Floor Lamps", "Ceiling Lights",
    "Candles", "Candle Holders", "Vases", "Artificial Plants", "Wall Decals",
    "Bed Sheets", "Duvet Covers", "Comforters", "Bed Pillows", "Mattress Toppers",
    "Blankets", "Throws", "Quilts", "Bed Skirts", "Pillow Shams",
    
    # Sports & Outdoors (35 categories)
    "Treadmills", "Exercise Bikes", "Ellipticals", "Rowing Machines", "Weight Benches",
    "Dumbbells", "Barbells", "Kettlebells", "Resistance Bands", "Yoga Mats",
    "Camping Tents", "Sleeping Bags", "Camping Chairs", "Coolers", "Backpacks",
    "Hiking Poles", "Water Bottles", "Hydration Packs", "Headlamps", "Lanterns",
    "Fishing Rods", "Fishing Reels", "Tackle Boxes", "Life Jackets", "Kayaks",
    "Bicycles", "Bike Helmets", "Bike Locks", "Bike Lights", "Bike Pumps",
    "Skateboards", "Scooters", "Inline Skates", "Protective Gear", "Golf Clubs",
    
    # Beauty & Personal Care (30 categories)
    "Face Moisturizers", "Face Cleansers", "Serums", "Face Masks", "Eye Creams",
    "Sunscreens", "BB Creams", "Foundations", "Concealers", "Blushes",
    "Lipsticks", "Lip Glosses", "Mascaras", "Eyeliners", "Eyeshadows",
    "Shampoos", "Conditioners", "Hair Masks", "Hair Oils", "Hair Sprays",
    "Body Lotions", "Body Washes", "Hand Creams", "Perfumes", "Colognes",
    "Deodorants", "Razors", "Shaving Creams", "Toothbrushes", "Electric Toothbrushes",
    
    # Health & Wellness (25 categories)
    "Multivitamins", "Vitamin D", "Vitamin C", "Omega-3", "Probiotics",
    "Protein Powders", "Pre-Workout", "Post-Workout", "BCAAs", "Creatine",
    "Blood Pressure Monitors", "Thermometers", "Pulse Oximeters", "Heating Pads", "Ice Packs",
    "First Aid Kits", "Pain Relief Creams", "Joint Supplements", "Sleep Aids", "Stress Relief",
    "Essential Oils", "Diffusers", "Meditation Cushions", "Foam Rollers", "Massage Balls",
    
    # Books & Media (25 categories)
    "Fiction Books", "Non-Fiction Books", "Biographies", "Self-Help Books", "Cookbooks",
    "Business Books", "Science Books", "History Books", "Art Books", "Travel Books",
    "Children's Books", "Young Adult Books", "Graphic Novels", "Comic Books", "Manga",
    "Audiobooks", "E-Books", "Blu-Ray Movies", "DVDs", "Box Sets",
    "Vinyl Records", "CDs", "Music Downloads", "Sheet Music", "Music Books",
    
    # Toys & Games (30 categories)
    "Action Figures", "Dolls", "Stuffed Animals", "Building Blocks", "LEGO Sets",
    "Board Games", "Card Games", "Puzzle Games", "Strategy Games", "Party Games",
    "Video Games", "PC Games", "Gaming Accessories", "Controllers", "Gaming Headsets",
    "RC Cars", "RC Drones", "Model Trains", "Model Kits", "Science Kits",
    "Art Supplies", "Coloring Books", "Craft Kits", "Slime Kits", "Play-Doh",
    "Outdoor Toys", "Water Toys", "Sports Toys", "Educational Toys", "Musical Toys",
    
    # Baby & Kids (20 categories)
    "Baby Monitors", "Strollers", "Car Seats", "High Chairs", "Baby Carriers",
    "Diaper Bags", "Diapers", "Baby Wipes", "Baby Bottles", "Pacifiers",
    "Crib Sheets", "Baby Blankets", "Swaddles", "Bibs", "Burp Cloths",
    "Baby Gates", "Playpens", "Baby Bouncers", "Baby Swings", "Teething Toys",
    
    # Pet Supplies (20 categories)
    "Dog Food", "Cat Food", "Pet Treats", "Dog Beds", "Cat Beds",
    "Pet Carriers", "Leashes", "Collars", "Pet Toys", "Scratching Posts",
    "Litter Boxes", "Pet Bowls", "Pet Grooming", "Pet Shampoos", "Pet Brushes",
    "Aquariums", "Fish Food", "Bird Cages", "Hamster Cages", "Pet Clothing",
    
    # Automotive (20 categories)
    "Car Covers", "Floor Mats", "Seat Covers", "Steering Wheel Covers", "Dash Cams",
    "Car Chargers", "Phone Mounts", "Air Fresheners", "Car Vacuums", "Tire Inflators",
    "Jump Starters", "Car Wax", "Car Polish", "Car Wash Kits", "Microfiber Towels",
    "Motor Oil", "Oil Filters", "Air Filters", "Windshield Wipers", "Car Batteries",
    
    # Tools & Hardware (20 categories)
    "Power Drills", "Circular Saws", "Jigsaws", "Sanders", "Nail Guns",
    "Tool Sets", "Screwdriver Sets", "Wrench Sets", "Socket Sets", "Pliers",
    "Hammers", "Tape Measures", "Levels", "Utility Knives", "Work Lights",
    "Ladders", "Tool Boxes", "Tool Belts", "Safety Glasses", "Work Gloves",
    
    # Garden & Outdoor (15 categories)
    "Lawn Mowers", "Leaf Blowers", "Hedge Trimmers", "Chainsaws", "Pressure Washers",
    "Garden Hoses", "Sprinklers", "Garden Tools", "Shovels", "Rakes",
    "Wheelbarrows", "Plant Pots", "Garden Soil", "Fertilizers", "Mulch",
]

# Verify we have 350+ categories
assert len(PRODUCT_CATEGORIES) >= 350, f"Expected 350+ categories, got {len(PRODUCT_CATEGORIES)}"

# Additional entropy dimensions for reducing collisions
RATING_VALUES = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
STOCK_RANGES = [(0, 50), (51, 100), (101, 200), (201, 400), (401, 800), (801, 1500)]
PRICE_RANGES = [(5, 25), (25, 50), (50, 100), (100, 250), (250, 500), (500, 1000), (1000, 2500)]
ORDER_STATUSES = ["pending", "processing", "confirmed", "shipped", "delivered", "cancelled", "refunded", "on_hold"]

def get_random_category():
    """Get a random category from the expanded list"""
    import random
    return random.choice(PRODUCT_CATEGORIES)

def get_random_category_subset(count=10):
    """Get a random subset of categories"""
    import random
    return random.sample(PRODUCT_CATEGORIES, min(count, len(PRODUCT_CATEGORIES)))
