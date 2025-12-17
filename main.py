from fastapi import FastAPI, HTTPException
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

@app.post("/bill/{id}",status_code=201)
def bill(id: str):
    #SQL Connection
    conn = get_connection()
    con = conn.cursor()

    #Validate ID
    con.execute("select id from a")

    _list = con.fetchall()
    
    list_of_ids = [i[0] for i in _list]

    if(id not in list_of_ids):
        raise HTTPException(status_code=400,detail="ID not found")


    #ID exists
    con.execute(f"SELECT id,Product_Name,Cost from a where id = {id}")
    res = con.fetchone()
    
    id = res[0]
    productName = res[1]
    cost = res[2]

    #Inserting into list of buy items
    con.execute(f"INSERT into bill (pID,pdtName,qty,cost) values({id},{productName},1,{cost}) on duplicate key update qty = qty + 1,cost = cost+{cost}")
    conn.commit()

    con.execute("SELECT * FROM bill")
    _list_of_buy_items = con.fetchall()

    list_of_buy_items = {}

    for i in _list_of_buy_items:
        temp_dict = {}

        temp_dict['pdtName'] = i[1]
        temp_dict['qty'] = i[2]
        temp_dict['cost'] = i[3]

        list_of_buy_items[i[0]] = temp_dict

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

    # check id exists
    cur.execute("SELECT * FROM a")
    _data = cur.fetchall()

    data = [i[0] for i in _data]

    msg = {}

    if value.id not in data:
        cur.close()
        conn.close()
        raise HTTPException(status_code=400, detail="ID not found")

    if value.state == 1:
        cur.execute(f"UPDATE a SET count = count + 1 WHERE id = {value.id}")
        msg = {"messege":"Count incremented"}
    else:
        cur.execute(f"UPDATE a SET count = count - 1 WHERE id = {value.id}")
        msg = {"messege":"Count decremented"}

    conn.commit()

    #Code for response
    cur.execute(f"SELECT * FROM a WHERE id = {value.id}")
    data = cur.fetchone()
    pID = data[0]
    pName = data[2]
    new_count = data[1]
    cost_per_item = data[4]
    
    msg['Shelf id'] = pID
    msg['PRoduct Name'] = pName
    msg["Total items present"] = new_count
    msg["Cost per item"] = cost_per_item

    cur.close()
    conn.close()

    return msg

# #For billing structure
# @app.post()