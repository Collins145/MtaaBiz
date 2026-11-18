STEPS FOR SETTING UP DJANGO PROJECT








1 APP CONFIGURATION
    Go to settings.py & configure your in INSTALLED APPS by parsing your app name

2 ENSURING BOTH PROJECT & APPS FOLDER HAVE THE  URLS FILE
    Copy & Paste the urls.py file from projects folder (MtaaBiz sub directory) to app folder (myapp sub directory).
    Configure the urls.py file in the project folder by adding the new & copied urls.py file in app folder.

N/B: For django to identify, we have to configure the new urls.py folder

3 CREATION OF FOLDERS AT THE ROOT/MAIN DIRECTORY OF THE PROJECT
    Create the following Folders;
    * templates folder - contains ALL HTML templates for your project.
    *static folder - contains ALL images, css & js.
    *
N/B: MAKE SURE ALL NEW DIRECTORIES CREATED ARE CONFIGURED AT SETTINGS.PY FILE.


    WHEN USING BOOTSTRAP TEMPLATE
* Download the template to be used inside the project & extract the zipped folder.
* Copy & Paste the folders required inside the differnet folders of your project.
    Copy the assets folders (css, images, js, vendor & scss folders) into the static folder.
    Copy ALL the HTML files into the templates sub-directory/sub-folder of your project.


    WHEN RENDERING THE PAGES OF YOUR WEBSITE
Create functions that renders and returns the different pages of the website inside views.py
   For example; Use  def index(request):
                     return render(request, 'index.html') to return & render the index page on your website.

Create the different links in the urls.py of your app folder.


SENDING INFORMATION TO THE DATABASE
Ways of Sending /  Submitting info to the DB;
    i Using forms (FRONTEND)
        *Ensure the form tag has a POST method for posting info to the DB.
        *Parse a CSRF token for implementing security & user input (immediatetly below the form tag ).
        *For ANY value provided as an in input the form, it has to be stored in a variable using a name attribute.
        *The button sending information to the DB has to be set with the type Submit.
    
    ii Models (BACKEND)
        *Create the different models using;
            python manage.py makemigrations
            python manage.py migrate

N/B: After defining the different models in models.py file of the apps folder, then run the two above commands to create the models/tables storing the user input from the form.

    Types of Fields in a Models (Django)
        1 IntegerField
        2 CharField
        3 TextField
        4 EmailField
        5 DateField

Register the model at admin.py
    Import everything from the file in models.py 

N/B: Django uses the MVT Architecture
        M - Model
        V - View
        T - Template
To link the Form (Frontend) to the Model (Backend), go to the views.py
    Use the function def index(request)
                        return render(request, 'index.html')

IMPLEMENTING CRUD OPERATIONS
1 C - Create ()
2 R - Read (Fetches everything saved)
3 U - Update ()
4 D - Delete ()


DELETING OPERATION
Delete

N/B: For delete & Edit operations, we MUST use an id when writing a function for deleting.


GOOGLE OAUTH SIGN-IN
1. Create a Google OAuth 2.0 Web application client in Google Cloud Console.
2. Add this authorized redirect URI for local development:
       http://127.0.0.1:8000/accounts/google/login/callback/
   Add the equivalent HTTPS callback URI for each production domain.
3. Set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET in the environment
   where Django runs. Do not store either value in source code.
4. On Windows PowerShell, set them before starting Django:
       $env:GOOGLE_OAUTH_CLIENT_ID = "your-client-id"
       $env:GOOGLE_OAUTH_CLIENT_SECRET = "your-client-secret"
       .\mtaa\Scripts\python.exe manage.py migrate
       .\mtaa\Scripts\python.exe manage.py runserver

The Google sign-in controls are disabled until both environment variables are
present. Users can connect or disconnect Google from Account settings. Google
verified-email sign-in can match and connect an existing MtaaBiz account.