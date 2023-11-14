import requests
import time
import os

PARENT_DIR = os.path.abspath(os.path.join(os.getcwd(), os.pardir))
KEY_PATH = os.path.join(PARENT_DIR, 'certificates', 'key.pem')   

def measure_request_time(url):
    start_time = time.time()
    response = requests.get(url, verify=False)
    end_time = time.time()
    return end_time - start_time, response.status_code

def main():
    for i in range(4):
        url = f'https://localhost:8000/assets/huge{i}.txt'

        time_taken, status_code = measure_request_time(url)
        print(f"Time: {time_taken:.4f} seconds, Status Code: {status_code}")

        time_taken, status_code = measure_request_time(url)
        print(f"Second request: {time_taken:.4f} seconds, Status Code: {status_code}")

if __name__ == "__main__":
    main()
