from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from .forms import SignUpForm, BloodBankSignUpForm, AppointmentForm
from django.contrib import messages
from .models import UserProfile, State, District, BloodBank, BloodStock, BloodCamp, BloodDonationCamp, Appointment
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import google.generativeai as genai
from django.conf import settings
import logging
import json
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import datetime
from django.urls import reverse
from django.db import connection
import pytz

# Set up logging
logger = logging.getLogger(__name__)

# Initialize Google AI model
model = None
try:
    if not settings.GENAI_API_KEY:
        print("ERROR: No API key found in settings!")
    else:
        print(f"Configuring Gemini with API key: {settings.GENAI_API_KEY[:5]}...")
        
        # Configure the API
        genai.configure(api_key=settings.GENAI_API_KEY)
        
        # Use gemini-1.5-pro model which supports generateContent
        model = genai.GenerativeModel('models/gemini-1.5-pro')
        print("Gemini model initialized successfully")
            
except Exception as e:
    print(f"Error initializing Gemini model: {str(e)}")
    print(f"Error type: {type(e)}")
    model = None

# Create your views here.

def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            blood_group = form.cleaned_data.get('blood_group')
            UserProfile.objects.filter(user=user).update(blood_group=blood_group)
            messages.success(request, 'Account created successfully! Please login to continue.')
            return redirect('login')
    else:
        form = SignUpForm()
    return render(request, 'accounts/signup.html', {'form': form})

def login_view(request):
    login_type = request.GET.get('type', 'user')
    print(f"Login type: {login_type}")  # Debug print
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        print(f"Login attempt for username: {username}")  # Debug print
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            print(f"User authenticated. Is staff: {user.is_staff}")  # Debug print
            if login_type == 'blood_bank' and not user.is_staff:
                messages.error(request, 'Invalid blood bank credentials.')
                return render(request, 'accounts/login.html', {'login_type': login_type})
            
            login(request, user)
            print("User logged in successfully")  # Debug print
            
            # Redirect blood bank users to their dashboard
            if login_type == 'blood_bank' and user.is_staff:
                print("Redirecting to blood bank dashboard")  # Debug print
                return redirect('blood_bank_dashboard')
                
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')
            print("Authentication failed")  # Debug print
    
    return render(request, 'accounts/login.html', {'login_type': login_type})

def blood_bank_login_view(request):
    return redirect('/?type=blood_bank')

@login_required(login_url='login')
def dashboard_view(request):
    context = {}
    if request.user.is_authenticated:
        context['user'] = request.user
        try:
            context['blood_group'] = request.user.userprofile.blood_group
        except UserProfile.DoesNotExist:
            context['blood_group'] = None
    return render(request, 'accounts/dashboard.html', context)

def logout_view(request):
    logout(request)
    messages.success(request, "You have been successfully logged out.")
    return redirect('login')

@login_required(login_url='login')
def type_donation_view(request):
    return render(request, 'accounts/type_donation.html')

@login_required(login_url='login')
def blood_donation_types_view(request):
    return render(request, 'accounts/blooddonationtypes.html')

@login_required(login_url='login')
def blood_availability_view(request):
    states = State.objects.all()
    context = {
        'states': states
    }
    return render(request, 'accounts/blood_availability.html', context)

@csrf_exempt
def get_blood_availability(request):
    if request.method == 'POST':
        try:
            state_id = request.POST.get('state')
            district_id = request.POST.get('district')
            blood_group = request.POST.get('blood_group')
            component = request.POST.get('component')

            # Query blood banks based on filters
            blood_stocks = BloodStock.objects.filter(
                blood_bank__district__state_id=state_id,
                blood_bank__district_id=district_id,
                blood_group=blood_group,
                component=component,
                units_available__gt=0,
                blood_bank__is_active=True
            ).select_related('blood_bank', 'blood_bank__district')

            results = []
            for stock in blood_stocks:
                results.append({
                    'id': stock.blood_bank.id,
                    'name': stock.blood_bank.name,
                    'location': f"{stock.blood_bank.district.name}, {stock.blood_bank.district.state.name}",
                    'contact': stock.blood_bank.contact_number,
                    'blood_group': stock.blood_group,
                    'component': stock.component,
                    'units_available': stock.units_available,
                    'last_updated': stock.last_updated.strftime("%Y-%m-%d %H:%M")
                })

            return JsonResponse(results, safe=False)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@csrf_exempt
