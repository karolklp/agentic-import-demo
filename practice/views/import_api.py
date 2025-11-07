"""API endpoints for Claude import worker to communicate with Django"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from django.utils import timezone
import json

from ..models import ImportJob, ImportQuestion, ImportLog


@csrf_exempt
@require_http_methods(["POST"])
def api_add_log(request, job_id):
    """Claude posts logs during import"""
    job = get_object_or_404(ImportJob, id=job_id)

    try:
        data = json.loads(request.body)
        message = data.get('message', '')
        level = data.get('level', 'INFO')
        metadata = data.get('metadata', {})

        log = ImportLog.objects.create(
            job=job,
            message=message,
            level=level,
            metadata=json.dumps(metadata) if metadata else ''
        )

        return JsonResponse({
            'success': True,
            'log_id': log.id
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def api_ask_question(request, job_id):
    """Claude asks a question that needs user input"""
    job = get_object_or_404(ImportJob, id=job_id)

    try:
        data = json.loads(request.body)

        question = ImportQuestion.objects.create(
            job=job,
            question_type=data.get('question_type', 'text'),
            question_text=data['question_text'],
            context=data.get('context', ''),
            options=data.get('options'),
            related_entity=data.get('related_entity', ''),
            related_data=data.get('related_data')
        )

        # Update job status to waiting for input
        job.status = 'waiting_input'
        job.save()

        job.add_log(f'Asked question: {question.question_text[:50]}...', 'DECISION')

        return JsonResponse({
            'success': True,
            'question_id': question.id
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@csrf_exempt
@require_http_methods(["GET"])
def api_get_pending_questions(request, job_id):
    """Get all pending questions for a job"""
    job = get_object_or_404(ImportJob, id=job_id)

    questions = ImportQuestion.objects.filter(
        job=job,
        status='pending'
    ).order_by('created_at')

    data = [{
        'id': q.id,
        'question_type': q.question_type,
        'question_text': q.question_text,
        'context': q.context,
        'options': q.options,
        'created_at': q.created_at.isoformat()
    } for q in questions]

    return JsonResponse({
        'success': True,
        'questions': data
    })


@csrf_exempt
@require_http_methods(["GET"])
def api_get_answer(request, job_id, question_id):
    """Get answer for a specific question (polls until answered)"""
    job = get_object_or_404(ImportJob, id=job_id)
    question = get_object_or_404(ImportQuestion, id=question_id, job=job)

    if question.status == 'answered':
        return JsonResponse({
            'success': True,
            'answered': True,
            'answer': question.answer,
            'answered_at': question.answered_at.isoformat()
        })
    else:
        return JsonResponse({
            'success': True,
            'answered': False
        })


@csrf_exempt
@require_http_methods(["PATCH"])
def api_update_status(request, job_id):
    """Update job status and statistics"""
    job = get_object_or_404(ImportJob, id=job_id)

    try:
        data = json.loads(request.body)

        if 'status' in data:
            job.status = data['status']

            if data['status'] == 'processing' and not job.started_at:
                job.started_at = timezone.now()
            elif data['status'] in ['completed', 'failed']:
                job.completed_at = timezone.now()

        if 'records_processed' in data:
            job.records_processed = data['records_processed']
        if 'records_imported' in data:
            job.records_imported = data['records_imported']
        if 'records_skipped' in data:
            job.records_skipped = data['records_skipped']
        if 'errors_count' in data:
            job.errors_count = data['errors_count']
        if 'summary' in data:
            job.summary = data['summary']
        if 'error_details' in data:
            job.error_details = data['error_details']

        job.save()

        return JsonResponse({
            'success': True
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def api_record_imported(request, job_id):
    """Record that a record was successfully imported"""
    job = get_object_or_404(ImportJob, id=job_id)

    try:
        data = json.loads(request.body)

        from ..models import ImportedRecord, ImportFile

        file = ImportFile.objects.get(id=data['file_id'], job=job)

        record = ImportedRecord.objects.create(
            job=job,
            model_name=data['model_name'],
            record_id=data['record_id'],
            source_file=file,
            source_row=data.get('source_row')
        )

        return JsonResponse({
            'success': True,
            'record_id': record.id
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@csrf_exempt
@require_http_methods(["GET"])
def api_get_logs(request):
    """Get logs for a job (for frontend polling)"""
    job_id = request.GET.get('job_id')
    after_id = int(request.GET.get('after_id', 0))

    if not job_id:
        return JsonResponse({'error': 'job_id required'}, status=400)

    job = get_object_or_404(ImportJob, id=job_id)

    logs = ImportLog.objects.filter(
        job=job,
        id__gt=after_id
    ).order_by('id')[:100]  # Limit to 100 logs per request

    data = [{
        'id': log.id,
        'timestamp': log.timestamp.isoformat(),
        'level': log.level,
        'message': log.message,
        'metadata': log.metadata_dict
    } for log in logs]

    return JsonResponse(data, safe=False)
