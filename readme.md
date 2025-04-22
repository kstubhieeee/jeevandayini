# Jeevandayini - Blood Donation Management System

Jeevandayini is a comprehensive web application that connects blood donors with blood banks, streamlining the blood donation process and helping save lives.

## Features

### For Donors
- User registration and authentication
- Blood donation appointment scheduling
- View and manage appointment history
- Receive donation certificates
- Track donation status

### For Blood Banks
- Dashboard to view and manage appointments
- Accept or reject donation requests
- Track donor history
- Mark donations as completed
- Send certificates to donors
- Manage blood inventory

## Technology Stack

- **Backend**: Django (Python)
- **Frontend**: HTML, CSS, JavaScript, Bootstrap
- **Database**: SQLite (can be configured for PostgreSQL)
- **Authentication**: Django built-in authentication system

## Installation and Setup

1. Clone the repository
   ```
   git clone https://github.com/kstubhieeee/jeevandayini.git
   cd jeevandayini
   ```

2. Create and activate a virtual environment
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies
   ```
   pip install -r requirements.txt
   ```

4. Run migrations
   ```
   python manage.py migrate
   ```

5. Create a superuser
   ```
   python manage.py createsuperuser
   ```

6. Run the development server
   ```
   python manage.py runserver
   ```

7. Access the application at http://127.0.0.1:8000/

## Project Structure

- **accounts**: Main app containing models, views, and templates
- **bloodbank**: Project configuration and URL routing
- **templates**: HTML templates for the application
- **static**: CSS, JavaScript, and images

## Models

- User (extends Django User)
- BloodBank
- Donor
- Appointment
- BloodInventory
- Certificate

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a pull request

## License

This project is open-source and available under the MIT License.

## Contact

- Project Link: [https://github.com/kstubhieeee/jeevandayini](https://github.com/kstubhieeee/jeevandayini)
