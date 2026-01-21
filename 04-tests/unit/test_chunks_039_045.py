"""Tests for CHUNK-039 through CHUNK-045"""
import os
import pytest

os.environ['DATABASE_URL'] = 'postgresql://test:test@localhost/test_db'
os.environ['TESSERACT_PATH'] = '/usr/bin/tesseract'
os.environ['MODEL_CACHE_DIR'] = '/tmp/test_models'


class TestChunk039HTMLTemplate:
    def test_upload_html_exists(self):
        assert os.path.exists('03-code/src/frontend/templates/upload.html')
    
    def test_html_has_form(self):
        with open('03-code/src/frontend/templates/upload.html') as f:
            content = f.read()
            assert '<form' in content
            assert 'upload-form' in content


class TestChunk040JavaScriptUpload:
    def test_upload_js_exists(self):
        assert os.path.exists('03-code/src/frontend/static/js/upload.js')
    
    def test_js_has_upload_logic(self):
        with open('03-code/src/frontend/static/js/upload.js') as f:
            content = f.read()
            assert 'fetch' in content
            assert '/api/upload' in content


class TestChunk041DatabaseInit:
    def test_init_script_exists(self):
        assert os.path.exists('03-code/scripts/init_db.py')
    
    def test_init_has_function(self):
        with open('03-code/scripts/init_db.py') as f:
            content = f.read()
            assert 'init_database' in content


class TestChunk042FrontendCSS:
    def test_css_exists(self):
        assert os.path.exists('03-code/src/frontend/static/css/main.css')
    
    def test_css_has_styles(self):
        with open('03-code/src/frontend/static/css/main.css') as f:
            content = f.read()
            assert 'upload-container' in content or 'body' in content


class TestChunk043Requirements:
    def test_requirements_exists(self):
        assert os.path.exists('requirements.txt')
    
    def test_requirements_has_fastapi(self):
        with open('requirements.txt') as f:
            content = f.read()
            assert 'fastapi' in content.lower()


class TestChunk044Configuration:
    def test_env_example_exists(self):
        assert os.path.exists('.env.example')
    
    def test_env_has_database_url(self):
        with open('.env.example') as f:
            content = f.read()
            assert 'DATABASE_URL' in content


class TestChunk045Documentation:
    def test_implementation_doc_exists(self):
        assert os.path.exists('IMPLEMENTATION.md')
    
    def test_doc_has_overview(self):
        with open('IMPLEMENTATION.md') as f:
            content = f.read()
            assert 'CHUNK' in content or 'Implementation' in content
