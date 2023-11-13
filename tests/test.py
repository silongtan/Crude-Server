import requests
import concurrent.futures
from concurrent.futures import ProcessPoolExecutor

def send_request(url):
    # Replace with the actual logic for sending a request
    response = requests.get(url, verify=False)
    return response.status_code

def main():
    url = "https://localhost:8000"  # Replace with your server's URL
    requests_count = 7

    with ProcessPoolExecutor() as executor:
        futures = [executor.submit(send_request, url) for _ in range(requests_count)]

        for future in concurrent.futures.as_completed(futures):
            status= future.result()
            print(f"Request completed with status {status}")

if __name__ == "__main__":
    main()
