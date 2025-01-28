from urllib import request
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from .models import *
from django.shortcuts import render, redirect
from .models import Equipment, Reservation
from .forms import ReservationForm
from datetime import datetime
from django.db.models import Q
from dateutil import parser
from django.contrib.auth.decorators import login_required
import json
from django.http import JsonResponse, HttpResponse
from dateutil import parser
from django.http import JsonResponse
from django.shortcuts import render
from .models import Equipment, Reservation
from django.contrib import messages
import xml.etree.ElementTree as ET
from django.utils.timezone import now

import logging

def store(request):
    equipment = Equipment.objects.all()

    query = request.GET.get('query', '')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    # Logowanie parametrów
    logging.debug(f"Query: {query}, Min Price: {min_price}, Max Price: {max_price}")

    if query:
        equipment = equipment.filter(name__icontains=query)

    if min_price:
        try:
            min_price = float(min_price)
            equipment = equipment.filter(price_per_day__gte=min_price)
        except ValueError:
            pass

    if max_price:
        try:
            max_price = float(max_price)
            equipment = equipment.filter(price_per_day__lte=max_price)
        except ValueError:
            pass

    context = {
        'equipment': equipment,
        'query': query,
        'min_price': min_price,
        'max_price': max_price,
    }
    return render(request, 'store/store.html', context)




def cart(request):
     context = {}
     return render(request, 'store/cart.html', context)

def reservations(request):
      context = {}
      return render(request, 'store/reservations.html', context)


@login_required
def reserve_equipment(request, equipment_id):
    equipment = get_object_or_404(Equipment, id=equipment_id)

    if request.method == "POST":
        # Pobierz daty z formularza
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        # Walidacja i obliczanie ceny
        if start_date and end_date:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
            total_days = (end_date_obj - start_date_obj).days

            if total_days > 0:
                total_price = total_days * equipment.price_per_day
                # Możesz zapisać rezerwację w bazie danych
                # Tworzenie rezerwacji (zakładając, że masz model Reservation)
                reservation = Reservation(
                    equipment=equipment,
                    start_date=start_date_obj,
                    end_date=end_date_obj,
                    total_price=total_price,
                    user=request.user
                )
                reservation.save()

                rental_history = RentalHistory.objects.create(
                    user=request.user,
                    equipment=equipment,
                    rental_date=start_date_obj,
                    total_price=total_price
                )
                rental_history.save()

                if not hasattr(request.user, 'customer'):
                    customer = Customer.objects.create(
                        user=request.user,
                        name=request.user.username,
                        email=request.user.email
                    )
                    customer.save()

                # Przekazanie informacji do szablonu
                messages.success(request, f"Equipment {equipment.name} reserved successfully!")
                return redirect('store')
            else:
                return HttpResponse("End date must be after start date.")
        else:
            return HttpResponse("Both dates are required.")

    return render(request, 'store/reserve.html', {'equipment': equipment})






