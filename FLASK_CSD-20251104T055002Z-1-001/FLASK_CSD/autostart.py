import time
import requests

processes = ["term1","term2","term3","term4","term5"]

for p in processes:
    requests.get(f"http://127.0.0.1:5000/start/{p}")
    time.sleep(5)  # 5s delay
