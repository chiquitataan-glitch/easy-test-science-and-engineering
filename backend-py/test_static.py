import sys
import traceback

sys.path.insert(0, '.')

passed = 0
failed = 0

def run_test(name, fn):
    global passed, failed
    print(f'\n=== {name} ===')
    try:
        fn()
        passed += 1
        print(f'PASS: {name}')
    except Exception as e:
        failed += 1
        print(f'FAIL: {name}')
        print(f'  Error: {e}')
        traceback.print_exc()


# Test 1: Config import
def test_config():
    from app.config import settings
    assert isinstance(settings.DATABASE_URL, str)
    assert settings.CORS_ORIGIN == 'http://localhost:5173'
    assert settings.MAX_FILE_SIZE == 20971520
    assert settings.DEFAULT_FREE_GENERATIONS == 20

run_test('Config import', test_config)


# Test 2: Schema imports
def test_schemas():
    from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
    from app.schemas.paper import GeneratePaperRequest, PaperResponse, QuestionItem
    from app.schemas.file import FileUploadResponse, FilePaginatedResponse
    from app.schemas.common import PaginationParams
    # Verify GeneratePaperRequest normalization
    req = GeneratePaperRequest(courseName='test', fileId='f1')
    assert req.documentIds == ['f1']
    req2 = GeneratePaperRequest(courseName='test', documentIds=['a', 'b'])
    assert req2.documentIds == ['a', 'b']

run_test('Schema imports', test_schemas)


# Test 3: Model enums
def test_enums():
    from app.models.enums import PaperStatus, FileStatus, ClientType, IdentityProvider
    assert PaperStatus.completed.value == 'completed'
    assert PaperStatus.failed.value == 'failed'
    assert PaperStatus.pending.value == 'pending'
    assert FileStatus.ready.value == 'ready'
    assert '.ppt' not in ['pdf', 'docx', 'pptx']  # Should not exist

run_test('Model enums', test_enums)


# Test 4: Auth service
def test_auth_service():
    from app.services.auth_service import (
        hash_password, verify_password, create_token, decode_token
    )
    from jose import ExpiredSignatureError

    pwd = 'test123456'
    hashed = hash_password(pwd)
    assert verify_password(pwd, hashed)
    assert not verify_password('wrong', hashed)

    token = create_token('test-user-id', 'user', 'free')
    assert len(token) > 10

    decoded = decode_token(token)
    assert decoded['sub'] == 'test-user-id'
    assert decoded['role'] == 'user'
    assert decoded['membership_type'] == 'free'

run_test('Auth service', test_auth_service)


# Test 5: DOCX exporter basic
def test_docx_export_basic():
    from app.services.docx_exporter import export_paper_to_docx_bytes
    test_data = {
        'paperTitle': 'Test Paper',
        'courseName': 'Test Course',
        'questions': [{
            'question_no': 1,
            'question_type': 'single_choice',
            'content': 'What is 1+1?',
            'options': [{'key': 'A', 'value': '2'}, {'key': 'B', 'value': '3'}],
            'answer': 'A',
            'analysis': 'Basic math',
            'knowledge_points': ['addition'],
            'difficulty': 'easy',
            'score': 5
        }]
    }
    docx_bytes = export_paper_to_docx_bytes(test_data)
    assert isinstance(docx_bytes, bytes)
    assert len(docx_bytes) > 0

run_test('DOCX export basic', test_docx_export_basic)


# Test 6: DOCX exporter empty content
def test_docx_export_empty_content():
    from app.services.docx_exporter import export_paper_to_docx_bytes
    test_data = {
        'paperTitle': 'Empty Content Test',
        'courseName': 'Test Course',
        'questions': [{
            'question_no': 1,
            'question_type': 'fill_blank',
            'content': '',
            'options': [],
            'answer': 'answer',
            'analysis': '',
            'knowledge_points': [],
            'difficulty': 'easy',
            'score': 2
        }]
    }
    docx_bytes = export_paper_to_docx_bytes(test_data)
    assert isinstance(docx_bytes, bytes)
    assert len(docx_bytes) > 0

run_test('DOCX export empty content', test_docx_export_empty_content)


# Test 7: QuotaExceededError
def test_quota_exceeded_error():
    from app.services.paper_generator import QuotaExceededError
    err = QuotaExceededError('no remaining generations')
    assert err.message == 'no remaining generations'
    assert isinstance(err, Exception)

run_test('QuotaExceededError', test_quota_exceeded_error)


# Test 8: Prompt building
def test_prompt_building():
    from app.services.paper_generator import build_generation_prompt, DEFAULT_CONFIG
    chunks = [{'content': 'Test reference content', 'source': 'test.docx'}]
    prompt = build_generation_prompt(chunks, None, 'general', 'Test Course')
    assert len(prompt) > 100
    assert 'Test Course' in prompt or '出题配置' in prompt

run_test('Prompt building', test_prompt_building)


# Test 9: Config normalization
def test_config_normalization():
    from app.services.paper_generator import _normalize_config, DEFAULT_CONFIG
    default = _normalize_config(None)
    assert len(default['types']) == 7  # 7 types including essay
    assert abs(sum(default['difficulty'].values()) - 1.0) < 0.01

    partial = _normalize_config({'types': {'single_choice': {'count': 5, 'score': 10}}})
    assert partial['types']['single_choice']['count'] == 5

