import time, requests, datetime

import os.path
import json

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# CS10 Su24 course id
COURSE_INSTANCE_ID = 155812
SERVER = "https://us.prairielearn.com/pl/api/v1"

# The keys of the dictionary are ASSESMENT_IDs.
# The items stored in the tuples are as follows: (spreadsheet_id, subsheet_name, email_column_letter, time_left_column_letter)
ASSESMENT_ID_TO_SPREADSHEET_INFO = {2436638: ("16e6hWK4wWiqetuyJrDvBy4O9Wwp83NR1JptZU1dIIxI", "Final", 'C', 'H')}


# This scope allows for write access.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = "16e6hWK4wWiqetuyJrDvBy4O9Wwp83NR1JptZU1dIIxI"

"""
Allows the user authenticate their google account, allowing the script to modify spreadsheets in their name.
Borrowed from here: https://developers.google.com/sheets/api/quickstart/python
"""
def allow_user_to_authenticate_google_account():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
          "credentials.json", SCOPES
       )
        creds = flow.run_local_server(port=0)
        print("Authentication succesful")
    # Save the credentials for the next run
    with open("token.json", "w") as token:
      token.write(creds.to_json())
    return creds

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
        name_to_final_submission[assessment_instance['user_uid']] = determine_final_submission_time(submission_log)
    return name_to_final_submission

def get_email_to_timestamp(sheet, sid, subsheet_name, email_column_letter, time_left_column_letter):
    emails_request_result = (sheet.values().get(
    spreadsheetId=sid,
    range=f'{subsheet_name}!{email_column_letter}2:{email_column_letter}').execute()
    )
    emails = emails_request_result.get("values", [])

    timestamp_request_result = (sheet.values().get(
     spreadsheetId=sid,
     range=f'{subsheet_name}!{time_left_column_letter}2:{time_left_column_letter}').execute()
     )

    timestamps = timestamp_request_result.get("values", [])

    emails_and_timestamps = zip(emails, timestamps)

    emails_to_timestamps = {pair[0][0]:pair[1][0] for pair in iter(emails_and_timestamps) if pair[1]}

    return emails_to_timestamps

def initialize_sheet_api_instance(creds):
    service = build("sheets", "v4", credentials=creds)
    sheet = service.spreadsheets()
    return sheet

def is_submission_late(pl_time, spreadsheet_time):
    format_data = "%m/%d/%Y %H:%M:%S"
    spreadsheet_time_as_iso = datetime.datetime.strptime(spreadsheet_time, format_data)
    pl_time_as_iso = datetime.datetime.fromisoformat(pl_time)
    spreadsheet_time_with_pl_tz = spreadsheet_time_as_iso.replace(tzinfo=pl_time_as_iso.tzinfo)
    return pl_time_as_iso > spreadsheet_time_with_pl_tz


def get_late_submitter_list_for_given_exam(course_instance_path, sheet, token, assesment_id):
    spreadsheet_id = ASSESMENT_ID_TO_SPREADSHEET_INFO[assesment_id][0]
    subsheet_name = ASSESMENT_ID_TO_SPREADSHEET_INFO[assesment_id][1]
    email_column_letter = ASSESMENT_ID_TO_SPREADSHEET_INFO[assesment_id][2]
    time_left_column_letter = ASSESMENT_ID_TO_SPREADSHEET_INFO[assesment_id][3]

    emails_to_pl_final_submission_timestamps = get_final_submission_timestamps(assesment_id, course_instance_path,
                                                                               token)
    emails_to_gs_timestamps = get_email_to_timestamp(sheet, spreadsheet_id, subsheet_name, email_column_letter,
                                                     time_left_column_letter)
    late_submitters = []
    for email, timestamp in emails_to_gs_timestamps.items():
        if is_submission_late(emails_to_pl_final_submission_timestamps[email], timestamp):
            late_submitters.append(email)
    return late_submitters

def main():
    token = input("Please enter your PrairieLearn api token: ")
    course_instance_path = f'/course_instances/{COURSE_INSTANCE_ID}'
    creds = allow_user_to_authenticate_google_account()
    sheet = initialize_sheet_api_instance(creds)

    exam_to_late_submitter_list = {}

    for assesment_id in ASSESMENT_ID_TO_SPREADSHEET_INFO:
        exam_to_late_submitter_list[assesment_id] = get_late_submitter_list_for_given_exam(course_instance_path, sheet, token, assesment_id)

    print(exam_to_late_submitter_list)

main()
