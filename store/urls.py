from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
        #Leave as empty string for base url
	path('', views.store, name="store"),
	path('cart/', views.cart, name="cart"),
	path('reservations/', views.user_reservations, name="reservations"),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('reserve/<int:equipment_id>/', views.reserve_equipment, name='reserve'),
    path('payment/<int:reservation_id>/', views.payment_view, name='payment'),
    path('my_account/', views.my_account, name='my_account'),
    
]