import requests

payload = {
    "email": "test@example.com",
    "amount": 1000,
    "reference": "test-123",
    "callback_url": "http://127.0.0.1:5000/api/payments/paystack/webhook"
}

headers = {
    "Authorization": "Bearer sk_test_115cae373be5512695afb76982585a5f03971af6",  # your Paystack test secret key
    "Content-Type": "application/json"
}

res = requests.post(
    "https://api.paystack.co/transaction/initialize",
    json=payload,
    headers=headers
)

print(res.status_code)
print(res.json())