def get_districts(request, state_id):
    try:
        districts = District.objects.filter(state_id=state_id).values('id', 'name')
        return JsonResponse(list(districts), safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def chatbot_view(request):
    if request.method == 'GET':
        return render(request, 'accounts/chatbot.html')
    
    if request.method == 'POST':
        try:
            print("\nReceived chatbot request")
            
            message = request.POST.get('message', '')
            print(f"User message: {message}")
            
            if not message:
                return JsonResponse({
                    'response': 'Please enter a message.'
                })

            if not model:
                print("Error: Gemini model not initialized")
                return JsonResponse({
                    'response': 'The AI service is currently unavailable. Please try again later.'
                })
            
            # Add context about blood donation to every prompt
            context = """You are an AI assistant for Jeevandayani, a blood donation platform. 
            You help users with questions about blood donation, blood types, eligibility, and the donation process. 
            Keep responses focused on blood donation and related medical topics. 
            Be professional but friendly, and always prioritize medical accuracy.
            Keep your responses concise and to the point."""
            
            try:
                # Generate response using the simple generate_content method
                print("\nGenerating response...")
                response = model.generate_content(
                    f"{context}\n\nUser: {message}",
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.7,
                        top_p=1,
                        top_k=40,
                        max_output_tokens=1024,
                    )
                )
                
                print("Response received from Gemini")
                print(f"Response type: {type(response)}")
                
                if hasattr(response, 'text'):
                    response_text = response.text.strip()
                    if response_text:
                        return JsonResponse({'response': response_text})
                    else:
                        print("Error: Empty response text")
                else:
                    print("Error: Response has no 'text' attribute")
                    print(f"Raw response: {response}")
                
                raise ValueError("Could not extract valid response from AI model")
                    
            except Exception as api_error:
                print(f"\nGemini API error: {str(api_error)}")
                print(f"Error type: {type(api_error)}")
                return JsonResponse({
                    'response': f'I apologize, but I encountered an issue generating a response. Error: {str(api_error)}'
                })
            
        except Exception as e:
            print(f"\nGeneral error: {str(e)}")
            print(f"Error type: {type(e)}")
            return JsonResponse({
                'response': f'I apologize, but I encountered a technical issue. Error: {str(e)}'
            })

def about_view(request):
    return render(request, 'accounts/about.html')

def blood_bank_signup_view(request):
    if request.method == 'POST':
        form = BloodBankSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.is_staff = True  # Make the user a staff member
            user.save()
            print(f"Created blood bank user: {user.username}, is_staff: {user.is_staff}")  # Debug print
            
            # Create the blood bank
            blood_bank = BloodBank.objects.create(
                name=form.cleaned_data['name'],
                address=form.cleaned_data['address'],
                district=form.cleaned_data['district'],
                contact_number=form.cleaned_data['contact_number'],
                email=form.cleaned_data['email'],
                license_number=form.cleaned_data['license_number'],
                is_active=True  # Ensure the blood bank is active
            )
            print(f"Created blood bank: {blood_bank.name}, email: {blood_bank.email}")  # Debug print
            
            messages.success(request, 'Blood bank registered successfully! Please login to continue.')
            return redirect('login')
    else:
        form = BloodBankSignUpForm()
    return render(request, 'accounts/blood_bank_signup.html', {'form': form})

@login_required(login_url='login')
def search_camps_view(request):
    states = State.objects.all().order_by('name')
    today = timezone.now().date()
    context = {
        'states': states,
        'today': today
    }
    return render(request, 'accounts/search_camps.html', context)

