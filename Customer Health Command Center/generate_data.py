"""
generate_data.py
Creates a mock dataset of 50 restaurants with weekly behavioral signals
and activation milestone completion flags.
Produces realistic variance: healthy, at-risk, and churning cohorts.
"""

import random
import pandas as pd

random.seed(42)

RESTAURANTS = [
    # Italian
    ("Napoli Kitchen", "Italian"), ("Trattoria Roma", "Italian"), ("Bella Pasta Co.", "Italian"),
    ("Osteria Fiorella", "Italian"), ("Villa Rosso", "Italian"),
    # Mexican
    ("Casa del Sol", "Mexican"), ("Taqueria Azteca", "Mexican"), ("El Rancho Grill", "Mexican"),
    ("Cocina Lola", "Mexican"), ("Señor Taco", "Mexican"),
    # American
    ("Main St. Burger", "American"), ("The Smokehouse", "American"), ("Liberty Diner", "American"),
    ("Big Sky Grill", "American"), ("Crossroads BBQ", "American"), ("Founders Kitchen", "American"),
    # Asian
    ("Golden Dragon", "Chinese"), ("Sakura Sushi", "Japanese"), ("Pho Saigon", "Vietnamese"),
    ("Bangkok Bites", "Thai"), ("Seoul Bowl", "Korean"), ("Dim Sum Palace", "Chinese"),
    ("Zen Ramen", "Japanese"), ("Spice Route", "Indian"),
    # Fast casual
    ("Fresh Bowl Co.", "Fast Casual"), ("The Wrap Station", "Fast Casual"), ("Urban Greens", "Fast Casual"),
    ("Grain & Go", "Fast Casual"), ("Stack'd", "Fast Casual"), ("Daily Harvest Cafe", "Fast Casual"),
    # Pizza
    ("Woodfire Pizza", "Pizza"), ("Slice Republic", "Pizza"), ("Napkin Pizza", "Pizza"),
    ("The Crust", "Pizza"),
    # Seafood / other
    ("Harbor Fish & Chips", "Seafood"), ("The Oyster Bar", "Seafood"), ("Crab Shack", "Seafood"),
    # Breakfast / brunch
    ("Morning Glory", "Breakfast"), ("The Egg Collective", "Breakfast"), ("Sunrise Cafe", "Breakfast"),
    ("Brunch Box", "Breakfast"),
    # Mediterranean / Middle Eastern
    ("Olive & Vine", "Mediterranean"), ("Falafel Palace", "Mediterranean"), ("The Mezze Table", "Mediterranean"),
    # Burgers / sandwiches
    ("Smash Bros. Burgers", "Burgers"), ("The Patty Lab", "Burgers"), ("Stack House", "Burgers"),
    # Misc
    ("Corner Bistro", "Bistro"), ("The Local Table", "Bistro"), ("Neighborhood Eats", "American"),
    ("Park Ave Kitchen", "American"), ("Midtown Cantina", "Mexican"),
]

TOTAL_FEATURES = 8  # total Owner features available

# Activation milestones: (column_name, label, due_by_month)
MILESTONES = [
    ("m_online_ordering",      "Online ordering live",          1),
    ("m_menu_digitized",       "Menu digitized",                1),
    ("m_loyalty_enrolled",     "Loyalty enrollment live",       2),
    ("m_first_campaign",       "First campaign sent",           2),
    ("m_branded_app",          "Branded app promoted",          3),
    ("m_payment_connected",    "Payment processing connected",  3),
    ("m_review_management",    "Review management active",      3),
    ("m_second_campaign",      "Second campaign sent",          4),
]


def _activation_milestones(months: int, health: str) -> dict:
    """
    Generate realistic milestone completion based on tenure and health tier.
    Healthy customers mostly complete on time; at-risk/churning have gaps.
    """
    # Base completion probability per tier
    p_base = {"healthy": 0.92, "at_risk": 0.60, "churning": 0.30}[health]

    result = {}
    for col, _, due_month in MILESTONES:
        if months < due_month:
            # Not due yet — always False
            result[col] = False
        else:
            # Should be done: probability decreases for unhealthy customers
            months_overdue = months - due_month
            # Slightly higher chance if they've had more time
            p = min(0.98, p_base + months_overdue * 0.03)
            result[col] = random.random() < p
    return result


def _healthy(name, cuisine):
    """High engagement, strong direct ordering."""
    prev = random.randint(280, 420)
    curr = prev + random.randint(-20, 40)
    months = random.randint(8, 36)
    record = {
        "restaurant_name": name,
        "cuisine_type": cuisine,
        "orders_this_week": curr,
        "orders_last_week": prev,
        "direct_order_rate": round(random.uniform(0.58, 0.82), 2),
        "marketing_campaigns_30d": random.randint(3, 8),
        "logins_per_week": random.randint(6, 14),
        "features_used": random.randint(5, 8),
        "total_features": TOTAL_FEATURES,
        "months_on_platform": months,
    }
    record.update(_activation_milestones(months, "healthy"))
    return record


def _at_risk(name, cuisine):
    """Declining signals, mixed engagement."""
    prev = random.randint(150, 300)
    curr = prev - random.randint(20, 80)
    months = random.randint(4, 18)
    record = {
        "restaurant_name": name,
        "cuisine_type": cuisine,
        "orders_this_week": max(curr, 20),
        "orders_last_week": prev,
        "direct_order_rate": round(random.uniform(0.28, 0.50), 2),
        "marketing_campaigns_30d": random.randint(0, 2),
        "logins_per_week": random.randint(2, 5),
        "features_used": random.randint(2, 4),
        "total_features": TOTAL_FEATURES,
        "months_on_platform": months,
    }
    record.update(_activation_milestones(months, "at_risk"))
    return record


def _churning(name, cuisine):
    """Near-zero engagement, heavy third-party dependency."""
    prev = random.randint(80, 200)
    curr = prev - random.randint(40, 100)
    months = random.randint(2, 12)
    record = {
        "restaurant_name": name,
        "cuisine_type": cuisine,
        "orders_this_week": max(curr, 5),
        "orders_last_week": prev,
        "direct_order_rate": round(random.uniform(0.05, 0.25), 2),
        "marketing_campaigns_30d": random.randint(0, 1),
        "logins_per_week": random.randint(0, 2),
        "features_used": random.randint(1, 3),
        "total_features": TOTAL_FEATURES,
        "months_on_platform": months,
    }
    record.update(_activation_milestones(months, "churning"))
    return record


def generate_dataset() -> pd.DataFrame:
    records = []
    shuffled = RESTAURANTS[:]
    random.shuffle(shuffled)

    # 20 healthy, 20 at-risk, 10 churning
    for name, cuisine in shuffled[:20]:
        records.append(_healthy(name, cuisine))
    for name, cuisine in shuffled[20:40]:
        records.append(_at_risk(name, cuisine))
    for name, cuisine in shuffled[40:50]:
        records.append(_churning(name, cuisine))

    df = pd.DataFrame(records)
    df["feature_adoption_rate"] = df["features_used"] / df["total_features"]
    return df


if __name__ == "__main__":
    df = generate_dataset()
    print(df.to_string(index=False))
    print(f"\n{len(df)} restaurants generated.")