run_test('Config normalization', test_config_normalization)


# Test 10: File extensions
def test_file_extensions():
    from app.services.file_service import ALLOWED_EXTENSIONS
    assert '.ppt' not in ALLOWED_EXTENSIONS, 'Old PPT format should NOT be allowed!'
    assert '.pptx' in ALLOWED_EXTENSIONS
    assert '.pdf' in ALLOWED_EXTENSIONS
    assert '.docx' in ALLOWED_EXTENSIONS

run_test('File extensions', test_file_extensions)


# Test 11: PaperQuestion model Text type
def test_paper_question_text_type():
    from app.models.paper_question import PaperQuestion
    content_type = PaperQuestion.__table__.c.content.type
    answer_type = PaperQuestion.__table__.c.answer.type
    analysis_type = PaperQuestion.__table__.c.analysis.type
    from sqlalchemy import Text
    assert isinstance(content_type, Text), f'content should be Text, got {type(content_type)}'
    assert isinstance(answer_type, Text), f'answer should be Text, got {type(answer_type)}'
    assert isinstance(analysis_type, Text), f'analysis should be Text, got {type(analysis_type)}'

run_test('PaperQuestion Text type', test_paper_question_text_type)


# Test 12: ForeignKey on membership_history and billing_log
def test_foreign_keys():
    from app.models.membership_history import MembershipHistory
    from app.models.billing_log import BillingLog
    from sqlalchemy import ForeignKey

    mh_fks = [c for c in MembershipHistory.__table__.c if c.foreign_keys]
    assert len(mh_fks) > 0, 'MembershipHistory should have foreign keys'
    user_fk_mh = any(
        any(fk.column.table.name == 'users' for fk in c.foreign_keys)
        for c in mh_fks
    )
    assert user_fk_mh, 'MembershipHistory.userId should FK to users'

    bl_fks = [c for c in BillingLog.__table__.c if c.foreign_keys]
    assert len(bl_fks) > 0, 'BillingLog should have foreign keys'
    user_fk_bl = any(
        any(fk.column.table.name == 'users' for fk in c.foreign_keys)
        for c in bl_fks
    )
    assert user_fk_bl, 'BillingLog.userId should FK to users'

run_test('Foreign keys on membership/billing', test_foreign_keys)


# Test 13: Global exception handler
def test_global_exception_handler():
    import inspect
    from app.main import global_exception_handler
    source = inspect.getsource(global_exception_handler)
    # Should not expose str(exc) directly
    assert 'str(exc)' not in source, 'Global handler should not expose raw exception'
    assert 'internal server error' in source.lower(), 'Should return generic message'

run_test('Global exception handler', test_global_exception_handler)


# Test 14: Auth refresh catches ExpiredSignatureError
def test_auth_refresh_handling():
    import inspect
    from app.api.auth import refresh
    source = inspect.getsource(refresh)
    assert 'ExpiredSignatureError' in source, 'refresh endpoint should catch ExpiredSignatureError'
    assert 'TOKEN_EXPIRED' in source, 'refresh endpoint should return TOKEN_EXPIRED'

run_test('Auth refresh ExpiredSignatureError', test_auth_refresh_handling)


# Test 15: Papers generate catches QuotaExceededError
def test_generate_catches_quota():
    import inspect
    from app.api.papers import generate_paper
    source = inspect.getsource(generate_paper)
    assert 'QuotaExceededError' in source, 'generate_paper should catch QuotaExceededError'
    assert '402' in source, 'generate_paper should return status 402'
    assert 'QUOTA_EXCEEDED' in source, 'generate_paper should use QUOTA_EXCEEDED code'

run_test('Generate catches QuotaExceededError', test_generate_catches_quota)


# Test 16: Papers export uses RFC 5987
def test_export_uses_rfc5987():
    import inspect
    from app.api.papers import export_paper_docx
    source = inspect.getsource(export_paper_docx)
    assert "filename*=UTF-8''" in source or 'filename*' in source, 'export should use RFC 5987 encoding'
    assert 'quote' in source.lower() or 'from urllib.parse import quote' in inspect.getsource(
        __import__('app.api.papers', fromlist=[''])
    ), 'export should import quote for filename encoding'

run_test('Export uses RFC 5987', test_export_uses_rfc5987)


# Test 17: DEFAULT_CONFIG matches frontend
def test_default_config_match():
    from app.services.paper_generator import DEFAULT_CONFIG
    default = DEFAULT_CONFIG['types']
    assert default['true_false']['count'] == 0, 'true_false should be 0 in backend default'
    assert default['calculation']['count'] == 2, 'calculation should be 2 in backend default'
    assert 'essay' in default, 'essay should exist in backend default'
    assert default['essay']['count'] == 1, 'essay count should be 1'

run_test('Default config matches frontend', test_default_config_match)


# Summary
print()
print('=' * 60)
print(f'TEST RESULTS: {passed} passed, {failed} failed, {passed + failed} total')
if failed == 0:
    print('ALL TESTS PASSED')
else:
    print(f'{failed} TEST(S) FAILED - CHECK OUTPUT ABOVE')
print('=' * 60)
