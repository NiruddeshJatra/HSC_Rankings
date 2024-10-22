from django.urls import path
from . import views

app_name = 'rankings'

urlpatterns = [
    path('', views.results, {'group': 'SCIENCE'}, name='results_default'),
    path('<str:group>/', views.results, name='results'),
    path('individual/<str:roll_no>/', views.individual_result, name='individual'),
]
