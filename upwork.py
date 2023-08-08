import json
import math
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common import NoSuchElementException, ElementNotInteractableException, ElementClickInterceptedException, \
    TimeoutException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

UPWORK_BASE_URL = "https://www.upwork.com"
UPWORK_LOGIN_PATH = UPWORK_BASE_URL + "/ab/account-security/login"

chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("start-maximized")
chrome_options.add_argument("disable-infobars")
DRIVER = webdriver.Chrome(options=chrome_options)

MAX_REQUEST_TRIAL = 10  # Max number of times to request a particular page in case of timeout.


class UpworkBot:
    matched_jobs_details = []
    matched_job_links = []
    trial_count = 0

    def __init__(self, search_url: str, requirements: dict, timeout: int, need_json_format: bool):
        self.search_url = search_url
        self.requirements = requirements
        self.timeout = timeout
        self.need_json_format = need_json_format
        self.timeout_msg = "Webpage takes too long to load after".format(self.timeout)

    @staticmethod
    def get_no_of_interviewing_and_invites(job_activity: BeautifulSoup):
        try:
            interviewing_no = int(
                job_activity.select_one('div > ul > li:nth-child(2)').get_text(strip=True).strip("Interviewing:"))
            invites_count = int(
                job_activity.select_one('div > ul > li:nth-child(3)').get_text(strip=True).strip("Invites sent:"))
        except ValueError:
            try:
                interviewing_no = int(
                    job_activity.select_one('div > ul > li:nth-child(3)').get_text(strip=True).strip("Interviewing:"))
                invites_count = int(
                    job_activity.select_one('div > ul > li:nth-child(4)').get_text(strip=True).strip("Invites sent:"))
            except ValueError:
                try:
                    interviewing_no = int(
                        job_activity.select_one('div > ul > li:nth-child(4)').get_text(strip=True).strip("Interviewing:"))
                    invites_count = int(
                        job_activity.select_one('div > ul > li:nth-child(5)').get_text(strip=True).strip("Invites sent:"))
                except AttributeError:
                    interviewing_no, invites_count = None, None  # Job is no longer available
            except AttributeError:
                interviewing_no, invites_count = None, None    #Job is no longer available
        except AttributeError:
            interviewing_no, invites_count = None, None  # Job is no longer available
        return {"interviewing_no": interviewing_no, "invites_count": invites_count}

    @staticmethod
    def get_proposal_count(job_activity) -> str:
        try:
            proposal_count = job_activity.select_one(
                "div > ul > li:nth-child(1) > span:nth-child(2) > span:nth-child(3)").get_text(
                strip=True)
        except AttributeError:
            proposal_count = None  # Job is no longer available
            # print("Job Unavailable")

        return proposal_count

    @staticmethod
    def get_total_hire_count(client_activity) -> int:
        try:
            hired_count = int(
                client_activity.select_one("div > ul > li:nth-child(3) > div").get_text(strip=True).split()[0])
        except (AttributeError, ValueError):
            hired_count = 0
        return hired_count

    @staticmethod
    def get_hire_rate(soup, client_activity, hired_count):
        try:
            hire_rate = int(
                soup.select_one("section.up-card-section.d-lg-none > div > ul > li:nth-child(2) > div").get_text(
                    strip=True).split()[0].strip("%"))
        except AttributeError:
            job_post_str = client_activity.select_one("div > ul > li:nth-child(2) > strong").get_text(strip=True).split()[0]
            try:
                employer_jobs_posted = int(job_post_str)
            except ValueError:
                employer_jobs_posted = int(job_post_str.replace(',', ''))

            hire_rate = math.ceil(float(hired_count / employer_jobs_posted) * 100)

        return hire_rate

    @staticmethod
    def get_employer_ratings(client_activity):

        try:
            ratings = float(
                client_activity.select_one("div.text-muted.rating.mb-20 > span").get_text(strip=True).split()[0])
        except AttributeError:
            ratings = 0

        return ratings

    @staticmethod
    def get_no_hires(job_activity):
        no_of_hires = 0
        try:
            for each in (job_activity.select_one("div > ul")).find_all("li"):
                temp = each.get_text(strip=True).split(":")
                if temp[0] == "Hires":
                    no_of_hires = int(temp[1])
        except AttributeError:
            pass
        return no_of_hires

    @staticmethod
    def get_payment_verification(client_activity):

        try:
            payment_verified = (client_activity.select_one("div.enterprise-payment.mb-10 > div > strong").get_text(
                strip=True)) == "Payment method verified"
        except AttributeError:
            try:
                payment_verified = (client_activity.select_one("div.mb-10 > div > div > span.text-muted").get_text(
                    strip=True)) == "Payment method verified"
            except AttributeError:
                payment_verified = (client_activity.select_one("div.mb-10 > div > div > strong").get_text(
                    strip=True)) == "Payment method verified"
        return payment_verified

    @staticmethod
    def get_total_amount_spent(client_activity):
        try:
            total_spent = client_activity.select_one("div > ul > li:nth-child(3) > strong > span > span").get_text(
                strip=True).strip('$')
        except (AttributeError, ValueError):
            total_spent = "0"

        if 'K' in total_spent:
            total_spent = float(total_spent.strip('K')) * 1000
        elif "M" in total_spent:
            total_spent = float(total_spent.strip("M")) * 1000000
        else:
            total_spent = int(total_spent)
        return total_spent

    @staticmethod
    def get_all_job_posting_links(html_page: str, page_no) -> list:
        """
            Scrapes a given html page and returns links to the detail page of all job search results items
            :param html_page: Weblink to the job search result page
            :param page_no: search list page number from Upwork url
            :return: Returns list of job links in the page
        """
        print("Retrieving all job links for page {0}...".format(page_no))
        print("Checking for requirements matches ...")

        soup = BeautifulSoup(html_page, "lxml")
        all_links = [each.get("href") for each in soup.select(".job-tile-title > a")]
        return all_links

    def get_job_and_client_activity(self, detail_page_html):
        """"
            Get the job activity and client activity html section from the detail page passed
        """
        soup = BeautifulSoup(detail_page_html, 'html.parser')
        job_activity = soup.select_one(
            "div.col-12.cfe-ui-job-details-content > section.up-card-section.row > div.col-lg-6")
        client_activity = soup.select_one("div.cfe-ui-job-about-client")
        exclamation_mark = False
        if client_activity is None:
            return self.get_job_and_client_activity(self.retrieve_job_details())
        try:
            if job_activity.find("h4").get_text(strip=True) != "Activity on this job":
                job_activity = soup.select_one("section.up-card-section.row > div:nth-child(2)")
                preferred_qualifications = (
                    soup.select_one("section.up-card-section.row > div:nth-child(1) > ul.list-unstyled")).find_all("li")
                for each in preferred_qualifications:
                    if each.select_one("span.ml-5 > div.text-danger") is not None:
                        exclamation_mark = True
                        break
        except AttributeError:
            # If it raises an attribute error, it means the page has not loaded the job activity element into the DOM at time of scraping
            # Now we will try to retrieve the whole job details element again
            return self.get_job_and_client_activity(self.retrieve_job_details())
        return {"job_activity": job_activity, "client_activity": client_activity, "exclamation_mark": exclamation_mark}

    def go_to_next_page(self):
        """
            Get the next page link by using a driver to locate the pagination button
            and clicking on the next page link tag.\n
            After the new page has been loaded the current url is then returned
        """
        try:
            next_btn = DRIVER.find_element(By.CSS_SELECTOR,
                                           "ul.up-pagination > li:nth-child(9) > button.up-pagination-item.up-btn.up-btn-link")
            if next_btn.is_enabled():
                next_btn.click()
                time.sleep(self.timeout)
                return True
        except ElementClickInterceptedException:
            pass
        except ElementNotInteractableException:
            pass
        return None

    def login_into_upwork(self, username: str, pswd: str, secret_ans=None):
        """
            Log in an upwork user with the username and password.


        :param username: User's Upwork username or email
        :param pswd: User's  Upwork password
        :param secret_ans: Upwork secret answer
        :return: dict containing two keys (success: bool, error_msg: None if success is True)

        """
        success = False
        if username and pswd:
            print("Logging into Upwork ... ")
            DRIVER.get(UPWORK_LOGIN_PATH)
            try:
                WebDriverWait(DRIVER, self.timeout).until(EC.presence_of_element_located((By.ID, "login_username")))
                username_input = DRIVER.find_element(By.ID, "login_username")
                username_input.send_keys(username)

                login_btn = DRIVER.find_element(By.ID, "login_password_continue")
                login_btn.click()

                time.sleep(5)
                WebDriverWait(DRIVER, self.timeout).until(EC.presence_of_element_located((By.ID, "login_password")))

                password_input = DRIVER.find_element(By.ID, "login_password")
                password_input.send_keys(pswd)

                proceed_btn = DRIVER.find_element(By.ID, "login_control_continue")
                proceed_btn.click()

                print("Verifying Login Credentials ...")
                time.sleep(5)
                try:
                    WebDriverWait(DRIVER, self.timeout).until(EC.presence_of_element_located((By.ID, "login_answer")))
                    ans = DRIVER.find_element(By.ID, "login_answer")
                    ans.send_keys(secret_ans)

                    proceed_button = DRIVER.find_element(By.ID, "login_control_continue")
                    proceed_button.click()
                except TimeoutException:
                    pass
                # To be sure that the user was logged in successful, we check if the current url is not the same as the
                # verification url.
                time.sleep(self.timeout)
                if "https://www.upwork.com/nx/find-work/" in DRIVER.current_url:
                    success, error_msg = True, None
                else:
                    try:
                        WebDriverWait(DRIVER, self.timeout).until(
                            EC.presence_of_element_located((By.ID, "login_answer")))
                        error_msg = "Incorrect Secret Answer"
                    except TimeoutException:
                        if "https://www.upwork.com/nx/find-work/" in DRIVER.current_url:
                            success, error_msg = True, None
                        else:
                            error_msg = "Time Out!. {0} took too long to load after {1}secs".format(DRIVER.current_url,
                                                                                                    self.timeout)
            except NoSuchElementException:
                error_msg = "Invalid password!"
            except ElementNotInteractableException:
                error_msg = "No account was found for {0}\nUsername is Invalid!!".format(username)
            except TimeoutException:
                error_msg = "Time Out!. {0} took too long to load after {1}secs".format(DRIVER.current_url,
                                                                                        self.timeout)
        else:
            error_msg = "Please pass login credentials"

        if error_msg is not None:
            print(error_msg)

        return success

    def retrieve_job_details(self):

        """
            Scrap the current webpage (must be a job detail page) and return the section that contains the details about
            a job.
        :return: html content
        """
        try:
            # Make sure all element has been loaded to the page before taking action
            WebDriverWait(DRIVER, self.timeout).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "job-details-loader")))
            detail_page = DRIVER.find_element(By.CLASS_NAME, "job-details-loader").get_attribute("innerHTML")
        except StaleElementReferenceException:
            time.sleep(5)
            detail_page = DRIVER.find_element(By.CLASS_NAME, "job-details-loader").get_attribute("innerHTML")
        except TimeoutException:
            print("Time Out! Webpage too long to load after {0} secs.".format(self.timeout))
            return None
        except NoSuchElementException:
            print("Unable to load details page")
            return None
        return detail_page

    def get_job_required_details(self, job_url=None) -> dict:
        """
        Get the details of job from the detail page and specify if the following requirements are met.\n
        Requirements:\n\n

        1. Less than 5 proposals or 5-10 proposals
        2. Payment verified
        3. No red exclamation mark
        4. Interviewing: 0
        5. Invites sent: 0
        6. Number of people hired for the job : 0
        7. Employer's total spent: > $1000
        8. Employer's rating: > 4/5

        For employers with a hire rate:
        * Employer's hire rate: > 60%

        For employers without a hire rate:
        * Calculate the number of people hired / total number of jobs posted, and ensure it's greater than 0.6 (60%).

        :param job_url: Link to job details
        :return: Returns a dict that contains information which tells if the details of the job search matches requirement and also the job search details information.
        """

        detail_page_html = self.retrieve_job_details()
        # Check if max number of trials has not been exceeded
        if self.trial_count >= MAX_REQUEST_TRIAL:
            print("Unresponsive job detail page. Please check Connection and Try again")
            raise TimeoutError

        # Reload the scraped details html_page again
        if detail_page_html is None:
            self.trial_count += 1
            return self.get_job_required_details(job_url)

        soup = BeautifulSoup(detail_page_html, 'html.parser')

        job_name = soup.select_one("h1").get_text(strip=True)  # Job name
        job_link = job_url

        activities = self.get_job_and_client_activity(detail_page_html)
        job_activity = activities['job_activity']
        client_activity = activities["client_activity"]

        exclamation_mark = activities['exclamation_mark']

        proposal_count = self.get_proposal_count(job_activity)
        interviewing_count_and_invite_count = self.get_no_of_interviewing_and_invites(job_activity)
        interviewing_no = interviewing_count_and_invite_count['interviewing_no']
        invites_count = interviewing_count_and_invite_count['invites_count']
        hired_count = self.get_no_hires(job_activity)

        payment_verified = self.get_payment_verification(client_activity)
        total_spent = self.get_total_amount_spent(client_activity)
        ratings = self.get_employer_ratings(client_activity)
        hire_rate = self.get_hire_rate(soup, client_activity, self.get_total_hire_count(client_activity))

        match = False

        if (proposal_count in self.requirements['proposal_count']) and (
                payment_verified == self.requirements["payment_verified"]) and \
                (exclamation_mark == self.requirements["exclamation_mark"]) and (
                interviewing_no <= self.requirements['interviewing_no']) and \
                (invites_count <= self.requirements['invites_count']) and (
                hired_count <= self.requirements['no_of_job_hires']) and \
                (hire_rate >= self.requirements['min_hire_rate']) and (
                total_spent >= self.requirements['min_amount_spent']) and \
                (ratings >= self.requirements['min_client_ratings']):
            match = True

        details = {
            "match": match, "job_name": job_name, "job_link": job_link, "proposal_count": proposal_count,
            "payment_verified": payment_verified, "exclamation_mark": exclamation_mark,
            "no_interviewing": interviewing_no, "invites_count": invites_count, "hired_count": hired_count,
            "total_spent": total_spent, "ratings": ratings, "hire_rate": hire_rate
        }
        return details

    def get_all_jobs_that_meets_requirements(self, no_of_jobs: int):

        """
            Return the first 50 jobs posting that matches a set of pre-defined requirements
            :param no_of_jobs: No of matching jobs to be retrieved.
        """

        page_no = 1
        # Navigates to the webpage link given
        try:
            DRIVER.get(self.search_url)
        except TimeoutException:
            print("Webpage too long to load")
            return
        while len(self.matched_job_links) != no_of_jobs:

            all_jobs = DRIVER.find_elements(By.CSS_SELECTOR, ".job-tile-title > .up-n-link")
            page_jobs_links = self.get_all_job_posting_links(DRIVER.page_source, page_no)
            index = 0
            no_page_match = 0

            for each in all_jobs:
                each_job_link = UPWORK_BASE_URL + page_jobs_links[index]
                print(each_job_link)
                try:
                    WebDriverWait(DRIVER, self.timeout).until(EC.element_to_be_clickable(each)).click()
                except ElementClickInterceptedException:
                    DRIVER.execute_script(
                        "arguments[0].click();",
                        WebDriverWait(DRIVER, self.timeout).until(EC.element_to_be_clickable(each))
                    )
                except StaleElementReferenceException:
                    print("The given URL does not seems to be a valid Upwork Job search result URL\n")
                    return []
                try:
                    job_details = self.get_job_required_details(each_job_link)
                    index += 1  # page number
                    if len(self.matched_job_links) == no_of_jobs:
                        break
                    if job_details['match'] and (each_job_link not in self.matched_job_links):  # Avoid duplicates
                        self.matched_jobs_details.append(job_details)
                        self.matched_job_links.append(each_job_link)
                        no_page_match += 1
                        self.save_job_results()

                    DRIVER.back()  # Go back to the previous page
                except TimeoutError:
                    return []

            if self.go_to_next_page() is None:
                break
            page_no += 1
            print("Found {0} jobs that meets requirements\n".format(no_page_match))
        print("\n\nScrapping completed!!")

        print("No of matched jobs: {0}\n".format(len(self.matched_job_links)))
        if len(self.matched_job_links) == 0:
            print("Unable to find jobs that meets requirements")
        else:
            print("Links to {0} matched jobs has been saved to match_jobs.txt".format(len(self.matched_job_links)))
            print("Details of matched jobs has been saved to match_jobs.json")
        return

    def save_job_results(self):
        self.save_txt_format()
        if self.need_json_format:
            self.save_json_format()

    def save_txt_format(self):
        with open("matched_jobs.txt", mode="w") as fp:
            for each in self.matched_job_links:
                fp.write(each)
                fp.write("\n")

    def save_json_format(self):
        with open("matched_jobs.json", mode="w") as fp:
            json.dump(self.matched_jobs_details, fp, indent=4)
            fp.write('\n')