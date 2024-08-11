import time, requests, datetime

COURSE_INSTANCE_ID = 155812
SERVER = "https://us.prairielearn.com/pl/api/v1"
ASSESMENT_ID = 2436638

"""
This method is adapted from Prairielearn's public repository.
https://github.com/PrairieLearn/PrairieLearn/blob/63c90a6523a3061743b8653a4cfafc62e0e0dbff/tools/api_download.py#L68
"""
def get_and_return_json(endpoint, token):

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
    #print(f'successfully downloaded {r.headers["content-length"]} bytes in {end_time - start_time} seconds')

    data = r.json()

    return data

def main():
    token = input("Please enter your PrairieLearn api token: ")
    course_instance_path = f'/course_instances/{COURSE_INSTANCE_ID}'

    assessment_instances = get_and_return_json(
                f'{course_instance_path}/assessments/{ASSESMENT_ID}/assessment_instances', 
                token)

main()
