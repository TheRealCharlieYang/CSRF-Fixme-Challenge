#!/usr/bin/env python3

import unittest
import subprocess
from subprocess import check_output
import requests
from time import sleep
from os import path
import zoneinfo
import random
import string
import re
from bs4 import BeautifulSoup
from gradescope_utils.autograder_utils.decorators import weight, number
import sys

if path.exists("/autograder"):
    AG = "/autograder"
else:
    AG = "."

# DEsired tests:
# /app/new_course  (HTML form/view to submit to createPost) PROVIDED
# /app/new_lecture (HTML form/view to submit to createComment) PROVIDED
# /app/dumpUploads   !!

# /app/createPost   (API endpoint for  new_course)
# /app/createComment  (API endpoint for  new_lecture)
# /app/DumpFeed      (diagnostic endpoint)
# TESTS FOR HTTP  200 or 201 response...  (4)
# TEST that row is actually added with valid input  (3)
# three tests with invalid input, something essential not defined (3)



CDT = zoneinfo.ZoneInfo("America/Chicago")
admin_data = {
                "email": "autograder_test@test.org",
                "is_admin": "1",
                "user_name": "Autograder Admin",
                "password": "Password123"
                }
user_data = {
                "email": "user_test@test.org",
                "is_admin": "0",
                "user_name": "Tester Student",
                "password": "Password123"
                }



class TestDjangoCSRFAaargh(unittest.TestCase):
    '''Test functionality of cloudysky API'''


    def get_csrf_login_token(self, session=None):
        if session is None:
            session = requests.Session()
        response0 = session.get("http://localhost:8000/accounts/login/")
        csrf = session.cookies.get("csrftoken")
        if csrf:
            csrfdata = csrf
        else:
            print("ERROR: Can't find csrf token in accounts/login/ page")
            csrfdata = "BOGUSDATA"
        self.csrfdata = csrfdata
        self.loginheaders = {"X-CSRFToken": csrfdata, "Referer":
                "http://localhost:8000/accounts/login/"}
        return session, csrfdata   # session


    @classmethod
    def setUpClass(self):
        '''This class logs in as an admin, and sets
        self.session  to have the necessary cookies to convince the
        server that we're still logged in.
        '''
        self.DEADSERVER = False
        print("starting server")
        p = subprocess.Popen([sys.executable, 'manage.py',
                              'runserver'],
                             close_fds=True)
        # Make sure server is still running in background, or error
        sleep(2)
        if p.returncode is None:
            self.SERVER = p
        else:
            self.DEADSERVER = True
            self.deadserver_error = p.communicate()

        def login(data):
            # Try to create user, but don't fail if user already exists
            response = requests.post("http://localhost:8000/app/createUser",
                                     data=data,
                                     )
            print("CreateUser status", response.status_code)
            # User creation may fail if user already exists, that's OK
            
            session, csrfdata = self.get_csrf_login_token(self)
            logindata = {"username": data["user_name"],
                     "password": data["password"],
                     "csrfmiddlewaretoken": csrfdata}
            loginheaders = {"X-CSRFToken": csrfdata, "Referer":
                            "http://localhost:8000/accounts/login/"}
            response1 = session.post("http://localhost:8000/accounts/login/",
                        data=logindata,
                        headers=loginheaders)
            print("LOGINDATA", logindata)
            print("LOGINHEADERS", loginheaders)
            print("LOGINCODE", response1.status_code)
            print("LOGINRESPNSE", response1.text)
            if "Please enter a correct username" in response1.text:
                print("Oh, this is bad, login failed")
            return session, loginheaders, csrfdata
#       Now we can use self.session  as a logged-in requests object.
        self.session_admin, self.headers_admin, self.csrfdata_admin = login(admin_data)
        self.session_user, self.headers_user, self.csrfdata_user = login(user_data)


    @classmethod
    def tearDownClass(self):
        self.SERVER.terminate()

    def get_csrf_token_for_authenticated_user(self, session):
        """Get a fresh CSRF token for an authenticated user session."""
        # After login, we need to get a fresh CSRF token
        # We can get this from any page that includes the CSRF token
        response = session.get("http://localhost:8000/app/new")
        csrf = session.cookies.get("csrftoken")
        if csrf:
            return csrf
        else:
            # Fallback: try to extract from page content
            csrf_match = re.search(r'csrfmiddlewaretoken["\s]*value="([^"]*)"', response.text)
            if csrf_match:
                return csrf_match.group(1)
            else:
                print("ERROR: Can't find fresh csrf token for authenticated user")
                return "BOGUSDATA"

    def test_create_post_admin_success(self):
        '''Check server responds with success to http://localhost:8000/app/createPost'''
        data = {'title': "Fuzzy bunnies are great",  "content": "I think so" }
        session = self.session_admin
        
        # Get a fresh CSRF token for authenticated requests
        fresh_csrf = self.get_csrf_token_for_authenticated_user(session)
        
        # Include CSRF token in the POST data
        data['csrfmiddlewaretoken'] = fresh_csrf
        
        # Also include it in headers
        headers = {"X-CSRFToken": fresh_csrf, "Referer": "http://localhost:8000/app/new"}
        
        request = session.post(
            "http://localhost:8000/app/createPost",
            data=data, headers=headers)
        self.assertLess(request.status_code, 203,  # 200 or 201 ok
            "Server returns error for POST to " +
            "http://localhost:8000/app/createPost " +
            "Data:{}".format(data) + 
            "Content:{}".format(request.text)+
            "Headers:{}".format(headers)
            )

    @weight(0.5)
    @number("10.1")
    def test_create_post_notloggedin(self):
        '''Check server responds with error for unauthenticated POST to http://localhost:8000/app/createPost'''
        data = {'title': "I like fuzzy bunnies 10.0",  "content": "I like fuzzy bunnies.  Do you?" }
        session, csrf = self.get_csrf_login_token()  # not logged in
        
        # Include CSRF token in the POST data for proper CSRF handling
        data['csrfmiddlewaretoken'] = csrf
        headers = {"X-CSRFToken": csrf, "Referer": "http://localhost:8000/accounts/login/"}
        
        request = session.post(
            "http://localhost:8000/app/createPost",
            data=data, headers=headers)  # not logged in but with proper CSRF
        self.assertEqual(request.status_code, 401,  # unauthorized
            "Server should return 401 for unauthenticated POST to " +
            "http://localhost:8000/app/createPost " +
            "Data:{}".format(data)
#           "Content:{}".format(request.text)
            )

