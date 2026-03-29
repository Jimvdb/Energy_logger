import csv
import os
import time
from datetime import datetime
from pymodbus.client import ModbusTcpClient

CSV_FILE = "em24_meting.csv"
POLL_INTERVAL = 0.5  # seconden
MODBUS_PORT = 502
SLAVE_ID = 1

# Voeg hier 1 of meerdere meters toe
METERS = [
    {"name": "em24_100", "ip": "192.168.1.100"},
#    {"name": "em24_124", "ip": "192.168.1.124"},
]

HEADER = [
    "timestamp",
    "meter",
    "ip",
    "voltage_l1",
    "voltage_l2",
    "voltage_l3",
    "current_l1",
    "current_l2",
    "current_l3",
    "frequency",
    "watt_L1",
    "watt_L2",
    "watt_L3",
    "va_L1",
    "va_L2",
    "va_L3",
]

# Register mapping volgens EM24 E1 protocol
REG_V_L1N = 0x0000  # 2 words, INT32, Volt*10
REG_V_L2N = 0x0002  # 2 words, INT32, Volt*10
REG_V_L3N = 0x0004  # 2 words, INT32, Volt*10

REG_A_L1  = 0x000C  # 2 words, INT32, Ampere*1000
REG_A_L2  = 0x000E  # 2 words, INT32, Ampere*1000
REG_A_L3  = 0x0010  # 2 words, INT32, Ampere*1000

REG_W_L1  = 0x0012  # 2 words, INT32, Watt * 10
REG_W_L2  = 0x0014  # 2 words, INT32, Watt * 10
REG_W_L3  = 0x0016  # 2 words, INT32, Watt * 10

REG_VA_L1  = 0x0018  # 2 words, INT32, VA * 10
REG_VA_L2  = 0x001A  # 2 words, INT32, VA * 10
REG_VA_L3  = 0x001C  # 2 words, INT32, VA * 10

REG_HZ    = 0x0033  # 1 word, UINT16, Hz*10

def init_csv(file_path: str) -> None:
    if not os.path.exists(file_path):
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(HEADER)

def append_csv_row(file_path: str, row: list) -> None:
    with open(file_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(row)

def to_signed_32(high_word: int, low_word: int) -> int:
    value = (high_word << 16) | low_word
    if value & 0x80000000:
        value -= 0x100000000
    return value

def read_int32(client: ModbusTcpClient, address: int, slave_id: int = 1) -> int:
    rr = client.read_holding_registers(address=address, count=2, device_id=slave_id)
    if rr.isError():
        raise RuntimeError(f"Modbus fout op register {hex(address)}: {rr}")

    # EM24 gebruikt bij INT32 woordvolgorde: LSW -> MSW
    low_word = rr.registers[0]
    high_word = rr.registers[1]

    return to_signed_32(high_word, low_word)

def read_uint16(client: ModbusTcpClient, address: int, slave_id: int = 1) -> int:
    rr = client.read_holding_registers(address=address, count=1, device_id=slave_id)
    if rr.isError():
        raise RuntimeError(f"Modbus fout op register {hex(address)}: {rr}")
    return rr.registers[0]

def read_meter(ip: str, name: str, slave_id: int = 1) -> dict:
    client = ModbusTcpClient(ip, port=MODBUS_PORT, timeout=2)

    try:
        if not client.connect():
            raise RuntimeError(f"Geen verbinding met {name} op {ip}:{MODBUS_PORT}")

        # Spanningen
        v1_raw = read_int32(client, REG_V_L1N, slave_id)
        v2_raw = read_int32(client, REG_V_L2N, slave_id)
        v3_raw = read_int32(client, REG_V_L3N, slave_id)

        # Stromen
        a1_raw = read_int32(client, REG_A_L1, slave_id)
        a2_raw = read_int32(client, REG_A_L2, slave_id)
        a3_raw = read_int32(client, REG_A_L3, slave_id)

        # Frequentie
        hz_raw = read_uint16(client, REG_HZ, slave_id)

        # Watt
        w1_raw = read_int32(client, REG_W_L1, slave_id)
        w2_raw = read_int32(client, REG_W_L2, slave_id)
        w3_raw = read_int32(client, REG_W_L3, slave_id)

        # VA
        va1_raw = read_int32(client, REG_VA_L1, slave_id)
        va2_raw = read_int32(client, REG_VA_L2, slave_id)
        va3_raw = read_int32(client, REG_VA_L3, slave_id)

        return {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-4],
            "meter": name,
            "ip": ip,
            "voltage_l1": v1_raw / 10.0,
            "voltage_l2": v2_raw / 10.0,
            "voltage_l3": v3_raw / 10.0,
            "current_l1": a1_raw / 1000.0,
            "current_l2": a2_raw / 1000.0,
            "current_l3": a3_raw / 1000.0,
            "frequency": hz_raw / 10.0,
            "watt_L1": w1_raw / 10.0,
            "watt_L2": w2_raw / 10.0,
            "watt_L3": w3_raw / 10.0,
            "va_L1": va1_raw / 10.0,
            "va_L2": va2_raw / 10.0,
            "va_L3": va3_raw / 10.0,
        }

    finally:
        client.close()

def main() -> None:
    init_csv(CSV_FILE)
    print(f"Logging gestart naar {CSV_FILE}")

    try:
        while True:
            cycle_start = time.time()

            for meter in METERS:
                try:
                    data = read_meter(ip=meter["ip"], name=meter["name"], slave_id=SLAVE_ID)

                    row = [
                        data["timestamp"],
                        data["meter"],
                        data["ip"],
                        data["voltage_l1"],
                        data["voltage_l2"],
                        data["voltage_l3"],
                        data["current_l1"],
                        data["current_l2"],
                        data["current_l3"],
                        data["frequency"],
                        data["watt_L1"],
                        data["watt_L2"],
                        data["watt_L3"],
                        data["va_L1"],
                        data["va_L2"],
                        data["va_L3"],
                    ]

                    append_csv_row(CSV_FILE, row)
                    print(row)

                except Exception as e:
                    print(f"Fout bij {meter['name']} ({meter['ip']}): {e}")

            elapsed = time.time() - cycle_start
            sleep_time = max(0, POLL_INTERVAL - elapsed)
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("Logging gestopt.")

if __name__ == "__main__":
    main()