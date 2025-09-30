from gemini_ird_pricer import create_app

app = create_app()

if __name__ == "__main__":
    with app.test_client() as client:
        resp = client.get("/")
        print("GET / status:", resp.status_code)
        print("Contains title:", b"Interest Rate Swap Pricer" in resp.data)
