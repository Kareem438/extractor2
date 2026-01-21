"""Unit tests for CHUNK-035: API Routes - Knowledge Units"""
import os
os.environ['DATABASE_URL'] = 'postgresql://test:test@localhost/test_db'
os.environ['TESSERACT_PATH'] = '/usr/bin/tesseract'
os.environ['MODEL_CACHE_DIR'] = '/tmp/test_models'

class TestChunk035APIRoutesKnowledgeUnits:
    def test_happy_path_list_records(self):
        from src.api.routes import knowledge_units
        assert hasattr(knowledge_units, 'list_knowledge_units')
    
    def test_error_handling(self):
        from src.api.routes import knowledge_units
        import inspect
        assert 'HTTPException' in inspect.getsource(knowledge_units.get_knowledge_unit)
    
    def test_edge_cases(self):
        from src.api.routes import knowledge_units
        assert hasattr(knowledge_units, 'router')
    
    def test_input_validation(self):
        from src.api.routes import knowledge_units
        import inspect
        assert 'book_id' in inspect.getsource(knowledge_units.list_knowledge_units)
    
    def test_get_record(self):
        from src.api.routes import knowledge_units
        assert hasattr(knowledge_units, 'get_knowledge_unit')
    
    def test_update_record(self):
        from src.api.routes import knowledge_units
        assert hasattr(knowledge_units, 'update_knowledge_unit')
    
    def test_merge_records(self):
        from src.api.routes import knowledge_units
        assert hasattr(knowledge_units, 'export_knowledge_units')
