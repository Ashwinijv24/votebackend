from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('register/', views.register, name='api_register'),
    path('login/', views.login, name='api_login'),
    path('logout/', views.logout, name='api_logout'),
    path('face-verify/', views.face_verification, name='api_face_verify'),

    # Elections
    path('elections/', views.elections, name='api_elections'),
    path('elections/<int:pk>/', views.election_detail, name='api_election_detail'),

    # Voting
    path('vote/', views.vote_page, name='api_vote'),
    path('vote/submit/', views.submit_vote, name='api_vote_submit'),

    # Results
    path('results/', views.results, name='api_results'),
    path('admin/results/', views.admin_results, name='api_admin_results'),
]
