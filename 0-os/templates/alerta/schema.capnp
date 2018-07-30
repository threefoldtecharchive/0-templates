@0x9902fdf453c9c070;

struct Schema {
    url @0: Text; # url of the alerta api server: http://{address}/api/
    apikey @1: Text; # apikey to connect to the server
    envname @2: Text; # configure the environment name for the alerta resource
}