@csrf_exempt
def search_camps(request):
    if request.method == 'GET':
        try:
            state_id = request.GET.get('state')
            district_id = request.GET.get('district')
            date_str = request.GET.get('date')

            results = []

            # Get blood camps
            blood_camps = BloodCamp.objects.filter(is_active=True)
            if state_id:
                blood_camps = blood_camps.filter(district__state_id=state_id)
            if district_id:
                blood_camps = blood_camps.filter(district_id=district_id)
            if date_str:
                blood_camps = blood_camps.filter(camp_date=date_str)

            # Add blood camps to results
            for camp in blood_camps:
                results.append({
                    'name': camp.name,
                    'location': camp.location,
                    'contact': camp.contact_number,
                    'date': camp.camp_date.strftime('%B %d, %Y'),
                    'time': f"{camp.start_time.strftime('%I:%M %p')} - {camp.end_time.strftime('%I:%M %p')}",
                    'description': camp.description,
                    'blood_bank': camp.blood_bank.name,
                    'contact_person': camp.contact_person,
                    'expected_donors': camp.expected_donors,
                    'type': 'Regular Camp'
                })

            # Get blood donation camps
            donation_camps = BloodDonationCamp.objects.all()
            if state_id:
                donation_camps = donation_camps.filter(blood_bank__district__state_id=state_id)
            if district_id:
                donation_camps = donation_camps.filter(blood_bank__district_id=district_id)
            if date_str:
                donation_camps = donation_camps.filter(camp_date=date_str)

            # Add blood donation camps to results
            for camp in donation_camps:
                results.append({
                    'name': camp.name,
                    'location': camp.location,
                    'contact': camp.contact_number,
                    'date': camp.camp_date.strftime('%B %d, %Y'),
                    'time': f"{camp.start_time.strftime('%I:%M %p')} - {camp.end_time.strftime('%I:%M %p')}",
                    'description': camp.description,
                    'blood_bank': camp.blood_bank.name,
                    'contact_person': camp.contact_person,
                    'expected_donors': camp.expected_donors,
                    'type': 'Special Donation Camp'
                })

            # Sort results by date
            results.sort(key=lambda x: datetime.strptime(x['date'], '%B %d, %Y'))

            return JsonResponse(results, safe=False)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@login_required(login_url='login')
def search_banks_view(request):
    states = State.objects.all().order_by('name')
    context = {
        'states': states
    }
    return render(request, 'accounts/search_banks.html', context)

@csrf_exempt
def search_banks(request):
    if request.method == 'GET':
        try:
            state_id = request.GET.get('state')
            district_id = request.GET.get('district')
            blood_group = request.GET.get('blood_group')

            # Base query
            blood_banks = BloodBank.objects.filter(is_active=True)

            # Apply filters
            if state_id:
                blood_banks = blood_banks.filter(district__state_id=state_id)
            if district_id:
                blood_banks = blood_banks.filter(district_id=district_id)
            if blood_group:
                blood_banks = blood_banks.filter(blood_stocks__blood_group=blood_group, blood_stocks__units_available__gt=0).distinct()

            # Get the results
            results = []
            for bank in blood_banks:
                results.append({
                    'id': bank.id,
                    'name': bank.name,
                    'address': bank.address,
                    'contact_number': bank.contact_number,
                    'email': bank.email,
                    'license_number': bank.license_number
                })

            return JsonResponse(results, safe=False)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@login_required(login_url='login')
