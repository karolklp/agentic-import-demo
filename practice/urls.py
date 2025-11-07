from django.urls import path
from .views import practice_views, import_views, import_api

urlpatterns = [
    path('', practice_views.dashboard, name='dashboard'),
    path('reset-data/', practice_views.reset_data, name='reset_data'),
    path('clients/', practice_views.client_list, name='client_list'),
    path('clients/<int:client_id>/', practice_views.client_detail, name='client_detail'),
    path('matters/', practice_views.matter_list, name='matter_list'),
    path('matters/<int:matter_id>/', practice_views.matter_detail, name='matter_detail'),
    path('attorneys/', practice_views.attorney_list, name='attorney_list'),
    path('attorneys/<int:attorney_id>/', practice_views.attorney_detail, name='attorney_detail'),
    path('invoices/', practice_views.invoice_list, name='invoice_list'),
    path('invoices/<int:invoice_id>/', practice_views.invoice_detail, name='invoice_detail'),

    # Import system
    path('import/', import_views.import_upload, name='import_upload'),
    path('import/<int:job_id>/', import_views.import_monitor, name='import_monitor'),
    path('import/<int:job_id>/status/', import_views.import_status, name='import_status'),
    path('import/<int:job_id>/logs/', import_views.import_logs_stream, name='import_logs_stream'),
    path('import/<int:job_id>/question/<int:question_id>/', import_views.import_question_answer, name='import_question_answer'),

    # API endpoints for Claude worker
    path('api/import/<int:job_id>/log/', import_api.api_add_log, name='api_add_log'),
    path('api/import/<int:job_id>/question/', import_api.api_ask_question, name='api_ask_question'),
    path('api/import/<int:job_id>/questions/pending/', import_api.api_get_pending_questions, name='api_get_pending_questions'),
    path('api/import/<int:job_id>/question/<int:question_id>/answer/', import_api.api_get_answer, name='api_get_answer'),
    path('api/import/<int:job_id>/status/', import_api.api_update_status, name='api_update_status'),
    path('api/import/<int:job_id>/record/', import_api.api_record_imported, name='api_record_imported'),
    path('import/api/logs/', import_api.api_get_logs, name='api_get_logs'),  # For frontend log polling
]