@login_required
def user_reservations(request):
    reservations = Reservation.objects.filter(user=request.user)
    unpaid_count = reservations.filter(status='Pending', paid=False).count()
    rental_history = RentalHistory.objects.filter(user=request.user)

    if request.GET.get('export') == 'json':
        reservations_data = [
            {
                'equipment': reservation.equipment.name,
                'start_date': reservation.start_date.strftime('%Y-%m-%d'),
                'end_date': reservation.end_date.strftime('%Y-%m-%d'),
                'total_price': reservation.total_price,
                'status': reservation.status,
                'paid': reservation.paid,
            }
            for reservation in reservations
        ]
        rental_history_data = [
        {
            'equipment': rental.equipment.name,
            'rental_date': rental.rental_date.strftime('%Y-%m-%d'),
            'return_date': rental.return_date.strftime('%Y-%m-%d') if rental.return_date else None,
            'total_price': rental.total_price,
        }
            for rental in rental_history
    ]
    
        response_data = {
            'reservations': reservations_data,
            'rental_history': rental_history_data,
    }
        return JsonResponse(response_data, safe=False)

    # Eksport do XML
    if request.GET.get('export') == 'xml':
        root = ET.Element('reservations')
        for reservation in reservations:
            res_elem = ET.SubElement(root, 'reservation')
            ET.SubElement(res_elem, 'equipment').text = reservation.equipment.name
            ET.SubElement(res_elem, 'start_date').text = reservation.start_date.strftime('%Y-%m-%d')
            ET.SubElement(res_elem, 'end_date').text = reservation.end_date.strftime('%Y-%m-%d')
            ET.SubElement(res_elem, 'total_price').text = str(reservation.total_price)
            ET.SubElement(res_elem, 'status').text = reservation.status
            ET.SubElement(res_elem, 'paid').text = str(reservation.paid)
        xml_data = ET.tostring(root, encoding='utf-8', method='xml')
        response = HttpResponse(xml_data, content_type='application/xml')
        response['Content-Disposition'] = 'attachment; filename="reservations.xml"'
        return response

    if request.method == "POST":
        reservation_id = request.POST.get('reservation_id')
        action = request.POST.get('action')
        reservation = Reservation.objects.get(id=reservation_id, user=request.user)
        
        if action == 'return':
            # Obsługa zwrotu
            reservation.status = 'Returned'
            reservation.save()

            rental_history, created = RentalHistory.objects.get_or_create(
                user=request.user, 
                equipment=reservation.equipment, 
                rental_date=reservation.start_date,
                total_price=reservation.total_price
                )
            rental_history.return_date = datetime.now()
            rental_history.save()
            messages.success(request, f"Reservation for {reservation.equipment.name} has been marked as returned.")
        elif action == 'pay':
            # Obsługa płatności tylko dla statusu Pending i nieopłaconych rezerwacji
            if reservation.status == 'Pending' and not reservation.paid:
                return redirect('payment', reservation_id=reservation.id)
            else:
                messages.error(request, "This reservation cannot be paid.")
        else:
            messages.error(request, "Invalid action.")
        return redirect('reservations')
    
    rental_history = RentalHistory.objects.filter(user=request.user)


    return render(request, 'store/reservations.html', {
        'reservations': reservations,
        'unpaid_count': unpaid_count,
        'rental_history': rental_history})


def payment_view(request, reservation_id):
    reservation = Reservation.objects.get(id=reservation_id)

    if request.method == 'POST':
        # Pobierz dane z formularza
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        payment_method = request.POST.get('payment_method')
        accepted_terms = request.POST.get('accept_terms')

        if not accepted_terms:
            messages.error(request, 'You must accept the terms and conditions.')
            return render(request, 'store/payment.html', {'reservation': reservation})

        # Jeśli płatność zakończona sukcesem
        reservation.paid = True
        reservation.status = 'Confirmed'

        reservation.save()

        # Możesz dodać informacje o dodatkowym sprzęcie do rezerwacji, jeśli chcesz


        messages.success(request, 'Payment successful! Your reservation is now confirmed.')
        return redirect('reservations')  # Przekierowanie do strony rezerwacji

    return render(request, 'store/payment.html', {'reservation': reservation})


from django.contrib.auth import login, authenticate
from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('store')  # Przekierowanie na stronę sklepu po zalogowaniu
            else:
                messages.error(request, "Invalid username or password")
        else:
            messages.error(request, "Invalid username or password")
    else:
        form = AuthenticationForm()

    return render(request, 'store/login.html', {'form': form})


from .forms import RegistrationForm
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash

def signup_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            # Tworzenie nowego użytkownika
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])  # Ustawienie hasła
            user.save()
            messages.success(request, "Account created successfully!")
            return redirect('login')  # Przekierowanie na stronę logowania
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = RegistrationForm()

    return render(request, 'store/signup.html', {'form': form})

from django.contrib.auth import logout
from django.shortcuts import redirect

def logout_view(request):
    logout(request)
    return redirect('store')  # Przekierowanie na stronę sklepu po wylogowaniu


@login_required
def my_account(request):
    user = request.user
    if request.method == "POST":
        password_form = PasswordChangeForm(user, request.POST)
        if password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)  # Uaktualnia sesję, aby użytkownik pozostał zalogowany
            messages.success(request, "Your password was successfully updated!")
            return redirect('my_account')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        password_form = PasswordChangeForm(user)

    return render(request, 'store/my_account.html', {
        'user': user,
        'password_form': password_form
    })