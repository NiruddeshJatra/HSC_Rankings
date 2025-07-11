from django.urls import path
from . import views

app_name = 'rankings'

urlpatterns = [
    path('', views.home, name='home'),
    path('<str:exam_type>/<str:group>/', views.results, name='results'),
    path('<str:exam_type>/individual/<str:roll_no>/', views.individual_result, name='individual'),
    # Add any other needed routes here
]
