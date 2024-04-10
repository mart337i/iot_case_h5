from fastapi import FastAPI, Depends
from fastapi_mqtt import FastMQTT, MQTTConfig
from fastapi.responses import HTMLResponse
import jsonpickle
from ipaddress import IPv4Address
from sqlmodel import Session,SQLModel

from models.monitoring import Alarm,Device,Sensor,Employe,KeyFob,EntryLog,ValueType,Reading

from database import engine
import logging

#Add the base logging config 
logging.basicConfig(filename='/home/sysadmin/code/iot_case_h5/app/logs/application.log',  # log to a file named 'app.log'
                    filemode='a',  # append to the log file if it exists, otherwise create it
                    level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

#get the logger with the newly set config
_logger = logging.getLogger(__name__)

#Application 
app = FastAPI(root_path="/api",docs_url="/docs", redoc_url="/redoc")

#Database Orm create engine
SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


class Nmap(SQLModel):
    host: IPv4Address
    portRange: str

    class Config:
        json_schema_extra = {
            "example" : {
                "host": "10.0.2.15",
                 "portRange": "22-80",
                 "description": "Scan the port from 22 to 80 of the ip address 10.0.2.15"
            }
        }


# ------------------------------------------------------------ HTTP

@app.get("/api",response_class=HTMLResponse)
async def entry():
    return """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Greenhouse API</title>
                <!-- Include Bootstrap CSS from CDN -->
                <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
            </head>
            <body class="bg-light">
                <div class="container py-5">
                    <h1 class="display-4 text-center mb-3">Welcome to the Greenhouse Temperature and Humidity API</h1>
                    <p class="lead text-center mb-5">Use the links below to navigate to the API documentation:</p>
                    <div class="row">
                        <div class="col-md-6 text-center mb-3">
                            <a href="/api/docs" class="btn btn-primary btn-lg">Swagger UI Documentation</a>
                        </div>
                        <div class="col-md-6 text-center mb-3">
                            <a href="/api/redoc" class="btn btn-secondary btn-lg">ReDoc Documentation</a>
                        </div>
                    </div>
                </div>
                <!-- jQuery first, then Popper.js, then Bootstrap JS -->
                <script src="https://code.jquery.com/jquery-3.5.1.slim.min.js"></script>
                <script src="https://cdn.jsdelivr.net/npm/@popperjs/core@2.9.2/dist/umd/popper.min.js"></script>
                <script src="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/js/bootstrap.min.js"></script>
            </body>
            </html>

    """


# ------------------------------------------------------------ MQTT

mqtt_config = MQTTConfig()

mqtt = FastMQTT(config=mqtt_config)

mqtt.init_app(app)

@mqtt.on_connect()
def connect(client, flags, rc, properties):
    mqtt.client.subscribe("/mqtt") # subscribing mqtt topic wildcard- multi-level
    print("connected: ", client, flags, rc, properties)

@mqtt.on_message()
async def message(client, topic, payload, qos, properties):
    print("received message: ", topic, payload, qos, properties)
    return 0 


@mqtt.on_disconnect()
def disconnect(client, packet, exc=None):
    print("Disconnected")

@mqtt.on_subscribe()
def subscribe(client, mid, qos, properties):
    print("subscribed", client, mid, qos, properties)

@app.get("/")
async def func():
    mqtt.client.publish("/mqtt", "Hello from fastApi") 
    return {"result": True, "message": "Published"}

@app.post("/scan/{host}")
async def scan_host_port(nmap_details : Nmap):
    results = {"got_val" : nmap_details}
    print(type(nmap_details))
    mqtt.client.publish("/mqtt/fromModel/nmap", jsonpickle.encode(nmap_details)) 
    return results
