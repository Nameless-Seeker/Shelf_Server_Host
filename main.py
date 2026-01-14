from fastapi import Body, FastAPI, HTTPException, Query, Path
from pydantic import BaseModel, Field
import mysql.connector
import os


def get_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQLHOST"),
        port=int(os.getenv("MYSQLPORT", "3306")),
        user=os.getenv("MYSQLUSER"),
        password=os.getenv("MYSQLPASSWORD"),
        database=os.getenv("MYSQLDATABASE")
    )


class A(BaseModel):
    id: str = Field(..., title="ID of the switch")
    state: int = Field(..., title="state of the switch",
                       description="Where the switch is pressed or not")


app = FastAPI()


class BillRequest(BaseModel):
    user_id: str


@app.post("/bill/{id}", status_code=201)
def bill(id: str, cart_id: str = Query(...)):
    user_id = cart_id
    # SQL Connection
    conn = get_connection()
    con = conn.cursor()

    # Validate ID
    con.execute("select id from a")

    _list = con.fetchall()

    list_of_ids = [i[0] for i in _list]

    if (id not in list_of_ids):
        raise HTTPException(status_code=400, detail="ID not found")

    # ID exists
    con.execute(f"SELECT id,Product_Name,Cost_Price from a where id = %s", (id,))
    res = con.fetchone()

    id = res[0]
    productName = res[1]
    Cost = res[2]

    # con.execute(
    #     "ALTER TABLE bill ADD UNIQUE KEY uq_user_product (user_id, p_id)")

    # Inserting into list of buy items
    sql = """
          INSERT INTO bill (user_id, p_id, p_name, qty, cost)
          VALUES (%s, %s, %s, 1, %s) ON DUPLICATE KEY
          UPDATE
              qty = qty + 1,
              cost = cost +
          VALUES (cost) \
          """

    con.execute(sql, (user_id, id, productName, Cost))

    conn.commit()

    con.execute(
        f"SELECT p_id,p_name,qty,cost FROM bill where user_id = %s", (user_id,))
    _list_of_buy_items = con.fetchall()

    list_of_buy_items = []

    for i in _list_of_buy_items:
        temp_dict = {}

        temp_dict['pID'] = i[0]
        temp_dict['pdtName'] = i[1]
        temp_dict['qty'] = i[2]
        temp_dict['Cost'] = i[3]

        list_of_buy_items.append(temp_dict)

    con.close()
    conn.close()
    return list_of_buy_items


@app.get("/health")
def health():
    return {"status": "OK"}


@app.get("/status")
def status():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * from a")
    rows = cur.fetchall()

    cur.close()
    conn.close()

    ans = {}

    for i in rows:
        temp_dict = {}

        temp_dict['Count'] = i[1]
        temp_dict['Product Name'] = i[2]
        temp_dict["Date and time"] = i[3].ctime()
        temp_dict["Cost per item"] = i[4]
        ans[i[0]] = temp_dict

    return ans


@app.post("/inc")
def inc(value: A):
    conn = get_connection()
    cur = conn.cursor()

    msg = {}

    if value.state == 1:
        cur.execute(
            "UPDATE a SET `count` = `count` + 1 WHERE id = %s", (value.id,))
        msg = {"messege": "Count incremented"}
    else:
        cur.execute(
            "UPDATE a SET `count` = `count` - 1 WHERE id = %s", (value.id,))
        msg = {"messege": "Count decremented"}

    conn.commit()

    # Code for response
    cur.execute("SELECT * FROM a WHERE id = %s", (value.id,))
    data = cur.fetchone()
    pID = data[0]
    pName = data[2]
    new_count = data[1]
    Cost_Price_per_item = data[4]

    msg['Shelf id'] = pID
    msg['PRoduct Name'] = pName
    msg["Total items present"] = new_count
    msg["Cost per item"] = Cost_Price_per_item

    cur.close()
    conn.close()

    return msg


@app.get('/clearBill', status_code=200)
def clearBill():
    conn = get_connection()
    con = conn.cursor()

    # //Clearing the bill table when all products bought
    con.execute("truncate table bill")

    conn.commit()
    con.close()
    conn.close()

    return {"message": "bill table cleared"}


@app.post('/transaction/{cart_id}', status_code=201)
def transaction(cart_id: str = Path(...)):
    user_id = cart_id

    conn = get_connection()
    con = conn.cursor()
    con.execute("""INSERT INTO transaction (products)
                   SELECT JSON_ARRAYAGG(p_id)
                   FROM bill
                   where user_id = %s
                   GROUP BY user_id;
                """, (user_id,))

    conn.commit()
    con.close()
    conn.close()

    return {'status': 'successful'}


@app.delete("/deleteOneCartItems/item/{cart_id}", status_code=200)
def deleteOneItemFromCart(cart_id: str = Path(...), product_id: str = Query(...)):
    conn = get_connection()
    con = conn.cursor()

    con.execute(
        "select qty from bill where user_id = %s and p_id = %s", (cart_id, product_id))
    qty = con.fetchone()[0]

    # If qty is more than one then decrease one product
    if (qty > 1):
        con.execute(
            "update bill set qty = qty-1 where user_id = %s and p_id = %s", (cart_id, product_id))

    else:
        con.execute(
            "delete from bill where user_id = %s and p_id = %s", (cart_id, product_id))

    conn.commit()

    # Returning the updated table
    con.execute(
        f"SELECT p_id,p_name,qty,cost FROM bill where user_id = %s", (cart_id,))
    _list_of_buy_items = con.fetchall()

    list_of_buy_items = []

    for i in _list_of_buy_items:
        temp_dict = {}

        temp_dict['pID'] = i[0]
        temp_dict['pdtName'] = i[1]
        temp_dict['qty'] = i[2]
        temp_dict['Cost'] = i[3]

        list_of_buy_items.append(temp_dict)

    con.close()
    conn.close()
    return list_of_buy_items


@app.delete("/deleteOneCartItems/{cart_id}", status_code=204)
def deleteOneCartItems(cart_id: str = Path(...)):
    conn = get_connection()
    con = conn.cursor()

    con.execute("""DELETE
                   FROM bill
                   where user_id = %s""", (cart_id,))

    conn.commit()
    con.close()
    conn.close()
    return
