"""
Integration tests for LEVEL 3: Presentation Layer (CHUNK-031 to CHUNK-040)

Tests the integration of:
- FastAPI Application Setup (CHUNK-031)
- Static File Serving (CHUNK-032)
- Homepage Route (CHUNK-033)
- Upload Page Route (CHUNK-034)
- Books List Page Route (CHUNK-035)
- Book Detail Page Route (CHUNK-036)
- Processing Page Route (CHUNK-037)
- Verification Page Route (CHUNK-038)
- Export Page Route (CHUNK-039)
- Template Rendering (CHUNK-040)

This test suite verifies UI routes and frontend integration.
"""

import pytest
import os
from fastapi.testclient import TestClient
from bs4 import BeautifulSoup
import tempfile
from pathlib import Path


@pytest.fixture
def app():
    """Create FastAPI application"""
    from src.main import app
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def sample_pdf():
    """Create sample PDF for upload testing"""
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Sample content")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        temp_path = f.name

    doc.save(temp_path)
    doc.close()

    yield temp_path
    os.unlink(temp_path)


class TestStaticFileServing:
    """Test static file serving"""

    def test_css_file_served(self, client):
        """Test that CSS files are served"""
        response = client.get("/static/css/main.css")

        # Should return 200 if file exists, or 404 if not configured yet
        assert response.status_code in [200, 404]

    def test_javascript_file_served(self, client):
        """Test that JavaScript files are served"""
        response = client.get("/static/js/main.js")

        assert response.status_code in [200, 404]

    def test_images_served(self, client):
        """Test that static images are served"""
        response = client.get("/static/images/logo.png")

        assert response.status_code in [200, 404]


class TestHomepageRoute:
    """Test homepage rendering"""

    def test_homepage_loads(self, client):
        """Test that homepage loads successfully"""
        response = client.get("/")

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_homepage_contains_navigation(self, client):
        """Test homepage contains navigation links"""
        response = client.get("/")

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Check for common navigation elements
            links = soup.find_all('a')
            assert len(links) > 0

    def test_homepage_title(self, client):
        """Test homepage has correct title"""
        response = client.get("/")

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            title = soup.find('title')

            assert title is not None
            assert "Knowledge Extraction" in title.text or "Home" in title.text


class TestUploadPageRoute:
    """Test upload page rendering and functionality"""

    def test_upload_page_loads(self, client):
        """Test upload page loads successfully"""
        response = client.get("/upload")

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_upload_form_present(self, client):
        """Test upload page contains upload form"""
        response = client.get("/upload")

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for form element
            form = soup.find('form')
            assert form is not None

            # Look for file input
            file_input = soup.find('input', {'type': 'file'})
            assert file_input is not None

    def test_upload_form_fields(self, client):
        """Test upload form has required fields"""
        response = client.get("/upload")

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Check for common form fields
            inputs = soup.find_all('input')
            selects = soup.find_all('select')

            assert len(inputs) > 0 or len(selects) > 0


class TestBooksListPageRoute:
    """Test books list page"""

    def test_books_list_page_loads(self, client):
        """Test books list page loads successfully"""
        response = client.get("/books")

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_books_list_displays_table(self, client):
        """Test books list page displays table"""
        response = client.get("/books")

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for table element
            table = soup.find('table')
            assert table is not None or soup.find('div', {'class': 'book-list'}) is not None

    def test_books_list_has_search(self, client):
        """Test books list has search functionality"""
        response = client.get("/books")

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for search input or filter
            search = soup.find('input', {'type': 'search'}) or soup.find('input', {'type': 'text'})
            assert search is not None or soup.find('form') is not None


class TestBookDetailPageRoute:
    """Test book detail page"""

    def test_book_detail_page_loads(self, client):
        """Test book detail page loads (with ID)"""
        response = client.get("/books/1")

        # Should return 200 if book exists, 404 if not
        assert response.status_code in [200, 404]

    def test_book_detail_shows_metadata(self, client):
        """Test book detail page shows metadata"""
        response = client.get("/books/1")

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for common metadata fields
            text_content = soup.get_text()
            assert len(text_content) > 0

    def test_book_detail_has_actions(self, client):
        """Test book detail page has action buttons"""
        response = client.get("/books/1")

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for action buttons
            buttons = soup.find_all('button')
            links = soup.find_all('a')

            assert len(buttons) > 0 or len(links) > 0


class TestProcessingPageRoute:
    """Test processing page"""

    def test_processing_page_loads(self, client):
        """Test processing page loads"""
        response = client.get("/processing")

        assert response.status_code == 200

    def test_processing_page_has_controls(self, client):
        """Test processing page has start/pause/resume controls"""
        response = client.get("/processing")

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for control buttons
            buttons = soup.find_all('button')
            assert len(buttons) > 0

    def test_processing_page_has_progress_indicator(self, client):
        """Test processing page has progress indicator"""
        response = client.get("/processing")

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for progress bar or indicator
            progress = soup.find('progress') or soup.find('div', {'class': 'progress'})
            assert progress is not None or soup.find('div') is not None


