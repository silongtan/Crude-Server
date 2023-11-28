import requests
import urllib3
import concurrent.futures
from concurrent.futures import ProcessPoolExecutor

response_cnt = dict()
response_cnt[200] = 0
response_cnt[429] = 0

urllib3.disable_warnings()

def send_request(url):
    # Replace with the actual logic for sending a request
    response = requests.get(url, verify=False)
    return response.status_code

def main():
    url = "https://localhost:8000"  # Replace with your server's URL
    requests_count = 10

    with ProcessPoolExecutor() as executor:
        futures = [executor.submit(send_request, url) for _ in range(requests_count)]

        for future in concurrent.futures.as_completed(futures):
            status = future.result()
            try:
                response_cnt[status] += 1
            except KeyError:
                print("Unexpected status code!")
                return

        try:
            assert(response_cnt[200] == 7)
            assert(response_cnt[429] == 3)
        except AssertionError:
            print("Bug in rate limit concurrency control!")
            return
        print("Tests passed!")

if __name__ == "__main__":
    main()
