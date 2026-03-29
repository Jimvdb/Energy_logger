from pymodbus.client import ModbusTcpClient

client = ModbusTcpClient("192.168.1.100", port=502)

if client.connect():
    print("Connectie OK")
else:
    print("Connectie mislukt")

client.close()