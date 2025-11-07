from django.shortcuts import render, redirect, get_object_or_404
from django.http import StreamingHttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib.auth.decorators import login_required
import os
import json
import time

from ..models import ImportJob, ImportFile, ImportQuestion, ImportLog
from ..forms import ImportJobForm, AnswerQuestionForm


def import_upload(request):
    """Upload files for import"""
    if request.method == 'POST':
        form = ImportJobForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            job = form.save()

            # Handle multiple file uploads
            files = request.FILES.getlist('files')
            for uploaded_file in files:
                file_ext = os.path.splitext(uploaded_file.name)[1].lower()
                file_type = 'csv' if file_ext == '.csv' else 'json' if file_ext == '.json' else 'xlsx'

                import_file = ImportFile.objects.create(
                    job=job,
                    filename=uploaded_file.name,
                    file=uploaded_file,
                    file_type=file_type,
                    file_size=uploaded_file.size
                )

            job.files_uploaded = len(files)
            job.status = 'queued'
            job.save()

            job.add_log(f'Uploaded {len(files)} files for import', 'INFO')

            # In production, this would spawn a Render job
            # For local testing, we'll redirect to monitor
            return redirect('import_monitor', job_id=job.id)
    else:
        form = ImportJobForm()

    # Show recent import jobs
    recent_jobs = ImportJob.objects.all()[:10]

    return render(request, 'import/upload.html', {
        'form': form,
        'recent_jobs': recent_jobs
    })


def import_monitor(request, job_id):
    """Real-time monitoring dashboard for import job"""
    job = get_object_or_404(ImportJob, id=job_id)
    questions = job.questions.filter(status='pending').order_by('created_at')

    return render(request, 'import/monitor.html', {
        'job': job,
        'pending_questions': questions
    })


def import_logs_stream(request, job_id):
    """Server-Sent Events stream for real-time logs"""
    job = get_object_or_404(ImportJob, id=job_id)

    def event_stream():
        last_log_id = 0
        while True:
            # Get new logs
            new_logs = ImportLog.objects.filter(
                job=job,
                id__gt=last_log_id
            ).order_by('id')[:50]

            for log in new_logs:
                data = {
                    'id': log.id,
                    'timestamp': log.timestamp.isoformat(),
                    'level': log.level,
                    'message': log.message,
                    'metadata': log.metadata_dict
                }
                yield f"data: {json.dumps(data)}\n\n"
                last_log_id = log.id

            # Check if job is complete
            job.refresh_from_db()
            if job.status in ['completed', 'failed', 'cancelled']:
                yield f"event: complete\ndata: {json.dumps({'status': job.status})}\n\n"
                break

            time.sleep(1)  # Poll every second

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


def import_status(request, job_id):
    """Get current status of import job"""
    job = get_object_or_404(ImportJob, id=job_id)

    data = {
        'status': job.status,
        'records_processed': job.records_processed,
        'records_imported': job.records_imported,
        'records_skipped': job.records_skipped,
        'errors_count': job.errors_count,
        'pending_questions': job.questions.filter(status='pending').count()
    }

    return JsonResponse(data)


def import_question_answer(request, job_id, question_id):
    """Answer a question from the import process"""
    job = get_object_or_404(ImportJob, id=job_id)
    question = get_object_or_404(ImportQuestion, id=question_id, job=job)

    if request.method == 'POST':
        form = AnswerQuestionForm(request.POST)
        if form.is_valid():
            question.answer = form.cleaned_data['answer']
            question.status = 'answered'
            question.answered_at = timezone.now()
            question.save()

            job.add_log(f'User answered question: {question.question_text[:50]}...', 'INFO')

            # If job was waiting, set back to processing
            if job.status == 'waiting_input':
                job.status = 'processing'
                job.save()

            return JsonResponse({'success': True})
    else:
        form = AnswerQuestionForm()

    return render(request, 'import/answer_question.html', {
        'job': job,
        'question': question,
        'form': form
    })


def import_list(request):
    """List all import jobs"""
    jobs = ImportJob.objects.all().order_by('-created_at')

    return render(request, 'import/list.html', {
        'jobs': jobs
    })
