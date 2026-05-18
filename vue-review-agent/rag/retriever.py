from indexer import get_client,get_collection,EMBEDDING_FN

def retrieve(query:str, n_results: int = 3) -> str:
    """
    根据查询文本，从vue_docs 和 custom_rules 两个 colection 中
    各检索最相关的片段，合并后返回给 reviewer 注入 prompt.

    n_results: 每个 collection 返回的片段数，
    太多会撑大 prompt 增加token 成本，太少可能遗漏关键规则。
    """
    client = get_client()
    results = []

    for collection_name in ["vue_docs","custom_rules"]:
        try:
            collection = get_collection(client, collection_name)
            # 只有 collection 非空才检索， 避免空库报错
            if collection.count() == 0:
                continue
            res = collection.query(
                query_texts=[query],
                n_results=min(n_results, collection.count())
            )
            docs = res["documents"][0]
            sources = [m["source"] for m in res["metadatas"][0]]
            for doc, source in zip(docs, sources):
                results.append(f"[来源：{source}]\n{doc}")
        except Exception as e:
            # 某个 collection 检索失败不影响整体，降级忽略
            continue
    if not results:
        return "未检索到相关文档。"
    return "\n\n---\n\n".join(results)