from django.urls import path
from .views import ApplicationSMSNotificationListView, RetrySMSNotificationView

urlpatterns = [
    path('applications/<uuid:application_id>/notifications/', ApplicationSMSNotificationListView.as_view(), name='application-sms-notifications'),
    path('applications/<str:application_id>/notifications/', ApplicationSMSNotificationListView.as_view(), name='application-sms-notifications-str'),
    path('notifications/<uuid:notification_id>/retry/', RetrySMSNotificationView.as_view(), name='notification-retry'),
    path('notifications/<str:notification_id>/retry/', RetrySMSNotificationView.as_view(), name='notification-retry-str'),
]

