# An Hassle-Free Event Management Solution

Welcome, the ultimate event management website that streamlines the chaos of organizing events and workshops. Designed to simplify the process because managing events should be as smooth as attending them! ????

## Use Case
    A solution for facilitating symposiums involving various events and workshops. Whether you're a student group, department, or organization, this platform has you covered.

#### Why this repo?

    PLUG AND PLAY !!! 

    Easily feed in data specific to the symposium and make it ONLINE in no time !!!

*The base minimum idea and code is available
(Originally developed for Department Symposium at University; So this can work for all university level symposium organization)

## Features
[That are implemented; Use your creativity and programming hat to do all interesting modifications and additions]

- **Easy Signup**: Create user accounts on the website effortlessly
- **Event Browsing**: Browse available events comfortably
- **Hassle-Free Registration**: Register for events within seconds
- **Customizable Events**: Create, modify, and manage events tailored to your needs
- **Flexible Payment Handling**: Smooth alternative to payment gateways, where we can manually verify user payments in a easier way (when they can't be availed) [ code can be modified to include that too] 
- Display all event participants at one place for certificate processing [Note: currently anyone can access, logic to be coded for change]
- **Driven by Registration Number**: The primary identifier for all user processes
- Mails that are unable to be sent because of some reason are stored in `static/unsent_mails`

## Privileges
- Super Admin
    - Event created by organizer can be made "on-line" or can be brought down
    - Accept winners and runners finalized by organizers to be published "on-line"
    - can do all below stated privilege tasks
- Organiser
    - Create and maintain events
        - event details including registration fee, welcome mail content
    
        - view and download registered participants
        - Maintain a record of "attended" participants
        -  Finalize winners and runners for the event
    - Preview how event details look on-line
    - can also perform "user" actions
- Payment Verifier
    - check and validate payment related things
    - can also perform "user" actions
- User
    - buy passes
    - register into events
- Access to different privilege (organiser, payment verifier, admin) function is provided through seperate dashboards accessable from general user dashboard
- Multiple admins are possible, but is not recommended and admin account can only be created using either source code or by modifying database

## Project Structure
(a typical structure of a flash framework based web app)
- static 
    - contains the assets for the website like css, js files and images
    - images
        - basic website images
    - images/events
        - images for events
    - images/events/payment_screenshots (if UPLOAD_FOLDER is set so)
        - screenshot for payments
- template
    - contains all html files
### Python Source Files
- routes.py
    - contains all routes
- models.py
    - contains all model definitions of the tables used in the website 
    - SQL Alchemy Object-Relational Mapping (ORM) library based models
    - also creates the database (if not exists) and creates a SUPER ADMIN (hardcoded; highest priviledge)
- forms.py
    - create form structure for all forms that appear in the website

## To-Dos (code)
- Add intro.mp4 file (for home repeat banner video)
- add accomodation form link
- Modify pass details and free pass access
- Mailing service
- Forget not to add your OWN touch !

# A General Overview of the website and its functioning with Snapshots

## A "User" level operation
- Home page
    - Contains a bg video (to be added in the /static/images/ directory)
    ![home-page](/readme_assets/home_1.png)

    - the events list, pass, sponsers for the event
    ![event-list](/readme_assets/home_2.png)
    
    - footer
    ![footer](/readme_assets/home_3.png)

- Account related
    - login
    ![login](/readme_assets/login.png)
    - signup
    ![signup](/readme_assets/signup.png)
    -reset password
    ![reset-passwrd-request](/readme_assets/reset_passwrd_1.png)
    ![reset-passwrd](/readme_assets/reset_passwrd_2.png)
    - dashboard
    ![user-dashboard](/readme_assets/user_dashboard.png)
    - update profile
    ![update-profile](/readme_assets/update_profile.png)

- Event related
    - event types list
    ![event-types](/readme_assets/event_categories_view.png)
    - Each category has its own available list of events
    ![events-list](/readme_assets/tech_events_list.png)
    - buy passes for registering into events
    ![buy-pass](/readme_assets/buy_pass.png)
    ![pass-payment](/readme_assets/payment_details.png)
    - event details and registration
    ![event-details](/readme_assets/sample_event_details.png)
    ![event-registration](/readme_assets/sample_event_registration_popup.png)


## A "Organiser" level operation
- Organiser dashboard (access from user dashboard; available at end of the dashboard)
![user-dashboard-organiser](/readme_assets/user_dashboard_for_organiser.png)
-organiser dashboard
![orgaiser-dashboard](/readme_assets/organiser_dashboard.png)
- Event related
    - create event
    ![create-event](/readme_assets/create_event.png)
    - update event (more or less similar to create event)
    ![update-event](/readme_assets/update_event.png)
    - event details
    ![event-details](/readme_assets/event_details.png)
    - download participants list as xlsx spreadsheet
    ![download-participant-xlsx](/readme_assets/participant_list_xlsx.png)

## A "Verifier" level operation
- verifier dashboard
![verifier-dashboard](/readme_assets/verifier_dashboard.png)

## The "Admin" level operation
- admin dashboard
![admin-dashboard](/readme_assets/admin_dashboard.png)
- manage events
![manage-events](/readme_assets/manage_events.png)
- modify user
![modify-user](/readme_assets/modify_user.png)


---

> Because managing events should be as smooth as attending them! ????

---

If this project has inspired you or influenced your work in any way, please feel free to cite this repository. I can't wait seeing innovative projects grow from this basic idea!

# Author
- Rohinth Ram R V