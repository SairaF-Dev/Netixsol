import hashlib

import chromadb


class ChromaVectorStore:
    """
    Persistent ChromaDB vector store with incremental indexing.

    Documents are embedded only when they are new or changed.
    """

    def __init__(
        self,
        embedder,
        persist_directory="./chroma_db",
        collection_name="real_estate_documents",
    ):
        if embedder is None:
            raise ValueError(
                "embedder is required"
            )

        if not isinstance(collection_name, str):
            raise TypeError(
                "collection_name must be a string"
            )

        if not collection_name.strip():
            raise ValueError(
                "collection_name cannot be empty"
            )

        self.embedder = embedder

        self.client = chromadb.PersistentClient(
            path=persist_directory
        )

        self.collection = (
            self.client.get_or_create_collection(
                name=collection_name,
                metadata={
                    "hnsw:space": "cosine"
                },
            )
        )

    # ------------------------------------------------------------------
    # Hashing
    # ------------------------------------------------------------------

    @staticmethod
    def _content_hash(text: str) -> str:
        """
        Generate a deterministic SHA-256 hash
        for document content.
        """

        return hashlib.sha256(
            text.encode("utf-8")
        ).hexdigest()

    # ------------------------------------------------------------------
    # Source inspection
    # ------------------------------------------------------------------

    def _get_source_chunks(self, source: str):
        """
        Return existing chunks for one source document.
        """

        result = self.collection.get(
            where={
                "source": source
            },
            include=[
                "metadatas"
            ],
        )

        return result.get("ids", []), result.get(
            "metadatas", []
        )

    def _get_source_hash(self, source: str):
        """
        Return the stored document hash.

        All chunks belonging to the same source carry
        the same document hash.
        """

        _, metadatas = self._get_source_chunks(
            source
        )

        if not metadatas:
            return None

        return metadatas[0].get(
            "document_hash"
        )

    # ------------------------------------------------------------------
    # Incremental indexing
    # ------------------------------------------------------------------

    def sync_documents(self, documents):
        """
        Incrementally synchronize documents with ChromaDB.

        New documents:
            chunk embeddings are created.

        Unchanged documents:
            completely skipped.

        Changed documents:
            old chunks are deleted and new chunks
            are embedded and inserted.
        """

        if not documents:
            return {
                "added": 0,
                "updated": 0,
                "skipped": 0,
                "chunks_indexed": 0,
            }

        added = 0
        updated = 0
        skipped = 0
        chunks_indexed = 0

        # Group chunks by source document.
        documents_by_source = {}

        for document in documents:

            if not isinstance(document, dict):
                raise TypeError(
                    "each document must be a dictionary"
                )

            source = document.get("source")
            text = document.get("text")

            if not source:
                raise ValueError(
                    "document source is required"
                )

            if not text or not text.strip():
                raise ValueError(
                    "document text cannot be empty"
                )

            documents_by_source.setdefault(
                source,
                []
            ).append(document)

        for source, chunks in (
            documents_by_source.items()
        ):

            # All chunks from the same source represent
            # one source document.
            combined_text = "\n".join(
                chunk["text"]
                for chunk in chunks
            )

            new_hash = self._content_hash(
                combined_text
            )

            old_hash = self._get_source_hash(
                source
            )

            # ----------------------------------------------------------
            # UNCHANGED DOCUMENT
            # ----------------------------------------------------------

            if old_hash == new_hash:
                skipped += 1
                continue

            # ----------------------------------------------------------
            # CHANGED / NEW DOCUMENT
            # ----------------------------------------------------------

            existing_ids, _ = (
                self._get_source_chunks(
                    source
                )
            )

            is_update = bool(existing_ids)

            if existing_ids:
                self.collection.delete(
                    ids=existing_ids
                )

            ids = []
            texts = []
            metadatas = []

            for chunk in chunks:

                chunk_id = chunk.get(
                    "chunk_id"
                )

                text = chunk.get("text")

                if chunk_id is None:
                    raise ValueError(
                        "document chunk_id is required"
                    )

                if not text or not text.strip():
                    raise ValueError(
                        "document text cannot be empty"
                    )

                document_id = (
                    f"{source}__chunk_{chunk_id}"
                )

                ids.append(document_id)
                texts.append(text)

                metadata = {
                    "source": source,
                    "chunk_id": int(chunk_id),
                    "document_hash": new_hash,
                }

                # Preserve optional metadata.
                for field in (
                    "property_name",
                    "property_id",
                    "document_type",
                ):
                    if field in chunk:
                        metadata[field] = str(
                            chunk[field]
                        )

                metadatas.append(metadata)

            # IMPORTANT:
            # Embeddings are generated ONLY here,
            # meaning only for new/changed documents.
            embeddings = (
                self.embedder.embed_many(
                    texts
                )
            )

            self.collection.upsert(
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
            )

            chunks_indexed += len(chunks)

            if is_update:
                updated += 1
            else:
                added += 1

        return {
            "added": added,
            "updated": updated,
            "skipped": skipped,
            "chunks_indexed": chunks_indexed,
        }

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        query,
        top_k=4,
        distance_threshold=None,
    ):
        """Search semantically similar chunks."""

        if not isinstance(query, str):
            raise TypeError(
                "query must be a string"
            )

        query = query.strip()

        if not query:
            raise ValueError(
                "query cannot be empty"
            )

        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than 0"
            )

        if (
            distance_threshold is not None
            and distance_threshold < 0
        ):
            raise ValueError(
                "distance_threshold cannot be negative"
            )

        # This is intentionally done for every USER QUERY.
        # We embed the query, NOT the documents.
        query_embedding = (
            self.embedder.embed(query)
        )

        results = self.collection.query(
            query_embeddings=[
                query_embedding
            ],
            n_results=top_k,
            include=[
                "documents",
                "metadatas",
                "distances",
            ],
        )

        if not results.get("documents"):
            return []

        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        output = []

        for text, metadata, distance in zip(
            documents,
            metadatas,
            distances,
        ):

            if (
                distance_threshold is not None
                and distance > distance_threshold
            ):
                continue

            output.append(
                {
                    "text": text,
                    "source": metadata["source"],
                    "chunk_id": metadata["chunk_id"],
                    "distance": float(distance),
                    "property_name": metadata.get(
                        "property_name",
                        "",
                    ),
                    "property_id": metadata.get(
                        "property_id",
                        "",
                    ),
                    "document_type": metadata.get(
                        "document_type",
                        "unknown",
                    ),
                }
            )

        return output

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def count(self):
        """Return number of indexed chunks."""

        return self.collection.count()

    def clear(self):
        """Delete all indexed chunks."""

        existing = self.collection.get(
            include=[]
        )

        ids = existing.get(
            "ids",
            []
        )

        if ids:
            self.collection.delete(
                ids=ids
            )