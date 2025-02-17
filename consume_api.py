import requests
import json

# Fetch the latest Stack Overflow questions sorted by recent activity
response = requests.get('https://api.stackexchange.com/2.3/questions?order=desc&sort=activity&site=stackoverflow')

for data in response.json()['items']:
    if(data['answer_count'] == 0):
        # If the question has no answers, print the title and link
        print(data['title'])
        print(data['link'])
        print()
    else:
        # Skip questions that already have answers
        print("skipped")
    print()

