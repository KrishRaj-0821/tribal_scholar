from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    VerificationQueueViewSet, DocumentVerificationViewSet, resolve_conflict_api_view,
    demo_reset_api_view, demo_status_api_view
)

router = DefaultRouter()
router.register(r'queue', VerificationQueueViewSet, basename='verification-queue')

urlpatterns = [
    # Synthetic SIH Demonstration Endpoints
    path('demo/reset/', demo_reset_api_view, name='demo-reset'),
    path('demo/status/', demo_status_api_view, name='demo-status'),

    # Document Evidence & Verification Actions
    path('documents/<uuid:pk>/evidence/', DocumentVerificationViewSet.as_view({'get': 'get_document_evidence'}), name='verification-doc-evidence'),
    path('documents/<str:pk>/evidence/', DocumentVerificationViewSet.as_view({'get': 'get_document_evidence'}), name='verification-doc-evidence-str'),
    path('documents/<uuid:pk>/ocr-fields/', DocumentVerificationViewSet.as_view({'get': 'get_ocr_field_evidence'}), name='verification-doc-ocr-fields'),
    path('documents/<str:pk>/ocr-fields/', DocumentVerificationViewSet.as_view({'get': 'get_ocr_field_evidence'}), name='verification-doc-ocr-fields-str'),
    path('documents/<uuid:pk>/verify-field/', DocumentVerificationViewSet.as_view({'post': 'verify_field'}), name='verification-doc-verify-field'),
    path('documents/<str:pk>/verify-field/', DocumentVerificationViewSet.as_view({'post': 'verify_field'}), name='verification-doc-verify-field-str'),
    path('documents/<uuid:pk>/reject-field/', DocumentVerificationViewSet.as_view({'post': 'reject_field'}), name='verification-doc-reject-field'),
    path('documents/<str:pk>/reject-field/', DocumentVerificationViewSet.as_view({'post': 'reject_field'}), name='verification-doc-reject-field-str'),
    path('documents/<uuid:pk>/history/', DocumentVerificationViewSet.as_view({'get': 'get_verification_history'}), name='verification-doc-history'),
    path('documents/<str:pk>/history/', DocumentVerificationViewSet.as_view({'get': 'get_verification_history'}), name='verification-doc-history-str'),
    path('documents/<uuid:pk>/reopen/', DocumentVerificationViewSet.as_view({'post': 'reopen_verification'}), name='verification-doc-reopen'),
    path('documents/<str:pk>/reopen/', DocumentVerificationViewSet.as_view({'post': 'reopen_verification'}), name='verification-doc-reopen-str'),
    path('documents/<uuid:pk>/verify-document/', DocumentVerificationViewSet.as_view({'post': 'verify_document'}), name='verification-doc-verify-document'),
    path('documents/<str:pk>/verify-document/', DocumentVerificationViewSet.as_view({'post': 'verify_document'}), name='verification-doc-verify-document-str'),
    path('documents/<uuid:pk>/complete/', DocumentVerificationViewSet.as_view({'post': 'complete_verification'}), name='verification-doc-complete'),
    path('documents/<str:pk>/complete/', DocumentVerificationViewSet.as_view({'post': 'complete_verification'}), name='verification-doc-complete-str'),

    # Conflict Resolution
    path('conflicts/<uuid:queue_item_id>/resolve/', resolve_conflict_api_view, name='resolve-conflict'),
    path('conflicts/<str:queue_item_id>/resolve/', resolve_conflict_api_view, name='resolve-conflict-str'),

    # Queue Router URLs
    path('', include(router.urls)),
]
