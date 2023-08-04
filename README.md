        ﻿An Automated Scraping bot. It automatically logs a user in and scraps a result of a given upwork job search link. 
        The Bot will continue running and navigating to the next page untill a given number is reached or the bot has scraped to the last page
        At the end of the program, The bot will store the the links to the list of jobs that meets the following requirements

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

        Run main.py to begin the app
        You can set the number of jobs you want to scrap in the MAXIMUM_MATCH_JOBS in main.py
        Set NEED_JSON_FORMAT to False if you do not need the json details of the matched jobs in main.py
