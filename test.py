import requests

url = "https://dev.azure.com/{org}/{project}/_apis/wit/wiql?api-version=7.0"

headers = {
    "Content-Type": "application/json",
    "Authorization": "Basic <base64_token>"
}

body = {
    "query": "SELECT [System.Id], [System.Title] FROM WorkItems WHERE [System.TeamProject] = 'AgentIQ' ORDER BY [System.CreatedDate] DESC"
}

response = requests.post(url, json=body, headers=headers)
print(response.status_code)
print(response.text)  # Xem chi tiết lỗi