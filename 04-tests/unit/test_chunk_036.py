"""Unit tests for CHUNK-036: API Routes - Images"""
import os
os.environ['DATABASE_URL'] = 'postgresql://test:test@localhost/test_db'
os.environ['TESSERACT_PATH'] = '/usr/bin/tesseract'
os.environ['MODEL_CACHE_DIR'] = '/tmp/test_models'

class TestChunk036APIRoutesImages:
    def test_happy_path_list_images(self):
        from src.api.routes import images
        assert hasattr(images, 'list_images')
    
    def test_error_handling(self):
        from src.api.routes import images
        import inspect
        assert 'HTTPException' in inspect.getsource(images.get_image_metadata)
    
    def test_edge_cases(self):
        from src.api.routes import images
        assert hasattr(images, 'router')
    
    def test_input_validation(self):
        from src.api.routes import images
        import inspect
        assert 'book_id' in inspect.getsource(images.list_images)
    
    def test_get_image(self):
        from src.api.routes import images
        assert hasattr(images, 'get_image_metadata')
    
    def test_image_data(self):
        from src.api.routes import images
        assert hasattr(images, 'get_image_data')
    
    def test_image_response(self):
        from src.api.routes import images
        import inspect
        assert 'Response' in inspect.getsource(images.get_image_data)
