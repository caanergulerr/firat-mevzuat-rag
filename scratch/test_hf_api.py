import requests

model_name = "dbmdz/bert-base-turkish-cased"
api_url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{model_name}"

try:
    response = requests.post(
        api_url,
        json={"inputs": ["Deneme cümlesi.", "İkinci bir cümle."], "options": {"wait_for_model": True}},
        timeout=15
    )
    response.raise_for_status()
    res_data = response.json()
    print("Type:", type(res_data))
    if isinstance(res_data, list):
        print("Length of outer list:", len(res_data))
        print("Type of first element:", type(res_data[0]))
        if isinstance(res_data[0], list):
            print("Shape of first element:", len(res_data[0]), "x", len(res_data[0][0]) if isinstance(res_data[0][0], list) else "scalar")
            # print sample output
            print("First few numbers:", res_data[0][:5])
except Exception as e:
    print("Error:", e)
