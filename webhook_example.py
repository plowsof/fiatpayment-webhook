# The event notification subscription signature key (sigKey) defined in dev portal for app.
SIG_KEY = b'hunter2hunter2123';
NOTIFICATION_URL = 'https://getwishlisted.xyz/webhook'

@app.post("/webhook")
async def get_body(request: Request,status_code=200):
    global NOTIFICATION_URL, SIG_KEY, client
    body = await request.body()
    length = int(request.headers['content-length'])
    square_signature = request.headers['x-square-signature']

    #print(length)
    #print(square_signature)

    url_request_bytes = NOTIFICATION_URL.encode('utf-8') + body

    # create hmac signature
    hmac_code = hmac.new(SIG_KEY, msg=None, digestmod='sha1')
    hmac_code.update(url_request_bytes)
    hash = hmac_code.digest()

    # compare to square signature from header
    if base64.b64encode(hash) != square_signature.encode('utf-8'):
        print("sig dont match")
        return ''
    data = json.loads(body.decode('utf-8'))
    #pprint.pprint(data[""]
    #get order id
    #get information (email / wish id) using order id
   
    print("Hello world")
    if (data["data"]["object"]["payment"]["status"]) != "COMPLETED":
        return ''

    order_id = data["data"]["object"]["payment"]["order_id"]
    #refid
    result = client.orders.retrieve_order(
      order_id = order_id
    )
    body = result.body
    #pprint.pprint(body)
    ref_id = body["order"]["reference_id"]
    #amount
    usd = data["data"]["object"]["payment"]["amount_money"]["amount"] / 100
    #confirm we've never seen this order_id before becaus ei noticed duplicate
    #if order id not in db - return - or add it and continue  
    con = sqlite3.connect('card_orders.db')
    cur = con.cursor()
    create_orders_table = """ CREATE TABLE IF NOT EXISTS orders (
                                usd integer,
                                ref_id text PRIMARY KEY,
                                email text,
                                fname text,
                                lname text,
                                zip text,
                                street text,
                                cc text,
                                order_id text,
                                date_time text
                            ); """

    cur.execute(create_orders_table)
    cur.execute('SELECT * FROM orders WHERE ref_id = ?',[ref_id])
    rows = cur.fetchall()
    print(f"[DEBUG] row data: {rows[0][8]}\n[DEBUG] != {order_id}")
    if rows[0][8] != order_id:
        print("We got monEY")
        sql = ''' UPDATE orders
          SET order_id = ?,
          usd = ?
          WHERE ref_id = ?'''   
        cur.execute(sql, (order_id,usd,ref_id))
        db_usd = usd 
        db_ref_id = rows[0][1]
        db_email = rows[0][2]
        db_fname = rows[0][3]
        db_lname = rows[0][4]
        db_zip = rows[0][5]
        db_street = rows[0][6]
        db_cc = rows[0][7]
        db_order_id = order_id
        db_date_time = rows[0][8]
        wishlist_usd_notify(db_usd,db_ref_id,db_email,db_fname,db_lname,db_zip,db_street,db_cc,db_order_id,db_date_time)
    con.commit()

    
@app.post("/flask/fiat_donate")
def square_checkout(fiatDonate: FiatDonate):
    global LOCATION_ID
    item_dict = fiatDonate.dict()
    #pprint.pprint(item_dict)
    '''
    send_this = {
    "fname": data[0].value,
    "lname": data[1].value,
    "street": data[2].value,
    "zip": data[3].value,
    "email": data[4].value,
    "id": id,
    "usd": usd
    }
    '''
    wish_id = item_dict["id"]
    usd_amount = item_dict["usd"]
    email = item_dict["email"]
    fname = item_dict["fname"]
    lname = item_dict["lname"]
    _zip = item_dict["zip"]
    street = item_dict["street"]
    cc = "TBD"
    order_id = "TBD"
    comment_name="Anonymous"
    comment="Test comment"
    ref_id = str(uuid.uuid4())[0:27] + "@" + wish_id
    con = sqlite3.connect('card_orders.db')
    cur = con.cursor()
    create_orders_table = """ CREATE TABLE IF NOT EXISTS orders (
                                usd integer,
                                ref_id text PRIMARY KEY,
                                email text,
                                fname text,
                                lname text,
                                zip text,
                                street text,
                                cc text,
                                order_id text,
                                date_time text,
                                comment text,
                                comment_name text,
                                amount_expected default 0 not null
                            ); """

    cur.execute(create_orders_table)
    con.commit()


    result = client.checkout.create_checkout(
    location_id = LOCATION_ID,
    body = {
    "idempotency_key": str(uuid.uuid4()),
    "order": {
      "order": {
                    "location_id": LOCATION_ID,
                    "reference_id": ref_id,
                    "customer_id": str(uuid.uuid4()),
                    "line_items": [
                                      {
                                        "uid": str(uuid.uuid4()),
                                        "name": "MAGIC Donation",
                                        "quantity": "1",
                                        "base_price_money": {
                                          "amount": int(usd_amount),
                                          "currency": "USD"
                                        }
                                      }
                                ],
                    "state": "OPEN"
            },
      "idempotency_key": str(uuid.uuid4())
    },
    "pre_populate_buyer_email": email,
    #"redirect_url" : 'https://getwishlisted.xyz/flask/checkout',
    "merchant_support_email" : "support@magicgrants.org"
    });

    if result.is_success():
        #pprint.pprint(result.body)
        body = result.body
        sql = ''' INSERT INTO orders (usd,ref_id,email,fname,lname,zip,street,cc,order_id,date_time,comment,comment_name)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?)'''
        print(f"[DEBUG]: inserting ref_id as: {ref_id}")
        cur.execute(sql, (0,ref_id,email,fname,lname,_zip,street,cc,order_id,str(datetime.now()),comment,comment_name))
        con.commit()
        return body["checkout"]["checkout_page_url"]
    elif result.is_error():
        print(result.errors)
    return '', 200

