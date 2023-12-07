import requests
import urllib3

urllib3.disable_warnings()

def send_request(url, method):
    if method == 'PUT':
        response = requests.put(url, verify=False)
    else:
        response = requests.delete(url, verify=False)
    return response.status_code

def main():
    url = "https://localhost:8000"
    try:
        assert(send_request(url, 'PUT') == 405)
        assert(send_request(url, 'DELETE') == 405)
    except AssertionError:
        print("Bug in unsupported method handling")
        return
    print("Tests Passed, both methods get response 405")

if __name__ == "__main__":
    main()
