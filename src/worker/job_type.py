from enum import Enum


class JobType(str, Enum):
	INGEST_DOCUMENT = "ingest_document"
	QUERY_RAG = "query_rag"