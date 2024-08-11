import time, requests, datetime

import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

COURSE_INSTANCE_ID = 155812
SERVER = "https://us.prairielearn.com/pl/api/v1"
ASSESMENT_ID = 2436638

"""
This method is adapted from Prairielearn's public repository.
https://github.com/PrairieLearn/PrairieLearn/blob/63c90a6523a3061743b8653a4cfafc62e0e0dbff/tools/api_download.py#L68
"""
def get_json(endpoint, token):

    url = SERVER + endpoint
    headers = {'Private-Token': token}
    start_time = time.time()
    retry_502_max = 30
    retry_502_i = 0
    while True:
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            break
        elif r.status_code == 502:
            retry_502_i += 1
            if retry_502_i >= retry_502_max:
                raise Exception(f'Maximum number of retries reached on 502 Bad Gateway Error for {url}')
            else:
                print(f'Bad Gateway Error encountered for {url}, retrying in 10 seconds')
                time.sleep(10)
                continue
        else:
            raise Exception(f'Invalid status returned for {url}: {r.status_code}')
        
    end_time = time.time() 

    data = r.json()

    return data

def determine_final_submission_time(submission_log):

    # Iterate through submission_log backward to find the final submission.
    for i in range(len(submission_log) - 1, -1, -1):
        if submission_log[i]['event_name'] == 'Submission':
            return submission_log[i]['date_iso8601']
    return None

def get_final_submission_timestamps(assesment_id, course_instance_path, token):
    name_to_final_submission = {}
    # An assessment_instance is a given student's instance of an assignment
    assessment_instances = get_json(
        f'{course_instance_path}/assessments/{assesment_id}/assessment_instances',
        token)
    for assessment_instance in assessment_instances:
        submission_log = get_json(
            f"{course_instance_path}/assessment_instances/{assessment_instance['assessment_instance_id']}/log",
            token)
        name_to_final_submission[assessment_instance['user_name']] = determine_final_submission_time(submission_log)
    return name_to_final_submission

def main():
    token = input("Please enter your PrairieLearn api token: ")
    course_instance_path = f'/course_instances/{COURSE_INSTANCE_ID}'
    get_final_submission_timestamps(ASSESMENT_ID, course_instance_path, token)


main()

