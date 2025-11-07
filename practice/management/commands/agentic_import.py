"""
Autonomous import using real Claude API with extended thinking.
This spawns an actual Claude instance that reads claude.md and performs the import.
"""
import os
import sys
import json
import time
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from practice.models import ImportJob, Client, Attorney, Matter, TimeEntry, Invoice, Payment

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class Command(BaseCommand):
    help = 'Run agentic import using real Claude API'

    def add_arguments(self, parser):
        parser.add_argument('job_id', type=int, help='Import job ID')
        parser.add_argument('--api-key', type=str, help='Anthropic API key (or set ANTHROPIC_API_KEY env var)')

    def handle(self, *args, **options):
        job_id = options['job_id']
        api_key = options.get('api_key') or os.environ.get('ANTHROPIC_API_KEY')

        if not ANTHROPIC_AVAILABLE:
            self.stdout.write(self.style.ERROR(
                '❌ Anthropic Python SDK not installed. Install with: pip install anthropic'
            ))
            return

        if not api_key:
            self.stdout.write(self.style.ERROR(
                '❌ No API key provided. Set ANTHROPIC_API_KEY environment variable or use --api-key'
            ))
            return

        try:
            job = ImportJob.objects.get(id=job_id)
        except ImportJob.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ Import job {job_id} not found'))
            return

        self.stdout.write(self.style.SUCCESS(f'\n🤖 Starting Agentic Import for Job #{job_id}'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

        # Read claude.md instructions
        claude_md_path = Path(settings.BASE_DIR) / 'claude.md'
        if not claude_md_path.exists():
            self.stdout.write(self.style.ERROR('❌ claude.md not found'))
            return

        with open(claude_md_path) as f:
            instructions = f.read()

        # Get uploaded files
        files = job.files.all()
        if not files.exists():
            self.stdout.write(self.style.ERROR('❌ No files uploaded for this job'))
            return

        # Build file information
        file_info = []
        for import_file in files:
            file_path = import_file.file.path
            file_info.append({
                'filename': import_file.filename,
                'path': file_path,
                'type': import_file.file_type,
                'size': import_file.file_size
            })

        self.stdout.write(f'\n📁 Files to import:')
        for info in file_info:
            self.stdout.write(f'  - {info["filename"]} ({info["type"]}, {info["size"]} bytes)')

        # Update job status
        job.status = 'processing'
        job.save()
        job.add_log('🤖 Agentic import started with Claude API', 'INFO')

        # Initialize Claude client
        client = Anthropic(api_key=api_key)

        # Prepare the prompt
        system_prompt = f"""{instructions}

## Current Job Context

**Job ID**: {job_id}
**API Base URL**: http://localhost:8800/import/api
**Files Uploaded**: {len(file_info)}

{self._format_file_list(file_info)}

## Your Task

Analyze these files and import the data into the Django database using the API endpoints described above.

**Important Instructions**:
1. Use the API endpoints to log your thinking and decisions
2. Ask questions when you encounter ambiguous data
3. Normalize all date formats
4. Handle duplicates intelligently
5. Resolve foreign key references
6. Update progress regularly

You have access to Python and can execute code. Use the `requests` library to call the API endpoints.

Start by analyzing the files and creating an import plan.
"""

        user_prompt = f"""Please execute the autonomous import for job #{job_id}.

The files are located at:
{chr(10).join(f'- {info["path"]}' for info in file_info)}

Use the Django ORM to create records. You have access to these models:
- Client
- Attorney
- Matter
- TimeEntry
- Invoice
- Payment

Start by reading the files, analyzing their structure, and then proceed with the import following the guidelines in claude.md.
"""

        self.stdout.write(f'\n🧠 Invoking Claude with extended thinking and tool use...\n')
        job.add_log('🧠 Starting agentic import with Claude AI (with execution)', 'INFO')

        # Define tools for Claude to use
        tools = [
            {
                "name": "execute_python",
                "description": "Execute Python code to import data. You have access to Django ORM (Client, Attorney, Matter, etc.) and can make HTTP requests to the API endpoints.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Python code to execute. You can import Django models, make API calls, read files, etc."
                        }
                    },
                    "required": ["code"]
                }
            },
            {
                "name": "log_message",
                "description": "Log a message to the import dashboard so the user can see your progress",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "level": {
                            "type": "string",
                            "enum": ["DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "THINKING", "DECISION"],
                            "description": "Log level"
                        },
                        "message": {
                            "type": "string",
                            "description": "Message to log"
                        }
                    },
                    "required": ["level", "message"]
                }
            }
        ]

        try:
            # Use streaming with tool use
            job.add_log('📡 Calling Anthropic API with streaming and tool use...', 'INFO')

            # Use stream parameter for real-time chunks
            with client.messages.stream(
                model="claude-sonnet-4-5-20250929",
                max_tokens=16000,
                thinking={
                    "type": "enabled",
                    "budget_tokens": 10000
                },
                tools=tools,
                messages=[
                    {
                        "role": "user",
                        "content": system_prompt + "\n\n" + user_prompt
                    }
                ],
                system="You are an autonomous data import agent. You can execute Python code, call APIs, and make intelligent decisions about messy data."
            ) as stream:
                self.stdout.write(self.style.SUCCESS('\n📊 Claude\'s Response (streaming with tool use):\n'))
                job.add_log('📊 Receiving streaming response from Claude...', 'SUCCESS')

                current_text = ""
                current_thinking = ""
                tool_use_id = None
                tool_name = None
                tool_input = {}

                messages = [{"role": "user", "content": system_prompt + "\n\n" + user_prompt}]

                for event in stream:
                    # Handle different event types
                    if event.type == "content_block_start":
                        if hasattr(event.content_block, 'type'):
                            if event.content_block.type == "thinking":
                                self.stdout.write(self.style.WARNING('\n💭 [Thinking]\n'))
                            elif event.content_block.type == "text":
                                self.stdout.write('\n💬 [Response]\n')
                            elif event.content_block.type == "tool_use":
                                tool_use_id = event.content_block.id
                                tool_name = event.content_block.name
                                tool_input = {}
                                self.stdout.write(self.style.SUCCESS(f'\n🔧 [Tool: {tool_name}]\n'))

                    elif event.type == "content_block_delta":
                        if hasattr(event.delta, 'type'):
                            if event.delta.type == "thinking_delta":
                                # Stream thinking in chunks
                                thinking_chunk = event.delta.thinking
                                self.stdout.write(thinking_chunk)
                                current_thinking += thinking_chunk

                                # Log thinking in reasonable chunks (when we hit newlines)
                                if '\n' in thinking_chunk:
                                    lines = current_thinking.split('\n')
                                    for line in lines[:-1]:  # All complete lines
                                        if line.strip():
                                            job.add_log(line[:300], 'THINKING')
                                    current_thinking = lines[-1]  # Keep incomplete line

                            elif event.delta.type == "text_delta":
                                # Stream text response in chunks
                                text_chunk = event.delta.text
                                self.stdout.write(text_chunk)
                                current_text += text_chunk

                                # Log text in reasonable chunks
                                if '\n' in text_chunk or len(current_text) > 200:
                                    lines = current_text.split('\n')
                                    for line in lines[:-1]:
                                        if line.strip():
                                            job.add_log(line[:500], 'INFO')
                                    current_text = lines[-1]

                            elif event.delta.type == "input_json_delta":
                                # Accumulate tool input
                                pass  # Input will be complete in final message

                    elif event.type == "content_block_stop":
                        # Flush any remaining text
                        if current_thinking.strip():
                            job.add_log(current_thinking[:300], 'THINKING')
                            current_thinking = ""
                        if current_text.strip():
                            job.add_log(current_text[:500], 'INFO')
                            current_text = ""

                    elif event.type == "message_stop":
                        # Get the final message with complete tool uses
                        final_message = stream.get_final_message()

                        # Execute any tool uses and continue the loop
                        if final_message.stop_reason == "tool_use":
                            # We'll loop to handle multiple rounds of tool calls
                            max_rounds = 50  # Allow more rounds for complex imports
                            current_round = 0

                            while current_round < max_rounds and final_message.stop_reason == "tool_use":
                                current_round += 1
                                self.stdout.write(f'\n🔄 Tool round {current_round}\n')

                                tool_results = []

                                for content_block in final_message.content:
                                    if content_block.type == "tool_use":
                                        tool_name = content_block.name
                                        tool_input = content_block.input
                                        tool_use_id = content_block.id

                                        self.stdout.write(f'\n🔧 Executing tool: {tool_name}\n')
                                        job.add_log(f'🔧 Executing {tool_name}', 'INFO')

                                        # Execute the tool
                                        result = self._execute_tool(tool_name, tool_input, job)

                                        tool_results.append({
                                            "type": "tool_result",
                                            "tool_use_id": tool_use_id,
                                            "content": result
                                        })

                                        self.stdout.write(f'✓ Tool result: {result[:200]}...\n')

                                # Build assistant message without thinking blocks
                                assistant_content = []
                                for block in final_message.content:
                                    if block.type != "thinking":
                                        assistant_content.append(block)

                                messages.append({
                                    "role": "assistant",
                                    "content": assistant_content
                                })
                                messages.append({
                                    "role": "user",
                                    "content": tool_results
                                })

                                # Make another API call
                                response = client.messages.create(
                                    model="claude-sonnet-4-5-20250929",
                                    max_tokens=8000,
                                    tools=tools,
                                    messages=messages,
                                    system="You are an autonomous data import agent. Continue executing the import."
                                )

                                # Process response
                                for block in response.content:
                                    if block.type == "text":
                                        self.stdout.write(block.text)
                                        for line in block.text.split('\n'):
                                            if line.strip():
                                                job.add_log(line[:500], 'INFO')

                                final_message = response

                            if current_round >= max_rounds:
                                job.add_log('⚠️ Reached maximum tool rounds', 'WARNING')

                self.stdout.write('\n')

            # In a real implementation, Claude would execute Python code via tool use
            # For now, we'll show that the infrastructure is ready

            self.stdout.write(self.style.SUCCESS('\n✅ Agentic import completed'))
            self.stdout.write(self.style.WARNING(
                '\nℹ️  Note: Full code execution requires Claude with tool use enabled.'
            ))
            self.stdout.write(self.style.WARNING(
                'For full autonomy, use Claude Code or implement tool use handlers.'
            ))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Error during import: {str(e)}'))
            job.status = 'failed'
            job.save()
            job.add_log(f'Error: {str(e)}', 'ERROR')
            raise

    def _format_file_list(self, file_info):
        """Format file list for prompt"""
        lines = []
        for info in file_info:
            lines.append(f"- **{info['filename']}** ({info['type'].upper()}, {info['size']} bytes)")
            lines.append(f"  Location: `{info['path']}`")
        return '\n'.join(lines)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.persistent_globals = None  # Will store execution context across calls

    def _execute_tool(self, tool_name, tool_input, job):
        """Execute a tool requested by Claude"""
        try:
            if tool_name == "log_message":
                # Log message to dashboard
                level = tool_input.get('level', 'INFO')
                message = tool_input.get('message', '')
                job.add_log(message, level)
                return f"Logged: {message[:100]}"

            elif tool_name == "execute_python":
                # Execute Python code
                code = tool_input.get('code', '')

                # Import all necessary models
                from practice.models import (
                    Client, Attorney, Matter, TimeEntry, Expense,
                    Invoice, InvoiceLineItem, Payment, Document,
                    PracticeArea, Service,
                    ImportJob, ImportFile, ImportQuestion, ImportLog,
                    ImportMapping, ImportedRecord
                )
                import csv
                import json
                import requests
                from datetime import datetime, date
                from pathlib import Path
                import os

                # Initialize persistent globals on first call
                if self.persistent_globals is None:
                    self.persistent_globals = {
                        '__builtins__': __builtins__,
                        'job': job,
                        'Client': Client,
                        'Attorney': Attorney,
                        'Matter': Matter,
                        'TimeEntry': TimeEntry,
                        'Expense': Expense,
                        'Invoice': Invoice,
                        'InvoiceLineItem': InvoiceLineItem,
                        'Payment': Payment,
                        'Document': Document,
                        'PracticeArea': PracticeArea,
                        'Service': Service,
                        'ImportJob': ImportJob,
                        'ImportFile': ImportFile,
                        'ImportQuestion': ImportQuestion,
                        'ImportLog': ImportLog,
                        'ImportMapping': ImportMapping,
                        'ImportedRecord': ImportedRecord,
                        'datetime': datetime,
                        'date': date,
                        'csv': csv,
                        'json': json,
                        'requests': requests,
                        'Path': Path,
                        'os': os,
                        'open': open,
                        'print': print,
                        'len': len,
                        'str': str,
                        'int': int,
                        'float': float,
                        'list': list,
                        'dict': dict,
                    }

                # Use persistent globals so variables carry over between executions
                exec_globals = self.persistent_globals
                exec_locals = self.persistent_globals  # Use same dict for locals

                # Capture output
                from io import StringIO
                import sys

                old_stdout = sys.stdout
                sys.stdout = captured_output = StringIO()

                try:
                    # Execute the code
                    exec(code, exec_globals, exec_locals)

                    # Restore stdout
                    sys.stdout = old_stdout

                    # Get output
                    output = captured_output.getvalue()

                    # Return result variable if set, otherwise captured output, otherwise success message
                    if 'result' in exec_locals:
                        result = exec_locals['result']
                        return f"{result}\n{output}" if output else str(result)
                    elif output:
                        return output
                    else:
                        return "Code executed successfully (no output)"

                except Exception as exec_error:
                    sys.stdout = old_stdout
                    raise exec_error

            else:
                return f"Unknown tool: {tool_name}"

        except Exception as e:
            error_msg = f"Tool execution error: {str(e)}"
            job.add_log(error_msg, 'ERROR')
            return error_msg
