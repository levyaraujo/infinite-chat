import asyncio
import datetime
import logging
import os
import re
import traceback
from typing import Dict, List

import httpx
from bs4 import BeautifulSoup
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from markdownify import markdownify as md

from back.infra.cache import redis_client
from infra.logs import setup_logging

BASE_URL = os.getenv("INFINITEPAY_BASE_URL", "https://ajuda.infinitepay.io/pt-BR")
COLLECTIONS_URL = os.getenv("INFINITEPAY_COLLECTIONS_URL", f"{BASE_URL}/collections")

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

logger = setup_logging(log_level=logging.INFO, redis_client=redis_client)

class RAGBuilder:
    def __init__(self, ollama_model: str = "nomic-embed-text",
                 db_connection: str = None):
        self.collections_urls = None
        self._articles_urls_by_category: Dict[str, List[str]] = {}
        self.headers = {
            "User-Agent": USER_AGENT
        }

        ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

        print(f"🔧 Configuring Ollama embeddings: {ollama_base_url} (model: {ollama_model})")

        self.embedding = OllamaEmbeddings(
            model=ollama_model,
            base_url=ollama_base_url
        )

    def check_collection_exists(self, collection_name: str = "infinitepay_help") -> bool:
        """Check if ChromaDB collection exists and has documents"""
        try:

            vectorstore = Chroma(
                collection_name=collection_name,
                embedding_function=self.embedding,
                persist_directory="/opt/vector_db"
            )

            test_results = vectorstore.similarity_search("test", k=1)
            count = len(test_results) if test_results else 0

            return count > 0

        except Exception as e:
            return False

    def _get_collections_urls(self):
        response = httpx.get(BASE_URL)
        soup = BeautifulSoup(response.text, "html.parser")

        links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.startswith(COLLECTIONS_URL):
                links.append(href)
        return links

    def _get_articles_by_collections(self) -> Dict[str, List[str]]:
        articles = {}
        for collection in self.collections_urls:
            response = httpx.get(collection)
            soup = BeautifulSoup(response.text, "html.parser")

            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.startswith(f"{BASE_URL}/articles"):
                    if not articles.get(collection):
                        articles[collection] = [href]
                    else:
                        articles[collection].append(href)

        return articles

    def _clean_markdown(self, content: str, title: str) -> str:
        lines = content.split('\n')
        cleaned_lines = []

        for line in lines:
            line = line.strip()

            if not cleaned_lines and not line:
                continue

            if any(skip in line.lower() for skip in [
                'atualizado há', 'updated', 'last modified', 'sumário', 'summary'
            ]):
                continue

            if line and not cleaned_lines:
                if not line.startswith('#'):
                    cleaned_lines.append(f"# {title}")
                cleaned_lines.append(line)
            else:
                cleaned_lines.append(line)

        content = '\n'.join(cleaned_lines)
        content = re.sub(r'\n{3,}', '\n\n', content)

        return content.strip()

    def extract_article_content(self, html_content: str, url: str) -> Dict:
        """Enhanced content extraction with better structure preservation"""
        soup = BeautifulSoup(html_content, 'html.parser')

        # Find main content
        content_selectors = ['.article', 'article', '.main-content', '.content']
        content = None
        for selector in content_selectors:
            content = soup.select_one(selector)
            if content:
                break

        if not content:
            content = soup.find('body')

        if not content:
            return {'title': 'Unknown', 'content': 'Could not extract content', 'url': url}

        # Remove unwanted elements
        for tag in soup(["script", "style", "footer", "header", "nav", "aside",
                         ".sidebar", ".footer", ".header", ".nav", ".advertisement"]):
            tag.decompose()

        # Remove help/contact sections
        cutoff_patterns = [
            lambda tag: tag.name == 'p' and any(phrase in tag.get_text().lower()
                                                for phrase in ['precisa de ajuda', 'entre em contato',
                                                               'fale conosco', 'suporte']),
            lambda tag: tag.name and 'footer' in tag.get('class', []),
            lambda tag: tag.name and 'contact' in tag.get('class', [])
        ]

        for pattern in cutoff_patterns:
            cutoff = content.find(pattern)
            if cutoff:
                for sibling in list(cutoff.find_all_next()):
                    sibling.decompose()
                cutoff.decompose()

        title = None
        title_selectors = ['h1', '.title', '.article-title', '.page-title', 'title']
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title = title_elem.get_text(strip=True)
                if title and len(title) > 3:
                    break

        if not title:
            title = url.split('/')[-1].replace('-', ' ').title()

        markdown_content = md(str(content),
                              heading_style="ATX",
                              bullets="-",
                              strip=['a'])

        markdown_content = self._clean_markdown(markdown_content, title)

        return {
            'title': title,
            'content': markdown_content,
            'url': url
        }

    async def load_single_article(self, url: str) -> Document:
        try:
            async with httpx.AsyncClient(headers=self.headers) as client:
                response = await client.get(url)
                response.raise_for_status()

                article_data = self.extract_article_content(response.text, url)

                doc = Document(
                    page_content=article_data['content'],
                    metadata={
                        'source': url,
                        'title': article_data['title'],
                        'url': url
                    }
                )

                return doc

        except Exception as e:
            print(f"Error loading article {url}: {e}")
            return Document(
                page_content=f"Error loading content: {e}",
                metadata={'source': url, 'error': str(e)}
            )

    async def load_documents_from_articles(self):
        all_documents = []

        for collection, articles in self._articles_urls_by_category.items():
            print(f"\n🔄 Processing collection: {collection}")
            print(f"   Articles to process: {len(articles)}")

            batch_size = 10
            for i in range(0, len(articles), batch_size):
                batch = articles[i:i + batch_size]

                tasks = [self.load_single_article(url) for url in batch]
                batch_docs = await asyncio.gather(*tasks)

                all_documents.extend(batch_docs)

                if batch_docs and batch_docs[0].page_content:
                    print(
                        f"   ✓ Batch {i // batch_size + 1}/{(len(articles) + batch_size - 1) // batch_size} completed")

        print(f"\n✅ Total documents loaded: {len(all_documents)}")
        return all_documents

    async def _split_documents(self, documents: List[Document]):
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1200,
            chunk_overlap=200,
            separators=[
                "\n# ",
                "\n## ",
                "\n### ",
                "\n\n",
                "\n",
                ". ",
                "? ",
                "! ",
                " ",
                ""
            ],
            length_function=len,
            is_separator_regex=False,
        )
        enhanced_chunks = []

        for doc in documents:
            if len(doc.page_content.strip()) < 200:
                continue

            chunks = splitter.split_documents([doc])

            for i, chunk in enumerate(chunks):
                chunk_content = self._clean_chunk_content(chunk.page_content)

                if len(chunk_content.strip()) < 50:
                    continue

                if not self._is_meaningful_chunk(chunk_content):
                    continue

                if not chunk_content.strip().startswith('#'):
                    title = doc.metadata.get('title', '')
                    if title and title.lower() not in chunk_content.lower():
                        chunk_content = f"# {title}\n\n{chunk_content}"

                chunk.page_content = chunk_content

                chunk.metadata.update({
                    'chunk_id': f"{doc.metadata.get('source', 'unknown')}_{i}",
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'has_heading': chunk_content.strip().startswith('#'),
                    'word_count': len(chunk_content.split()),
                    'original_title': doc.metadata.get('title', ''),
                    'source_url': doc.metadata.get('source', ''),
                })

                enhanced_chunks.append(chunk)

        return enhanced_chunks

    def _clean_chunk_content(self, content: str) -> str:
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = re.sub(r'[ \t]+', ' ', content)

        content = re.sub(r'\*{3,}', '', content)
        content = re.sub(r'-{3,}', '', content)

        content = re.sub(r'\n\s*\n\s*-', '\n-', content)

        return content.strip()

    def _is_meaningful_chunk(self, content: str) -> bool:
        text = re.sub(r'[#*\-\n]', ' ', content).strip()
        words = text.split()

        if len(words) < 5:
            return False

        metadata_patterns = [
            'atualizado há', 'updated', 'sumário', 'summary', 'índice',
            'voltar', 'próximo', 'anterior', 'home', 'início'
        ]

        if any(pattern in text.lower() for pattern in metadata_patterns):
            return False

        return len([w for w in words if len(w) > 3]) >= 3

    async def save_to_vectordb(self, documents: List[Document], collection_name: str = "infinitepay_help"):
        try:
            vectorstore = Chroma.from_documents(
                collection_name=collection_name,
                documents=documents,
                embedding=self.embedding,
                persist_directory="/opt/vector_db"
            )

            texts = [doc.page_content for doc in documents]
            metadatas = [doc.metadata for doc in documents]

            batch_size = 200
            total_batches = (len(texts) + batch_size - 1) // batch_size
            print(f"📦 Processing {total_batches} optimized batches...")

            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                batch_metadatas = metadatas[i:i + batch_size]

                batch_num = i // batch_size + 1
                print(f"   Batch {batch_num}/{total_batches} ({len(batch_texts)} docs)")

                vectorstore.add_texts(
                    texts=batch_texts,
                    metadatas=batch_metadatas,
                )

            print(f"✅ Successfully saved {len(documents)} documents to ChromaDB!")
            return vectorstore

        except Exception:
            logger.error(f"Error saving to ChromaDB", {
                "timestamp": datetime.now().isoformat(),
                "content": traceback.format_exc()
            })

    async def build_and_save_rag_system(self, collection_name: str = "infinitepay_help"):
        import time

        print("🚀 === Building and Saving RAG System (OPTIMIZED) ===")

        print("\n📥 1. Loading and splitting documents...")
        load_start = time.time()
        documents = await self.load_documents_from_articles()
        split_documents = await self._split_documents(documents)
        load_time = time.time() - load_start

        print("🏷️  Adding metadata to chunks...")
        for i, doc in enumerate(split_documents):
            doc.metadata.update({
                'chunk_id': f"{doc.metadata.get('source', 'unknown')}_{i}",
                'chunk_index': i,
                'total_chunks': len(split_documents)
            })

        print(f"✅ Created {len(split_documents)} document chunks in {load_time:.2f}s")

        print("\n💾 2. Saving to ChromaDB...")
        vectorstore = await self.save_to_vectordb(split_documents, collection_name)

        return vectorstore, split_documents

    async def _build_documents(self):
        collection_name = "infinitepay_help"
        if not self.check_collection_exists(collection_name):
            self.collections_urls = self._get_collections_urls()
            self._articles_urls_by_category = self._get_articles_by_collections()
            print("🔄 No existing vector database found. Building from scratch...")
            print("📥 Loading and processing documents...")

            try:
                await self.build_and_save_rag_system(collection_name)
                print("✅ Vector database created successfully!")
            except Exception as e:
                print(f"❌ Error building vector database: {e}")
                return

async def build_rag_documents():
    builder = RAGBuilder()

    await builder._build_documents()