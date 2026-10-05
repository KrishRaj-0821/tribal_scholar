from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied

from apps.applications.models import Application
from apps.accounts.models import UserRole
from .models import SMSNotification
from .serializers import SMSNotificationSerializer


class ApplicationSMSNotificationListView(generics.ListAPIView):
    """
    GET /api/v1/applications/{application_id}/notifications/
    Returns SMS notification audit history for an application.
    Protected by RBAC and IDOR ownership check.
    """
    serializer_class = SMSNotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        app_id = self.kwargs.get('application_id')
        application = get_object_or_404(Application, id=app_id)
        user = self.request.user

        # Ownership authorization: applicant owns application, or user is authorized officer/admin
        if getattr(user, 'role', '') == UserRole.APPLICANT:
            if application.applicant and application.applicant.user != user:
                raise PermissionDenied("You can only view notifications for your own application.")

        return SMSNotification.objects.filter(application=application).order_by('-created_at')


class RetrySMSNotificationView(generics.GenericAPIView):
    """
    POST /api/v1/notifications/{notification_id}/retry/
    Allows retrying a failed notification.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, notification_id):
        from .tasks import dispatch_sms_notification_task
        from .models import NotificationStatus

        notification = get_object_or_404(SMSNotification, id=notification_id)
        user = request.user

        if notification.application and getattr(user, 'role', '') == UserRole.APPLICANT:
            if notification.application.applicant and notification.application.applicant.user != user:
                raise PermissionDenied("You can only retry notifications for your own application.")

        if notification.status not in [NotificationStatus.FAILED, NotificationStatus.RETRY_PENDING]:
            return Response(
                {"error": f"Cannot retry notification with status {notification.status}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        notification.status = NotificationStatus.PENDING
        notification.failure_reason = None
        notification.save(update_fields=['status', 'failure_reason'])

        try:
            dispatch_sms_notification_task.delay(str(notification.id))
        except Exception:
            dispatch_sms_notification_task(str(notification.id))

        notification.refresh_from_db()
        return Response(SMSNotificationSerializer(notification).data, status=status.HTTP_200_OK)


class WorkerEgressIPView(generics.GenericAPIView):
    """
    GET /api/v1/notifications/worker-egress-ip/
    Inspects both the backend web service and Celery worker outbound egress IPs.
    If ?probe=true is provided, executes probe_fast2sms_connectivity_task on worker.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        import urllib.request
        from .tasks import check_worker_egress_ip_task, probe_fast2sms_connectivity_task

        # 1. Backend web process egress IP
        backend_ip = "unknown"
        try:
            req = urllib.request.Request('https://api.ipify.org', headers={'User-Agent': 'curl/8.0.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                backend_ip = resp.read().decode('utf-8').strip()
        except Exception as e:
            backend_ip = f"error: {str(e)}"

        # 2. Celery worker egress IP
        worker_data = {}
        try:
            async_res = check_worker_egress_ip_task.delay()
            worker_data = async_res.get(timeout=15)
        except Exception as exc:
            worker_data = {"error": f"Failed to query worker egress IP: {str(exc)}"}

        response_data = {
            "backend_egress_ip": backend_ip,
            "worker_egress": worker_data,
        }

        # 3. Optional live Fast2SMS probe from worker
        if request.query_params.get('probe') == 'true':
            test_phone = request.query_params.get('phone', '9122671902')
            try:
                probe_res = probe_fast2sms_connectivity_task.delay(test_phone=test_phone)
                response_data["fast2sms_worker_probe"] = probe_res.get(timeout=15)
            except Exception as probe_err:
                response_data["fast2sms_worker_probe"] = {"error": str(probe_err)}

        return Response(response_data, status=status.HTTP_200_OK)


