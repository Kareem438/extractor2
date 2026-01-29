"""
ChromaDB Service

Provides vector storage and semantic search capabilities for knowledge units.

Features:
- Store knowledge unit embeddings in ChromaDB
- Semantic search across all books
- Similarity matching for duplicate detection
- Book-specific and cross-book search
"""

from typing import List, Dict, Optional
import hashlib
from sqlalchemy import text
from src.database.connection import SessionLocal
from src.utils.logging_config import logger


class ChromaService:
    """
    Manages ChromaDB operations for knowledge units.
    """

    def __init__(self, persist_directory: str = "/mnt/h/12-extractor/chroma_db"):
        """
        Initialize ChromaDB service.

        Args:
            persist_directory: Path to persist ChromaDB data
        """
        self.persist_directory = persist_directory
        self.client = None
        self.collection = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize ChromaDB client and collection."""
        try:
            import chromadb
            from chromadb.config import Settings

            # Create persistent client
            self.client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(anonymized_telemetry=False)
            )

            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name="knowledge_base_unified",
                metadata={
                    "description": "Unified collection for all books",
                    "hnsw:space": "cosine"  # Use cosine similarity
                }
            )

            logger.info(f"ChromaDB initialized: {self.collection.count()} documents")

        except ImportError:
            logger.warning("ChromaDB not installed. Vector search will not be available.")
            self.client = None
            self.collection = None
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self.client = None
            self.collection = None

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding vector for text using sentence-transformers.

        Args:
            text: Input text

        Returns:
            Embedding vector or None if unavailable
        """
        try:
            from sentence_transformers import SentenceTransformer

            # Use a lightweight model (384 dimensions)
            model = SentenceTransformer('all-MiniLM-L6-v2')
            embedding = model.encode(text).tolist()

            return embedding

        except ImportError:
            logger.warning("sentence-transformers not installed. Cannot generate embeddings.")
            return None
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None

    def add_knowledge_unit(
        self,
        book_id: int,
        unit_id: int,
        text: str,
        metadata: Dict
    ) -> bool:
        """
        Add a knowledge unit to ChromaDB.

        Args:
            book_id: Book ID
            unit_id: Unit ID
            text: Text content
            metadata: Additional metadata

        Returns:
            True if successful, False otherwise
        """
        if not self.collection:
            logger.warning("ChromaDB not initialized. Skipping vector storage.")
            return False

        try:
            # Generate unique ID
            doc_id = f"book{book_id}_unit{unit_id}"

            # Generate embedding
            embedding = self.generate_embedding(text)
            if not embedding:
                return False

            # Filter out None values from metadata (ChromaDB doesn't accept None)
            clean_metadata = {
                k: v for k, v in metadata.items()
                if v is not None
            }

            # Add to collection
            self.collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[text],
                metadatas=[{
                    "book_id": book_id,
                    "unit_id": unit_id,
                    **clean_metadata
                }]
            )

            logger.debug(f"Added unit {doc_id} to ChromaDB")
            return True

        except Exception as e:
            logger.error(f"Failed to add unit to ChromaDB: {e}")
            return False

    def add_knowledge_units_bulk(
        self,
        book_id: int,
        units: List[Dict]
    ) -> Dict[str, int]:
        """
        Add multiple knowledge units to ChromaDB in bulk.

        Args:
            book_id: Book ID
            units: List of unit dictionaries with 'unit_id', 'text', 'metadata'

        Returns:
            Dictionary with success/failure counts
        """
        if not self.collection:
            logger.warning("ChromaDB not initialized. Skipping vector storage.")
            return {"success": 0, "failed": len(units)}

        try:
            ids = []
            embeddings = []
            documents = []
            metadatas = []

            for unit in units:
                # Generate unique ID
                doc_id = f"book{book_id}_unit{unit['unit_id']}"

                # Generate embedding
                embedding = self.generate_embedding(unit['text'])
                if not embedding:
                    continue

                # Filter out None values from metadata (ChromaDB doesn't accept None)
                clean_metadata = {
                    k: v for k, v in unit.get('metadata', {}).items()
                    if v is not None
                }

                ids.append(doc_id)
                embeddings.append(embedding)
                documents.append(unit['text'])
                metadatas.append({
                    "book_id": book_id,
                    "unit_id": unit['unit_id'],
                    **clean_metadata
                })

            # Bulk add
            if ids:
                self.collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas
                )

            logger.info(f"Added {len(ids)} units to ChromaDB for book {book_id}")
            return {"success": len(ids), "failed": len(units) - len(ids)}

        except Exception as e:
            logger.error(f"Failed to bulk add units to ChromaDB: {e}")
            return {"success": 0, "failed": len(units)}

    def search_similar(
        self,
        query_text: str,
        n_results: int = 10,
        book_id: Optional[int] = None
    ) -> List[Dict]:
        """
        Search for similar knowledge units.

        Args:
            query_text: Query text
            n_results: Number of results to return
            book_id: Optional book ID to filter results

        Returns:
            List of matching units with similarity scores
        """
        if not self.collection:
            logger.warning("ChromaDB not initialized. Cannot perform search.")
            return []

        try:
            # Generate query embedding
            query_embedding = self.generate_embedding(query_text)
            if not query_embedding:
                return []

            # Build filter
            where_filter = None
            if book_id:
                where_filter = {"book_id": book_id}

            # Query collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_filter
            )

            # Format results
            matches = []
            if results and results['ids']:
                for i, doc_id in enumerate(results['ids'][0]):
                    matches.append({
                        'doc_id': doc_id,
                        'text': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'distance': results['distances'][0][i] if 'distances' in results else None
                    })

            logger.info(f"Found {len(matches)} similar units for query")
            return matches

        except Exception as e:
            logger.error(f"Failed to search ChromaDB: {e}")
            return []

    def delete_book_units(self, book_id: int) -> bool:
        """
        Delete all units for a specific book.

        Args:
            book_id: Book ID

        Returns:
            True if successful
        """
        if not self.collection:
            return False

        try:
            # Query for all units of this book
            results = self.collection.get(
                where={"book_id": book_id}
            )

            if results and results['ids']:
                # Delete all matching IDs
                self.collection.delete(ids=results['ids'])
                logger.info(f"Deleted {len(results['ids'])} units for book {book_id}")

            return True

        except Exception as e:
            logger.error(f"Failed to delete book units from ChromaDB: {e}")
            return False

    def delete_by_book_id(self, book_id: int) -> int:
        """
        Delete all embeddings for a specific book and return count deleted.

        Args:
            book_id: Book ID

        Returns:
            Number of embeddings deleted
        """
        if not self.collection:
            return 0

        try:
            # Query for all units of this book
            results = self.collection.get(
                where={"book_id": book_id}
            )

            count = 0
            if results and results['ids']:
                count = len(results['ids'])
                # Delete all matching IDs
                self.collection.delete(ids=results['ids'])
                logger.info(f"Deleted {count} embeddings for book {book_id}")

            return count

        except Exception as e:
            logger.error(f"Failed to delete book embeddings from ChromaDB: {e}")
            return 0

    def count_by_book_id(self, book_id: int) -> int:
        """
        Count embeddings for a specific book.

        Args:
            book_id: Book ID

        Returns:
            Number of embeddings for this book
        """
        if not self.collection:
            return 0

        try:
            # Query for all units of this book
            results = self.collection.get(
                where={"book_id": book_id}
            )

            if results and results['ids']:
                return len(results['ids'])
            return 0

        except Exception as e:
            logger.error(f"Failed to count book embeddings in ChromaDB: {e}")
            return 0

    def update_knowledge_unit(
        self,
        book_id: int,
        unit_id: int,
        text: str,
        metadata: Dict
    ) -> bool:
        """
        Update a knowledge unit in ChromaDB.

        Args:
            book_id: Book ID
            unit_id: Unit ID
            text: Updated text content
            metadata: Updated metadata

        Returns:
            True if successful
        """
        if not self.collection:
            return False

        try:
            doc_id = f"book{book_id}_unit{unit_id}"

            # Delete old version
            self.collection.delete(ids=[doc_id])

            # Add new version
            return self.add_knowledge_unit(book_id, unit_id, text, metadata)

        except Exception as e:
            logger.error(f"Failed to update unit in ChromaDB: {e}")
            return False

    async def sync_book_to_chroma(self, book_id: int, table_prefix: str) -> Dict[str, int]:
        """
        Synchronize all knowledge units from a book to ChromaDB.

        Args:
            book_id: Book ID
            table_prefix: Table prefix for this book

        Returns:
            Summary dictionary with sync statistics
        """
        if not self.collection:
            logger.warning("ChromaDB not initialized. Skipping sync.")
            return {"success": 0, "failed": 0, "total": 0}

        db = SessionLocal()
        try:
            # Get all knowledge units
            results = db.execute(
                text(f"""
                SELECT unit_id, text_content, page_number, verified,
                       chapter, topic, sub_topic, language
                FROM {table_prefix}_knowledge_units
                WHERE LENGTH(text_content) > 0
                ORDER BY unit_id
                """)
            ).fetchall()

            units = []
            for row in results:
                units.append({
                    'unit_id': row[0],
                    'text': row[1],
                    'metadata': {
                        'page_number': row[2],
                        'verified': row[3],
                        'chapter': row[4],
                        'topic': row[5],
                        'sub_topic': row[6],
                        'language': row[7]
                    }
                })

            # Bulk add to ChromaDB
            result = self.add_knowledge_units_bulk(book_id, units)
            result['total'] = len(units)

            logger.info(
                f"ChromaDB sync complete for book {book_id}: "
                f"{result['success']} success, {result['failed']} failed"
            )

            return result

        except Exception as e:
            logger.error(f"Failed to sync book to ChromaDB: {e}")
            return {"success": 0, "failed": 0, "total": 0}
        finally:
            db.close()

    def get_collection_stats(self) -> Dict:
        """
        Get statistics about the ChromaDB collection.

        Returns:
            Dictionary with collection statistics
        """
        if not self.collection:
            return {"status": "not_initialized", "count": 0}

        try:
            count = self.collection.count()
            return {
                "status": "active",
                "count": count,
                "name": self.collection.name,
                "persist_directory": self.persist_directory
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"status": "error", "count": 0}


# Singleton instance
_chroma_service_instance = None


def get_chroma_service() -> ChromaService:
    """Get singleton ChromaService instance."""
    global _chroma_service_instance
    if _chroma_service_instance is None:
        _chroma_service_instance = ChromaService()
    return _chroma_service_instance
