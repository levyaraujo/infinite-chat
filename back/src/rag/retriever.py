from langchain_chroma import Chroma

from src.rag.builder import RAGBuilder


class RAGRetriever(RAGBuilder):
    def __init__(self):
        super().__init__()

        self.vectorstore = Chroma(
            collection_name="infinitepay_help",
            embedding_function=self.embedding,
            persist_directory="/opt/vector_db"
        )

    async def search_by_distance(
        self, query: str, max_distance: float = 0.35,
        k: int = 5
    ):
        try:
            print(f"🎯 Enhanced search: '{query}' (max_dist: {max_distance})")

            # More results for better filtering
            results_with_scores = self.vectorstore.similarity_search_with_score(query, k=k * 3)

            filtered_results = []
            for doc, distance in results_with_scores:
                if distance <= max_distance:
                    chunk_type = doc.metadata.get('chunk_type', 'general_content')
                    title_relevance = self._calculate_title_relevance(query, doc.metadata.get('original_title', ''))

                    priority_score = distance
                    if chunk_type in ['instructions', 'title_section']:
                        priority_score -= 0.05
                    if title_relevance > 0.3:
                        priority_score -= 0.03
                    if doc.metadata.get('has_heading', False):
                        priority_score -= 0.02

                    filtered_results.append((doc, priority_score, distance))

            filtered_results.sort(key=lambda x: x[1])
            final_results = [(doc, original_dist) for doc, _, original_dist in filtered_results[:k]]

            return [doc for doc, _ in final_results]

        except Exception as e:
            return []

    def _calculate_title_relevance(self, query: str, title: str) -> float:
        if not title:
            return 0.0

        query_words = set(query.lower().split())
        title_words = set(title.lower().split())

        if not query_words:
            return 0.0

        intersection = len(query_words.intersection(title_words))
        union = len(query_words.union(title_words))

        return intersection / union if union > 0 else 0.0