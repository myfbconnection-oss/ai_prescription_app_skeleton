from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from itertools import combinations
import math
import random

router = APIRouter()

# -----------------------------
# Pydantic Models
# -----------------------------
class UserLocation(BaseModel):
    latitude: float
    longitude: float
class DeliveryRequest(BaseModel):
    prescription_salts: List[str]
    user_location: UserLocation
    demand_factor: Optional[float] = 0.0
    convenience_factor: Optional[bool] = True

# -----------------------------
# Generate Mock Data
# -----------------------------
def generate_mock_shops():
    base_lat = 28.5355
    base_lon = 77.3910
    salts = [f"Medicine {i}mg" for i in range(1, 51)]
    shops = []

    for i in range(1, 51):
        shop_inventory = {}
        # Inventory variation
        if i % 5 == 0:
            available_salts = salts  # full inventory
        elif i % 3 == 0:
            available_salts = random.sample(salts, 35)  # partial inventory
        else:
            available_salts = random.sample(salts, 20)  # limited inventory

        for salt in available_salts:
            shop_inventory[salt] = {
                "brand": f"Brand_{salt.replace(' ', '')}_{i}",
                "price": round(random.uniform(5.0, 20.0), 2)
            }

        shop = {
            "shop_id": f"S{i:03}",
            "shop_name": f"Vendor_{i}",
            "base_cost": round(random.uniform(0.0, 25.0), 2),
            "location": {
                "latitude": base_lat + random.uniform(-0.01, 0.01),
                "longitude": base_lon + random.uniform(-0.01, 0.01)
            },
            "inventory": shop_inventory
        }
        shops.append(shop)
    return shops, salts

shops, all_salts = generate_mock_shops()

# -----------------------------
# Helper Functions
# -----------------------------
def calculate_distance_km(loc1, loc2):
    return math.sqrt((loc1["latitude"] - loc2["latitude"])**2 + (loc1["longitude"] - loc2["longitude"])**2) * 111

def calculate_delivery_cost(base_cost, distance_km, demand_factor):
    return base_cost + (distance_km * 5) + demand_factor
def get_fulfillment_combinations(prescription_salts):
    valid_combinations = []
    for r in range(1, len(shops)+1):
        for combo in combinations(shops, r):
            covered_salts = set()
            for shop in combo:
                covered_salts.update(shop["inventory"].keys())
            if all(salt in covered_salts for salt in prescription_salts):
                valid_combinations.append(combo)
    return valid_combinations

# -----------------------------
# Endpoint
# -----------------------------
@router.post("/delivery/calculate")
def calculate_delivery(request: DeliveryRequest):
    prescription_salts = request.prescription_salts
    user_location = request.user_location
    demand_factor = request.demand_factor
    convenience_factor = request.convenience_factor

    combinations_list = get_fulfillment_combinations(prescription_salts)
    if not combinations_list:
        raise HTTPException(status_code=404, detail="No shop combinations found to fulfill prescription.")

    ranked_options = []

    for combo in combinations_list:
        fulfillment_details = []
        total_medicine_cost = 0.0
        total_delivery_cost = 0.0

        for shop in combo:
            items = []
            for salt in prescription_salts:
                if salt in shop["inventory"]:
                    item = shop["inventory"][salt]
                    items.append({
                        "salt": salt,
                        "brand": item["brand"],
                        "price": item["price"]
                    })
                    total_medicine_cost += item["price"]

            distance_km = calculate_distance_km(shop["location"], user_location.dict())
            delivery_cost = calculate_delivery_cost(shop["base_cost"], distance_km, demand_factor)
            total_delivery_cost += delivery_cost

            fulfillment_details.append({
                "shop_id": shop["shop_id"],
                "shop_name": shop["shop_name"],
                "delivery_cost": round(delivery_cost, 2),
                "items": items
            })

        grand_total = round(total_medicine_cost + total_delivery_cost, 2)
        ranked_options.append({
            "num_shops": len(combo),
            "total_medicine_cost": round(total_medicine_cost, 2),
            "total_delivery_cost": round(total_delivery_cost, 2),
            "grand_total": grand_total,
            "fulfillment_details": fulfillment_details
        })

    ranked_options.sort(key=lambda x: (x["num_shops"], x["grand_total"]))
    for i, option in enumerate(ranked_options):
        option["rank"] = i + 1
        option["priority_reason"] = "Fewest shops + reasonable cost" if convenience_factor else "Lowest cost"

    return {
        "msg": "✅ Optimal fulfillment scenarios calculated and ranked.",
        "prescription_salts": prescription_salts,
        "optimal_options_ranked": ranked_options
    }
