"""
ChromaDB Input/Output Handler

Handles reading from and writing to ChromaDB for pipeline steps.
Supports embedding operations, semantic search, and metadata updates.
"""

from typing import Dict, Any, Optional, List
import chromadb
from chromadb.config import Settings
import logging

logger = logging.getLogger(__name__)


class ChromaDBHandler:
    """Handler for ChromaDB read/write operations"""

    def __init__(
        self,
        table_prefix: str,
        chroma_host: str = "localhost",
        chroma_port: int = 8000
    ):
        """
        Initialize ChromaDB handler for a specific book.

        Args:
            table_prefix: Table prefix for this book (e.g., 'book1_example')
            chroma_host: ChromaDB server host
            chroma_port: ChromaDB server port
        """
        self.table_prefix = table_prefix
        self.chroma_host = chroma_host
        self.chroma_port = chroma_port

        # Initialize ChromaDB client
        self.client = chromadb.HttpClient(
            host=chroma_host,
            port=chroma_port,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=False
            )
        )

        # Collection names
        self.collection_name = f"{table_prefix}_embeddings"

    def get_or_create_collection(self):
        """Get or create the collection for this book"""
        try:
            collection = self.client.get_collection(name=self.collection_name)
        except Exception:
            # Collection doesn't exist, create it
            collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"table_prefix": self.table_prefix}
            )
            logger.info(f"Created ChromaDB collection: {self.collection_name}")

        return collection

    def upsert_embedding(
        self,
        entity_type: str,
        entity_id: int,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Generate and store embedding for text.

        Args:
            entity_type: 'paragraph' or 'diagram'
            entity_id: Entity ID
            text: Text to embed
            metadata: Additional metadata to store

        Returns:
            True if successful
        """
        collection = self.get_or_create_collection()

        # Create document ID
        doc_id = f"{entity_type}_{entity_id}"

        # Prepare metadata
        meta = {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "table_prefix": self.table_prefix
        }
        if metadata:
            meta.update(metadata)

        # Upsert to ChromaDB (will generate embedding automatically)
        collection.upsert(
            ids=[doc_id],
            documents=[text],
            metadatas=[meta]
        )

        logger.info(
            f"Upserted embedding for {entity_type} {entity_id} "
            f"with text length {len(text)}"
        )

        return True

    def semantic_search(
        self,
        entity_type: str,
        entity_id: int,
        max_results: int = 5,
        include_self: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Find similar records to the given entity using semantic search.

        Args:
            entity_type: 'paragraph' or 'diagram'
            entity_id: Entity ID to find similar records for
            max_results: Maximum number of results to return
            include_self: Whether to include the query entity in results

        Returns:
            List of similar records with scores
            [
                {
                    "entity_type": "paragraph",
                    "entity_id": 123,
                    "distance": 0.25,
                    "text": "...",
                    "metadata": {...}
                },
                ...
            ]
        """
        collection = self.get_or_create_collection()

        # Get the current entity's embedding
        doc_id = f"{entity_type}_{entity_id}"

        try:
            # Get the entity
            result = collection.get(
                ids=[doc_id],
                include=["embeddings", "documents", "metadatas"]
            )

            if not result['embeddings']:
                logger.warning(
                    f"No embedding found for {entity_type} {entity_id}"
                )
                return []

            embedding = result['embeddings'][0]

            # Query for similar items
            query_results = collection.query(
                query_embeddings=[embedding],
                n_results=max_results + (1 if not include_self else 0),
                include=["documents", "metadatas", "distances"]
            )

            # Format results
            similar_records = []
            for i, doc_id in enumerate(query_results['ids'][0]):
                # Skip self if not included
                if not include_self and doc_id == f"{entity_type}_{entity_id}":
                    continue

                similar_records.append({
                    "entity_type": query_results['metadatas'][0][i].get('entity_type'),
                    "entity_id": query_results['metadatas'][0][i].get('entity_id'),
                    "distance": query_results['distances'][0][i],
                    "text": query_results['documents'][0][i],
                    "metadata": query_results['metadatas'][0][i]
                })

            # Limit to max_results
            return similar_records[:max_results]

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []

    def get_embedding(
        self,
        entity_type: str,
        entity_id: int
    ) -> Optional[List[float]]:
        """
        Retrieve the embedding vector for an entity.

        Args:
            entity_type: 'paragraph' or 'diagram'
            entity_id: Entity ID

        Returns:
            Embedding vector or None if not found
        """
        collection = self.get_or_create_collection()

        doc_id = f"{entity_type}_{entity_id}"

        try:
            result = collection.get(
                ids=[doc_id],
                include=["embeddings"]
            )

            if result['embeddings']:
                return result['embeddings'][0]
            return None

        except Exception as e:
            logger.error(f"Failed to get embedding: {e}")
            return None

    def get_metadata(
        self,
        entity_type: str,
        entity_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve stored metadata for an entity.

        Args:
            entity_type: 'paragraph' or 'diagram'
            entity_id: Entity ID

        Returns:
            Metadata dictionary or None if not found
        """
        collection = self.get_or_create_collection()

        doc_id = f"{entity_type}_{entity_id}"

        try:
            result = collection.get(
                ids=[doc_id],
                include=["metadatas"]
            )

            if result['metadatas']:
                return result['metadatas'][0]
            return None

        except Exception as e:
            logger.error(f"Failed to get metadata: {e}")
            return None

    def update_metadata(
        self,
        entity_type: str,
        entity_id: int,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Update metadata fields in ChromaDB.

        Args:
            entity_type: 'paragraph' or 'diagram'
            entity_id: Entity ID
            metadata: Metadata fields to update

        Returns:
            True if successful
        """
        collection = self.get_or_create_collection()

        doc_id = f"{entity_type}_{entity_id}"

        try:
            # Get existing metadata
            existing = self.get_metadata(entity_type, entity_id)

            if existing is None:
                logger.warning(
                    f"Cannot update metadata for non-existent entity: "
                    f"{entity_type} {entity_id}"
                )
                return False

            # Merge metadata
            updated_metadata = {**existing, **metadata}

            # Update
            collection.update(
                ids=[doc_id],
                metadatas=[updated_metadata]
            )

            logger.info(f"Updated metadata for {entity_type} {entity_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update metadata: {e}")
            return False

    def delete_entry(
        self,
        entity_type: str,
        entity_id: int
    ) -> bool:
        """
        Remove an entry from ChromaDB.

        Args:
            entity_type: 'paragraph' or 'diagram'
            entity_id: Entity ID

        Returns:
            True if successful
        """
        collection = self.get_or_create_collection()

        doc_id = f"{entity_type}_{entity_id}"

        try:
            collection.delete(ids=[doc_id])
            logger.info(f"Deleted entry for {entity_type} {entity_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete entry: {e}")
            return False

    def format_similar_results(
        self,
        similar_records: List[Dict[str, Any]],
        format_type: str = "json"
    ) -> str:
        """
        Format similar search results for Claude prompt.

        Args:
            similar_records: List of similar records from semantic_search()
            format_type: 'json', 'numbered_list', or 'concatenated'

        Returns:
            Formatted string
        """
        if not similar_records:
            return "No similar records found."

        if format_type == "json":
            import json
            return json.dumps(similar_records, indent=2, ensure_ascii=False)

        elif format_type == "numbered_list":
            lines = []
            for i, record in enumerate(similar_records, 1):
                lines.append(
                    f"{i}. {record['text']} "
                    f"(similarity: {1 - record['distance']:.2f})"
                )
            return "\n".join(lines)

        elif format_type == "concatenated":
            return "\n\n---\n\n".join([r['text'] for r in similar_records])

        else:
            raise ValueError(f"Unknown format_type: {format_type}")