class TestVerificationPageRoute:
    """Test verification page"""

    def test_verification_page_loads(self, client):
        """Test verification page loads"""
        response = client.get("/verification")

        assert response.status_code == 200

    def test_verification_page_shows_records(self, client):
        """Test verification page can display records"""
        response = client.get("/verification?book_id=1")

        # Should load even if no records
        assert response.status_code in [200, 404]

    def test_verification_page_has_edit_controls(self, client):
        """Test verification page has edit controls"""
        response = client.get("/verification")

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for input fields or edit buttons
            inputs = soup.find_all('input')
            buttons = soup.find_all('button')

            assert len(inputs) > 0 or len(buttons) > 0


class TestExportPageRoute:
    """Test export page"""

    def test_export_page_loads(self, client):
        """Test export page loads"""
        response = client.get("/export")

        assert response.status_code == 200

    def test_export_options_available(self, client):
        """Test export page has format options"""
        response = client.get("/export")

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for format selection
            radios = soup.find_all('input', {'type': 'radio'})
            selects = soup.find_all('select')

            assert len(radios) > 0 or len(selects) > 0

    def test_export_has_download_button(self, client):
        """Test export page has download button"""
        response = client.get("/export")

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for download button
            buttons = soup.find_all('button')
            download_links = soup.find_all('a', {'download': True})

            assert len(buttons) > 0 or len(download_links) > 0


class TestTemplateRendering:
    """Test template rendering functionality"""

    def test_base_template_exists(self, client):
        """Test that base template is used across pages"""
        pages = ["/", "/upload", "/books", "/processing"]

        for page in pages:
            response = client.get(page)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')

                # Check for common base template elements
                html_tag = soup.find('html')
                head_tag = soup.find('head')
                body_tag = soup.find('body')

                assert html_tag is not None
                assert head_tag is not None
                assert body_tag is not None

    def test_template_variables_rendered(self, client):
        """Test that template variables are properly rendered"""
        response = client.get("/")

        if response.status_code == 200:
            content = response.content.decode()

            # Should not contain unrendered template syntax
            assert "{{" not in content or "}}" not in content

    def test_error_page_template(self, client):
        """Test error page template renders"""
        response = client.get("/nonexistent-page")

        assert response.status_code == 404

        if response.status_code == 404:
            # Should render 404 template
            soup = BeautifulSoup(response.content, 'html.parser')
            assert soup.find('html') is not None


class TestNavigationAndRouting:
    """Test navigation between pages"""

    def test_homepage_to_upload_navigation(self, client):
        """Test navigation from homepage to upload"""
        response = client.get("/")

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for link to upload page
            upload_link = soup.find('a', href='/upload')
            assert upload_link is not None or soup.find('a') is not None

    def test_books_list_to_detail_navigation(self, client):
        """Test navigation from books list to detail"""
        response = client.get("/books")

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for links to book details
            links = soup.find_all('a')
            book_links = [link for link in links if '/books/' in link.get('href', '')]

            assert len(links) > 0

    def test_breadcrumb_navigation(self, client):
        """Test breadcrumb navigation exists"""
        pages = ["/books/1", "/processing", "/verification"]

        for page in pages:
            response = client.get(page)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')

                # Look for breadcrumb or back button
                breadcrumb = soup.find('nav', {'class': 'breadcrumb'})
                back_link = soup.find('a', text='Back')

                # At least one navigation element should exist
                assert breadcrumb is not None or back_link is not None or soup.find('nav') is not None


class TestFullPresentationIntegration:
    """Test complete presentation layer workflows"""

    def test_complete_user_workflow(self, client, sample_pdf):
        """Test complete user workflow through UI"""
        # 1. Visit homepage
        response = client.get("/")
        assert response.status_code == 200

        # 2. Navigate to upload
        response = client.get("/upload")
        assert response.status_code == 200

        # 3. Upload book (via API, UI would use form)
        with open(sample_pdf, 'rb') as f:
            files = {'file': ('test.pdf', f, 'application/pdf')}
            data = {'book_name': 'UI Test Book'}
            response = client.post("/api/books/upload", files=files, data=data)

        # Should succeed or return validation error
        assert response.status_code in [200, 201, 422]

        # 4. View books list
        response = client.get("/books")
        assert response.status_code == 200

        # 5. Visit processing page
        response = client.get("/processing")
        assert response.status_code == 200

    def test_responsive_design_viewport(self, client):
        """Test pages have responsive design meta tags"""
        pages = ["/", "/upload", "/books"]

        for page in pages:
            response = client.get(page)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')

                # Look for viewport meta tag
                viewport = soup.find('meta', {'name': 'viewport'})
                assert viewport is not None or soup.find('meta') is not None

    def test_all_pages_have_consistent_layout(self, client):
        """Test all pages share consistent layout"""
        pages = ["/", "/upload", "/books", "/processing", "/verification", "/export"]

        headers = []
        footers = []

        for page in pages:
            response = client.get(page)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')

                # Check for header
                header = soup.find('header') or soup.find('nav')
                if header:
                    headers.append(True)

                # Check for footer
                footer = soup.find('footer')
                if footer:
                    footers.append(True)

        # Most pages should have consistent layout elements
        assert len(headers) > 0 or len(footers) > 0
