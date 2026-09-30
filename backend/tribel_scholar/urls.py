from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.documents.views import (
    SourceDocumentViewSet,
    ApplicationDocumentUploadView,
    DocumentDetailView,
    DocumentDownloadView,
    DocumentOCRStatusView,
    DocumentOCRResultView,
    DocumentClassificationView,
    DocumentExtractedFieldsView,
    DocumentTriggerOCRView
)
from apps.schemes.views import (
    SchemeViewSet, SchemeVersionViewSet, SchemeRuleViewSet,
    ReferenceSetViewSet, ReferenceSetItemViewSet,
    SchemeQuotaViewSet, SelectionMethodViewSet, InstitutionEligibilityViewSet
)
from apps.workflow.views import (
    WorkflowDefinitionViewSet, WorkflowStateViewSet,
    WorkflowTransitionViewSet, ApplicationStatusHistoryViewSet
)
from apps.audit.views import AuditLogViewSet
from apps.integrations.views import IntegrationStatusView
from apps.applications.views import ApplicationViewSet, EligibilityEvaluationViewSet, SchemeApplicationFormView

router = DefaultRouter()
router.register(r'source-documents', SourceDocumentViewSet, basename='source-document')
router.register(r'schemes', SchemeViewSet, basename='scheme')
router.register(r'scheme-versions', SchemeVersionViewSet, basename='scheme-version')
router.register(r'rules', SchemeRuleViewSet, basename='rule')
router.register(r'quotas', SchemeQuotaViewSet, basename='quota')
router.register(r'selection-methods', SelectionMethodViewSet, basename='selection-method')
router.register(r'institution-eligibilities', InstitutionEligibilityViewSet, basename='institution-eligibility')
router.register(r'reference-sets', ReferenceSetViewSet, basename='reference-set')
router.register(r'reference-set-items', ReferenceSetItemViewSet, basename='reference-set-item')
router.register(r'applications', ApplicationViewSet, basename='application')
router.register(r'eligibility-evaluations', EligibilityEvaluationViewSet, basename='eligibility-evaluation')
router.register(r'workflow-definitions', WorkflowDefinitionViewSet, basename='workflow-definition')
router.register(r'workflow-states', WorkflowStateViewSet, basename='workflow-state')
router.register(r'workflow-transitions', WorkflowTransitionViewSet, basename='workflow-transition')
router.register(r'application-status-history', ApplicationStatusHistoryViewSet, basename='application-status-history')
router.register(r'audit-logs', AuditLogViewSet, basename='audit-log')

from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(url='/api/v1/', permanent=False), name='api-root-redirect'),
    path('admin/', admin.site.urls),
    path('api/v1/schemes/<uuid:scheme_version_id>/application-form/', SchemeApplicationFormView.as_view(), name='scheme-application-form'),
    path('api/v1/schemes/<str:scheme_version_id>/application-form/', SchemeApplicationFormView.as_view(), name='scheme-application-form-str'),
    path('api/v1/applications/<uuid:application_id>/documents/', ApplicationDocumentUploadView.as_view(), name='application-document-upload'),
    path('api/v1/applications/<str:application_id>/documents/', ApplicationDocumentUploadView.as_view(), name='application-document-upload-str'),
    path('api/v1/documents/<uuid:document_id>/download/', DocumentDownloadView.as_view(), name='document-download'),
    path('api/v1/documents/<str:document_id>/download/', DocumentDownloadView.as_view(), name='document-download-str'),
    path('api/v1/documents/<uuid:document_id>/ocr-status/', DocumentOCRStatusView.as_view(), name='document-ocr-status'),
    path('api/v1/documents/<str:document_id>/ocr-status/', DocumentOCRStatusView.as_view(), name='document-ocr-status-str'),
    path('api/v1/documents/<uuid:document_id>/ocr-result/', DocumentOCRResultView.as_view(), name='document-ocr-result'),
    path('api/v1/documents/<str:document_id>/ocr-result/', DocumentOCRResultView.as_view(), name='document-ocr-result-str'),
    path('api/v1/documents/<uuid:document_id>/classification/', DocumentClassificationView.as_view(), name='document-classification'),
    path('api/v1/documents/<str:document_id>/classification/', DocumentClassificationView.as_view(), name='document-classification-str'),
    path('api/v1/documents/<uuid:document_id>/extracted-fields/', DocumentExtractedFieldsView.as_view(), name='document-extracted-fields'),
    path('api/v1/documents/<str:document_id>/extracted-fields/', DocumentExtractedFieldsView.as_view(), name='document-extracted-fields-str'),
    path('api/v1/documents/<uuid:document_id>/trigger-ocr/', DocumentTriggerOCRView.as_view(), name='document-trigger-ocr'),
    path('api/v1/documents/<str:document_id>/trigger-ocr/', DocumentTriggerOCRView.as_view(), name='document-trigger-ocr-str'),
    path('api/v1/documents/<uuid:document_id>/', DocumentDetailView.as_view(), name='document-detail'),
    path('api/v1/documents/<str:document_id>/', DocumentDetailView.as_view(), name='document-detail-str'),
    path('api/v1/verification/', include('apps.verification.urls')),
    path('api/v1/', include(router.urls)),
    path('api/v1/integrations/status/', IntegrationStatusView.as_view(), name='integration-status'),
]

