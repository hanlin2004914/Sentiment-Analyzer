import requests

URL = "http://127.0.0.1:8000/tools/get_wsj_titles"

def get_titles(n=5):
    res = requests.post(URL, json={"limit": n})

    if res.status_code != 200:
        print("Error:", res.text)
        return []

    data = res.json()
    return data.get("titles", [])


if __name__ == "__main__":
    titles = get_titles(5)

    print("\nWSJ Titles:\n")
    for t in titles:
        print("-", t)