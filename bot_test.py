import requests
import base64

def image_to_base64(image_path):
    with open(image_path, 'rb') as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def send_image_to_api(image_path, api_url="http://192.168.1.16:8888/predict/"):
    image_data = image_to_base64(image_path)
    response = requests.post(api_url, json={"base64_str": image_data})

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None

def main():
    test_image_path = "test_img/img1.jpg"
    results = send_image_to_api(test_image_path)

    if results:
        result = results.get("detections", [])
        print(result)

if __name__ == "__main__":
    main()
