from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)

class Barrel(BaseModel):
    sku: str

    ml_per_barrel: int
    potion_type: list[int]
    price: int

    quantity: int

@router.post("/deliver/{order_id}")
def post_deliver_barrels(barrels_delivered: list[Barrel], order_id: int):
    """ """

    print(f"Barrels delivered: {barrels_delivered}, Order_id: {order_id}")
    total_green_ml, total_red_ml, total_blue_ml, total_dark_ml = 0, 0, 0, 0
    total_price = 0
    t = "Barrel delivery"
    for barrel in barrels_delivered:
        total_price += barrel.price * barrel.quantity
        if barrel.potion_type == [0, 1, 0, 0]:
            total_green_ml += barrel.ml_per_barrel * barrel.quantity
        elif barrel.potion_type == [1, 0, 0, 0]:
            total_red_ml += barrel.ml_per_barrel * barrel.quantity
        elif barrel.potion_type == [0, 0, 1, 0]:
            total_blue_ml += barrel.ml_per_barrel * barrel.quantity
        else:
            total_dark_ml += barrel.ml_per_barrel * barrel.quantity

    with db.engine.begin() as connection:
         
         connection.execute(sqlalchemy.text("""INSERT INTO global_inventory (gold, num_red_ml, num_green_ml, num_blue_ml, num_dark_ml, transaction) 
                                            VALUES(:gold, :total_redml, :total_greenml, :total_blueml, :total_darkml, :transaction) """), 
                                            {"total_greenml": total_green_ml, "total_redml": total_red_ml, 
                                             "total_blueml": total_blue_ml, "total_darkml": total_dark_ml,
                                              "gold": -total_price, "transaction": t})
        

    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    sorted_catalog = sorted(wholesale_catalog, key=lambda x: x.price, reverse=True) # reverse=True
    print("Sorted catalog: ", sorted_catalog)

    bp = 0
    plan = []

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""SELECT SUM(gold) AS gold,
                                                    SUM(num_green_ml) AS num_green_ml,
                                                    SUM(num_red_ml) AS num_red_ml,
                                                    SUM(num_blue_ml) AS num_blue_ml,
                                                    SUM(num_dark_ml) AS num_dark_ml
                                                    FROM global_inventory""")).mappings().fetchone()
        
        capacity = connection.execute(sqlalchemy.text("SELECT ml_cap FROM capacity")).scalar_one_or_none()

    print("Time to buy barrels! Current inventory: ", result)

    greenml = result["num_green_ml"]
    redml = result["num_red_ml"]
    blueml = result["num_blue_ml"]
    darkml = result["num_dark_ml"]
    gold = result["gold"]

    gold = gold - 1000 if gold > 1000 else gold # remove on resets
    print(f"Budget: {gold}")

    totalml = greenml + redml + blueml + darkml
    capacity -= totalml
    print(f"{capacity} ml available")
    if capacity == 0 and gold == 0: 
         return[]

    if(redml <= greenml and redml <= blueml):
        least_ml = 0
    elif(greenml <= redml and greenml <= blueml):
        least_ml = 1
    elif(blueml <= greenml and blueml <= redml):
        least_ml = 2

    print("Least ml: ", least_ml)

    for barrel in sorted_catalog:
        bp = barrel.price
        ml = barrel.ml_per_barrel

        if capacity - ml > 0 and gold >= bp:            
            if barrel.potion_type == [0, 0, 0, 1] and darkml < 5000:              
                print("Buying dark barrel")
                plan.append({
                    "sku": barrel.sku,
                    "quantity": 1
                    })      
                darkml += ml
                capacity -= ml
                gold -= bp
                    
            if barrel.potion_type == [1, 0, 0, 0] and least_ml == 0:
                print("Buying red barrel")
                plan.append({
                    "sku": barrel.sku,
                    "quantity": 1
                })
                redml += ml
                capacity -= ml
                gold -= bp
                least_ml = 1 if greenml <= blueml else 2
                    
            elif barrel.potion_type == [0, 1, 0, 0] and least_ml == 1:                    
                print("Buying green barrel")
                plan.append({
                    "sku": barrel.sku,
                    "quantity": 1
                })
                greenml += ml
                capacity -= ml
                gold -= bp
                least_ml = 0 if redml < blueml else 2

            elif barrel.potion_type == [0, 0, 1, 0] and least_ml == 2:
                print("Buying blue barrel")
                plan.append({
                    "sku": barrel.sku,
                    "quantity": 1
                })
                blueml += ml
                capacity -= ml
                gold -= bp
                least_ml = 1 if greenml < redml else 0

    print("Barrel plan: ", plan)
    return plan