def schedule_appointment_view(request, bank_id):
    try:
        blood_bank = BloodBank.objects.get(id=bank_id, is_active=True)
        print(f"Blood bank found: {blood_bank.name}, ID: {blood_bank.id}")  # Debug print
    except BloodBank.DoesNotExist:
        messages.error(request, "Blood bank not found or is inactive")
        return redirect('search_banks')

    if request.method == 'POST':
        print("=" * 50)
        print("POST request received in schedule_appointment_view")  # Debug print
        print(f"POST data: {request.POST}")  # Debug print
        
        # Double-check blood_bank_id from form
        form_bank_id = request.POST.get('blood_bank_id')
        print(f"Form blood_bank_id: {form_bank_id}")
        
        # Ensure we're using the correct blood bank
        if form_bank_id and form_bank_id.isdigit():
            try:
                form_bank = BloodBank.objects.get(id=int(form_bank_id))
                if form_bank.id != blood_bank.id:
                    print(f"Warning: Form bank ID ({form_bank.id}) doesn't match URL bank ID ({blood_bank.id})")
                    # Use the one from the URL for consistency
            except BloodBank.DoesNotExist:
                print(f"Blood bank with ID {form_bank_id} from form not found")
        
        form = AppointmentForm(request.POST)
        print(f"Form validation: {form.is_valid()}")  # Debug print
        if not form.is_valid():
            print(f"Form errors: {form.errors}")  # Debug print
            print(f"Form non-field errors: {form.non_field_errors()}")  # Debug print
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error in {field}: {error}")
            return render(request, 'accounts/schedule_appointment.html', {'form': form, 'blood_bank': blood_bank})
        
        try:
            appointment = form.save(commit=False)
            appointment.user = request.user
            print(f"Setting blood_bank_id to {blood_bank.id} for user {request.user.username}")
            appointment.blood_bank_id = blood_bank.id  # Directly set the ID to avoid RelatedObjectDoesNotExist
            appointment.status = 'PENDING'
            
            print(f"About to save appointment for blood bank: {blood_bank.name}, ID: {blood_bank.id}")
            
            # First try a regular save
            try:
                print("Trying regular save method...")
                appointment.save()
                print(f"Appointment saved via regular method with ID: {appointment.id}")
                
                # Double-check the appointment was saved with the correct blood bank
                saved_appointment = Appointment.objects.get(id=appointment.id)
                print(f"Saved appointment blood bank: {saved_appointment.blood_bank_id} vs expected: {blood_bank.id}")
                
                # Store appointment info in session for confirmation page
                request.session['appointment_info'] = {
                    'id': appointment.id,
                    'full_name': appointment.full_name,
                    'blood_bank_name': blood_bank.name,
                    'appointment_date': appointment.appointment_date.strftime('%Y-%m-%d'),
                    'appointment_time': appointment.appointment_time,
                    'blood_group': appointment.blood_group
                }
                print(f"Stored in session: {request.session['appointment_info']}")
                request.session.modified = True
                
                print("About to redirect to appointment_confirmation")  # Debug print
                return_url = reverse('appointment_confirmation')
                print(f"Redirect URL: {return_url}")
                messages.success(request, "Appointment scheduled successfully! You will receive a confirmation soon.")
                return redirect(return_url)
            except Exception as save_error:
                print(f"Regular save error: {save_error}")
                print(f"Error type: {type(save_error)}")  # Debug print
                print("Attempting direct SQL insert...")
                
                # Try direct SQL approach as a fallback
                with connection.cursor() as cursor:
                    try:
                        # Get a timestamp for created_at and updated_at
                        now = datetime.now(pytz.timezone('UTC')).strftime('%Y-%m-%d %H:%M:%S')
                        
                        # Direct SQL insert
                        cursor.execute(
                            """
                            INSERT INTO accounts_appointment 
                            (user_id, blood_bank_id, appointment_date, appointment_time, full_name, age, gender, 
                            blood_group, phone_number, email, address, govt_id_type, govt_id_number, 
                            previous_donation, medical_conditions, status, created_at, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            [
                                request.user.id, blood_bank.id, 
                                appointment.appointment_date.strftime('%Y-%m-%d'), appointment.appointment_time,
                                appointment.full_name, appointment.age, appointment.gender, appointment.blood_group,
                                appointment.phone_number, appointment.email, appointment.address, appointment.govt_id_type,
                                appointment.govt_id_number, 
                                appointment.previous_donation.strftime('%Y-%m-%d') if appointment.previous_donation else None, 
                                appointment.medical_conditions, 'PENDING', now, now
                            ]
                        )
                        connection.commit()
                        print("Appointment inserted directly via SQL")
                        
                        # Store appointment info in session for confirmation page
                        request.session['appointment_info'] = {
                            'full_name': appointment.full_name,
                            'blood_bank_name': blood_bank.name,
                            'appointment_date': appointment.appointment_date.strftime('%Y-%m-%d'),
                            'appointment_time': appointment.appointment_time,
                            'blood_group': appointment.blood_group
                        }
                        
                        print("About to redirect to appointment_confirmation after SQL insert")  # Debug print
                        print("Appointment saved successfully via SQL")
                        messages.success(request, "Appointment scheduled successfully! You will receive a confirmation soon.")
                        return redirect('appointment_confirmation')
                    except Exception as sql_error:
                        print(f"SQL Error: {sql_error}")
                        print(f"SQL Error type: {type(sql_error)}")  # Debug print
                        raise
        except ValidationError as e:
            print(f"ValidationError: {e}")  # Debug print
            for field, errors in e.message_dict.items():
                for error in errors:
                    form.add_error(field, error)
        except Exception as e:
            print(f"Exception during save: {str(e)}")  # Debug print
            print(f"Exception type: {type(e)}")  # Debug print
            messages.error(request, f"Error saving appointment: {str(e)}")
    else:
        initial_data = {}
        if hasattr(request.user, 'userprofile'):
            initial_data['blood_group'] = request.user.userprofile.blood_group
        form = AppointmentForm(initial=initial_data)

    context = {
        'form': form,
        'blood_bank': blood_bank
    }
    return render(request, 'accounts/schedule_appointment.html', context)

@login_required(login_url='login')
def appointment_confirmation(request):
    print("=" * 50)
    print("Entering appointment_confirmation view")
    context = {}
    
    # Debug the entire session
    print("All session keys:", request.session.keys())
    
    # Get appointment info from session
    appointment_info = request.session.get('appointment_info', {})
    print(f"Session appointment_info: {appointment_info}")
    
    if appointment_info:
        context['appointment'] = appointment_info
        print(f"Added appointment info to context: {appointment_info}")
        
        # Clear the session data after using it
        try:
            del request.session['appointment_info']
            request.session.modified = True
            print("Session data cleared successfully")
        except KeyError:
            print("KeyError: appointment_info not found in session")
    else:
        print("No appointment info found in session - trying fallback")
        # Try to get the most recent appointment for this user
        try:
            recent_appointment = Appointment.objects.filter(
                user=request.user
            ).order_by('-created_at').first()
            
            if recent_appointment:
                print(f"Found recent appointment: {recent_appointment.id}")
                context['appointment'] = {
                    'id': recent_appointment.id,
                    'full_name': recent_appointment.full_name,
                    'blood_bank_name': recent_appointment.blood_bank.name,
                    'appointment_date': recent_appointment.appointment_date.strftime('%Y-%m-%d'),
                    'appointment_time': recent_appointment.appointment_time,
                    'blood_group': recent_appointment.blood_group
                }
                print(f"Using fallback recent appointment: {context['appointment']}")
            else:
                print("No recent appointments found for this user")
                messages.warning(request, "No appointment information found. Please try scheduling again.")
        except Exception as e:
            print(f"Error retrieving recent appointment: {e}")
            messages.warning(request, "No appointment information found. Please try scheduling again.")
    
    return render(request, 'accounts/appointment_confirmation.html', context)

def registered_users(request):
    try:
        # If the user is a blood bank staff member, show only their bank's appointments
        if request.user.is_staff:
            blood_bank = BloodBank.objects.get(email=request.user.email)
            print(f"Staff user: showing appointments for blood bank {blood_bank.name}")
        else:
            # For regular users, show all appointments (can be limited later)
            print("Non-staff user: showing all appointments")
            blood_bank = None
        
        # Get appointments based on user type
        if blood_bank:
            appointments = Appointment.objects.filter(blood_bank=blood_bank).order_by('appointment_date')
        else:
            appointments = Appointment.objects.all().order_by('appointment_date')
        
        print(f"Found {appointments.count()} appointments for registered users view")
        for appt in appointments[:5]:  # Print first 5 for debugging
            print(f"Appointment: {appt.id} - {appt.full_name} - {appt.appointment_date}")
            
        return render(request, 'accounts/registered_users.html', {'appointments': appointments})
    except Exception as e:
        print(f"Error in registered_users: {str(e)}")
        messages.error(request, f"Error retrieving appointments: {str(e)}")
        return render(request, 'accounts/error.html', {'message': 'An error occurred while retrieving appointments.'})

@login_required(login_url='login')
def update_blood_stock(request):
    if not request.user.is_staff:
        messages.error(request, 'Access denied. Blood bank login required.')
        return redirect('login')
    
    if request.method == 'POST':
        stock_id = request.POST.get('update_stock')
        try:
            stock = BloodStock.objects.get(id=stock_id)
            
            # Verify the blood bank owns this stock
            if stock.blood_bank.email != request.user.email:
                messages.error(request, 'Access denied. You can only update your own blood bank stock.')
                return redirect('blood_bank_dashboard')
            
            # Update stock
            new_units = request.POST.get(f'stock_{stock_id}')
            new_expiry = request.POST.get(f'expiry_{stock_id}')
            
            if new_units and new_expiry:
                stock.units_available = int(new_units)
                stock.expiry_date = new_expiry
                stock.save()
                messages.success(request, f'Successfully updated {stock.blood_group} {stock.component} stock.')
            else:
                messages.error(request, 'Invalid input. Please provide both units and expiry date.')
                
        except BloodStock.DoesNotExist:
            messages.error(request, 'Blood stock not found.')
        except ValueError:
            messages.error(request, 'Invalid input. Please enter valid numbers for units.')
        except Exception as e:
            # Log the exception and return an error message
            print(f"Error in update_blood_stock: {e}")
            messages.error(request, 'An error occurred while updating the stock.')
            
    return redirect('blood_bank_dashboard')

@login_required(login_url='login')
def add_blood_stock(request):
    if not request.user.is_staff:
        messages.error(request, 'Access denied. Blood bank login required.')
        return redirect('login')
    
    if request.method == 'POST':
        try:
            blood_bank = BloodBank.objects.get(email=request.user.email)
            
            # Get form data
            blood_group = request.POST.get('blood_group')
            component = request.POST.get('component')
            units = int(request.POST.get('units'))
            expiry_date = request.POST.get('expiry_date')
            
            # Create new blood stock entry
            BloodStock.objects.create(
                blood_bank=blood_bank,
                blood_group=blood_group,
                component=component,
                units_available=units,
                expiry_date=expiry_date
            )
            
            messages.success(request, f'Successfully added {units} units of {blood_group} {component}.')
        except BloodBank.DoesNotExist:
            messages.error(request, 'Blood bank not found.')
        except ValueError:
            messages.error(request, 'Invalid input. Please enter valid numbers for units.')
        except Exception as e:
            messages.error(request, f'Error adding blood stock: {str(e)}')
    
    return redirect('blood_bank_dashboard')

@login_required
def organize_camp(request):
    if not request.user.is_staff:
        messages.error(request, "Access denied. Only blood banks can organize camps.")
        return redirect('login')

    try:
        blood_bank = BloodBank.objects.get(email=request.user.email)
    except BloodBank.DoesNotExist:
        messages.error(request, "Blood bank not found.")
        return redirect('login')

    if request.method == 'POST':
        try:
            camp = BloodDonationCamp.objects.create(
                blood_bank=blood_bank,
                name=request.POST['name'],
                location=request.POST['location'],
                camp_date=request.POST['camp_date'],
                start_time=request.POST['start_time'],
                end_time=request.POST['end_time'],
                contact_person=request.POST['contact_person'],
                contact_number=request.POST['contact_number'],
                expected_donors=request.POST['expected_donors'],
                description=request.POST['description']
            )
            messages.success(request, f"Blood donation camp '{camp.name}' has been scheduled successfully!")
            return redirect('blood_bank_dashboard')
        except Exception as e:
            messages.error(request, f"Error scheduling camp: {str(e)}")
            return redirect('organize_camp')

    today = datetime.now().date()
    return render(request, 'accounts/organize_camp.html', {'today': today})

@login_required(login_url='login')
def blood_bank_dashboard(request):
    print("=" * 50)
    print("Entering blood_bank_dashboard view")
    context = {}
    registered_users_url = reverse('registered_users')
    context['registered_users_url'] = registered_users_url
    
    if not request.user.is_staff:
        print(f"User {request.user.username} is not staff, redirecting to login")
        messages.error(request, 'Access denied. Blood bank login required.')
        return redirect('login')
    
    try:
        blood_bank = BloodBank.objects.get(email=request.user.email)
        print(f"Found blood bank for dashboard: {blood_bank.name}, ID: {blood_bank.id}")  # Debug print
        
        blood_stocks = BloodStock.objects.filter(blood_bank=blood_bank)
        print(f"Found {blood_stocks.count()} blood stocks")  # Debug print
        
        # Get all appointments for this blood bank
        appointments = Appointment.objects.filter(blood_bank=blood_bank).order_by('appointment_date')
        print(f"Found {appointments.count()} appointments for blood bank {blood_bank.id}")  # Debug print
        
        # Print detailed info about each appointment
        for appt in appointments:
            print(f"Appointment: ID={appt.id}, User={appt.user.username}, Name={appt.full_name}, Date={appt.appointment_date}, Status={appt.status}")  # Debug print
        
        context.update({
            'blood_bank': blood_bank,
            'blood_stocks': blood_stocks,
            'appointments': appointments
        })
        
        return render(request, 'accounts/blood_bank_dashboard.html', context)
    except BloodBank.DoesNotExist:
        print(f"Blood bank not found for user {request.user.username}")
        return render(request, 'accounts/error.html', {'message': 'Blood bank not found.'})
    except Exception as e:
        print(f"Error in blood_bank_dashboard: {str(e)}")  # Debug print
        return render(request, 'accounts/error.html', {'message': 'An error occurred.'})
