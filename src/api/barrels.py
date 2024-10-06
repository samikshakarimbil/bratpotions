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
    total_greenml = 0
    total_price = 0
    for barrel in barrels_delivered:
        if barrel.potion_type == [0, 1, 0, 0]:
            total_greenml += barrel.ml_per_barrel * barrel.quantity
            total_price += barrel.price * barrel.quantity

    if total_greenml > 0:
        with db.engine.begin() as connection:
            connection.execute(sqlalchemy.text("UPDATE global_inventory \
                                                SET num_green_ml = num_green_ml + :total_greenml, \
                                                gold = gold - :total_price"),
                                                 {"total_greenml": total_greenml, "total_price": total_price})
        print(f"barrels delivered: {barrels_delivered} order_id: {order_id}")

    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)

    bprice = 0
    sku = ""

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory")).mappings()
        result = result.fetchone()
    print(result)
    least_ml = min(result["num_red_ml"], result["num_green_ml"], result["num_blue_ml"])
    print("least:", least_ml)

    for barrel in wholesale_catalog:
        if barrel.potion_type == [1, 0, 0, 0] and least_ml == 0:
            if result["gold"] >= barrel.price:
                bprice = barrel.price
                sku = barrel.sku
        elif barrel.potion_type == [0, 1, 0, 0] and least_ml == 1:
            if result["gold"] >= barrel.price:
                bprice = barrel.price
                sku = barrel.sku
        elif barrel.potion_type == [0, 0, 1, 0] and least_ml == 2:
            if result["gold"] >= barrel.price:
                bprice = barrel.price
                sku = barrel.sku

    print("barrel price: ", bprice)

    if bprice:
        return [
                {
                    "sku": sku,
                    "quantity": 1,
                }
            ]
    
    return[]

