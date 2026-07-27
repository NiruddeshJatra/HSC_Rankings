from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = 'rankings'

urlpatterns = [
    path('', views.home, name='home'),
    path('methodology/', views.methodology, name='methodology'),

    # Current URL scheme
    path('<str:exam>/<str:year>/<str:group>/', views.results, name='results'),
    path('<str:exam>/<str:year>/individual/<str:roll_no>/', views.individual_result, name='individual'),

    # Legacy permanent redirects (must come after the patterns above)
    path('hsc/individual/<str:roll_no>/', RedirectView.as_view(url='/hsc/2024/individual/%(roll_no)s/', permanent=True)),
    path('ssc/individual/<str:roll_no>/', RedirectView.as_view(url='/ssc/2025/individual/%(roll_no)s/', permanent=True)),
    path('hsc_2025/individual/<str:roll_no>/', RedirectView.as_view(url='/hsc/2025/individual/%(roll_no)s/', permanent=True)),
    path('hsc/<str:group>/', RedirectView.as_view(url='/hsc/2024/%(group)s/', permanent=True)),
    path('ssc/<str:group>/', RedirectView.as_view(url='/ssc/2025/%(group)s/', permanent=True)),
    path('hsc_2025/<str:group>/', RedirectView.as_view(url='/hsc/2025/%(group)s/', permanent=True)),
]
