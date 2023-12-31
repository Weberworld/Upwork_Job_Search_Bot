from bs4 import BeautifulSoup
from selenium.common import TimeoutException
from upwork import UpworkBot


"""
    This file is the entry point of the Upwork Scraping bot.

    Run main.py to execute

    At the end of the script, two files will be created
    1. matched_job_links: A .txt file that contains the link to the job details that meets the requirements
    2. matched_job_details: This is a json file that contains brief details of jobs that meets the requirements.

    You can specified the max number of matching jobs you want in the MAXIMUM_MATCH_JOBS
    If you do not the json file, Please set the NEED_JSON_FORMAT to False
    Increase or decrease the timeout session in the TIMEOUT_AFTER
    Change the value of each key in the REQUIREMENTS to apply filters

"""


MAXIMUM_MATCH_JOBS = 10
TIMEOUT_AFTER = 10
NEED_JSON_FORMAT = True
REQUIREMENTS = {
    "payment_verified": True,
    "exclamation_mark": False,
    "proposal_count": ["Less than 5", "5 to 10"],
    "interviewing_no": 0,
    "invites_count": 0,
    "no_of_job_hires": 0,
    "min_hire_rate": 50,
    "min_amount_spent": 500,
    "min_client_ratings": 3
}

if __name__ == "__main__":

    # Input login credentials
    username = input("What is your Upwork username/email? ")
    password = input("Enter your Upwork password? ")
    secret_ans = None
    secret_question = input("Do you have a secret question answer on Upwork? 'y' or 'n'? ")

    try:
        if secret_question == 'y' or secret_question == "n":
            if secret_question == 'y':
                secret_ans = input("What is the answer to your Upwork secret question? ")

            search_link = input("\nPlease input upwork Job search result link: ")
            print("Just a moment!\nPlease wait ...\n")

            scrap_bot = UpworkBot(search_url=search_link, requirements=REQUIREMENTS, timeout=TIMEOUT_AFTER, need_json_format=NEED_JSON_FORMAT)
            login_successful = scrap_bot.login_into_upwork(username, password, secret_ans)

            if login_successful:
                print("Login Successful!!\n")

                # Get the job results

                print("\nGetting List of jobs ... ")
                print("This will take a moment. Please wait ...\n\n")

                scrap_bot.get_all_jobs_that_meets_requirements(MAXIMUM_MATCH_JOBS)

            else:
                print("Login Failed!!")
        else:
            print("Incorrect option. Type 'y' for yes and 'n' for No")
            print("Run program again!!")
    except TimeoutException:
        print("Time Out. Please check your internet connection")

# End of Main