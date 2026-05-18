from pathlib import Path
from chromadb.utils import embedding_functions
import chromadb


# Chromadb 持久化存储路径，重启后数据不丢失
CHROMA_DB_PATH = Path(__file__).parent.parent / ".chromadb"

# 使用sentence-transformers 的轻量模型做向量化
# 使用 all-MiniLM-L6-v2: 384 维向量，速度快，中英文都支持
EMBEDDING_FN = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

VUE_DOCS_DIR = Path(__file__).parent / "vue_docs"

def get_client() -> chromadb.PersistentClient:
    """获取 ChromaDB 持久化客户端，数据存在 .chromadb/ 目录下。"""
    return chromadb.PersistentClient(path=str(CHROMA_DB_PATH))

def get_collection(client:chromadb.PersistentClient,name:str):
    """获取或创建指定 collection.
    get_or_create 保证幂等性：重复调用不会重复建建库。
    """
    return client.get_or_create_collection(
        name=name,
        embedding_function=EMBEDDING_FN,
        metadata={"hnsw:space":"cosine"}, # 用余弦相似度衡量语义距离
    )

def chunk_text(text:str,chunk_size: int = 300,overlap: int=50) -> list[str]:
    """把长文档切成固定大小的片段，相邻片段有overlap字符的重叠。
    重叠时为了避免把一个完整的知识点切断在两个片段边界
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

def index_vue_docs():
    """
    把 vue_docs/ 下 所有 .md 文件向量化并存入 vue_docs collection.
    已存在的文档会先删除再重建，保证内容是最新的。
    """
    client = get_client()
    collection = get_collection(client,"vue_docs")

    # 清空旧数据，避免重复索引
    existing = collection.get()
    if existing["ids"]:
        collection.delete(ids=existing["ids"])
        print(f"已清空旧索引，共 {len(existing['ids'])}条")
    
    docs, ids, metadatas = [], [], []
    doc_id = 0

    for md_file in sorted(VUE_DOCS_DIR.glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        chunks = chunk_text(text)

        for chunk in chunks:
            if not chunk.strip():
                continue
            docs.append(chunk)
            ids.append(f"vue_doc_{doc_id}")
            # metadata 记录来源文件，方便调试时追溯检索结果
            metadatas.append({"source": md_file.name})
            doc_id += 1
    
    collection.add(documents=docs,ids=ids,metadatas=metadatas)
    print(f"Vue 文档索引完成，共 {len(docs)} 个片段，来自{len(list(VUE_DOCS_DIR.glob('*.md')))}个文件")

def index_custom_rules(rules_text:str, source_name: str = "custom"):
    """
    把用户自定义规范文本向量化并存入 custom_rules collection.
    source_name 用于标识规范来源（如团队名、项目名）。
    """
    client = get_client()
    collection = get_collection(client,"custom_rules")

    chunks = chunk_text(rules_text)
    docs, ids, metadatas = [], [], []

    for i,chunk in enumerate(chunks):
        if not chunk.strip():
            continue
        docs.append(chunk)
        ids.append(f"custom_{source_name}_{i}")
        metadatas.append({"source": source_name})

    collection.add(documents=docs, ids=ids, metadatas=metadatas)
    print(f"自定义规范索引完成，共{ len(docs)} 个片段")

if __name__ == "__main__":
    # 直接运行此文件即可建立索引
    print("开始建立 Vue 文档索引...")
    index_vue_docs()
    