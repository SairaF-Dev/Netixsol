from __future__ import annotations
import hashlib, json
import chromadb

class ChromaVectorStore:
    METADATA_FIELDS=('property_name','property_id','property_ids','document_type')
    def __init__(self,embedder,persist_directory='./chroma_db',collection_name='real_estate_documents'):
        if embedder is None: raise ValueError('embedder is required')
        if not isinstance(collection_name,str) or not collection_name.strip():
            raise ValueError('collection_name must be a non-empty string')
        self.embedder=embedder
        self.client=chromadb.PersistentClient(path=persist_directory)
        self.collection=self.client.get_or_create_collection(name=collection_name,metadata={'hnsw:space':'cosine'})
    @staticmethod
    def _fingerprint(chunks):
        payload=[{'text':c['text'], **{k:str(c.get(k,'')) for k in ChromaVectorStore.METADATA_FIELDS}} for c in chunks]
        raw=json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':'))
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()
    def _get_source_chunks(self,source):
        r=self.collection.get(where={'source':source},include=['metadatas'])
        return r.get('ids',[]),r.get('metadatas',[])
    def _get_source_hash(self,source):
        _,m=self._get_source_chunks(source); return m[0].get('document_hash') if m else None
    def _existing_sources(self):
        r=self.collection.get(include=['metadatas'])
        return {str(m.get('source')) for m in r.get('metadatas',[]) if m and m.get('source')}
    def sync_documents(self,documents):
        if not documents:
            r=self.collection.get(include=[]); ids=r.get('ids',[])
            if ids: self.collection.delete(ids=ids)
            return {'added':0,'updated':0,'skipped':0,'deleted_sources':0,'deleted_chunks':len(ids),'chunks_indexed':0}
        by_source={}
        for d in documents:
            if not isinstance(d,dict): raise TypeError('each document must be a dictionary')
            source=str(d.get('source','')).strip(); text=str(d.get('text','')).strip()
            if not source: raise ValueError('document source is required')
            if not text: raise ValueError('document text cannot be empty')
            by_source.setdefault(source,[]).append(d)
        stale=self._existing_sources()-set(by_source); deleted_chunks=0
        for source in sorted(stale):
            ids,_=self._get_source_chunks(source)
            if ids: self.collection.delete(ids=ids); deleted_chunks+=len(ids)
        added=updated=skipped=chunks_indexed=0
        for source,chunks in by_source.items():
            new_hash=self._fingerprint(chunks); old_hash=self._get_source_hash(source)
            if old_hash==new_hash: skipped+=1; continue
            old_ids,_=self._get_source_chunks(source); is_update=bool(old_ids)
            if old_ids: self.collection.delete(ids=old_ids)
            ids=[]; texts=[]; metas=[]
            for c in chunks:
                cid=c.get('chunk_id'); text=str(c.get('text','')).strip()
                if cid is None: raise ValueError('document chunk_id is required')
                ids.append(f'{source}__chunk_{cid}'); texts.append(text)
                meta={'source':source,'chunk_id':int(cid),'document_hash':new_hash}
                for field in self.METADATA_FIELDS:
                    if field in c: meta[field]=str(c[field])
                metas.append(meta)
            embeddings=self.embedder.embed_many(texts)
            self.collection.upsert(ids=ids,documents=texts,embeddings=embeddings,metadatas=metas)
            chunks_indexed+=len(chunks); updated+=int(is_update); added+=int(not is_update)
        return {'added':added,'updated':updated,'skipped':skipped,'deleted_sources':len(stale),'deleted_chunks':deleted_chunks,'chunks_indexed':chunks_indexed}
    def search(self,query,top_k=4,distance_threshold=None,metadata_filter=None):
        if not isinstance(query,str): raise TypeError('query must be a string')
        query=query.strip()
        if not query: raise ValueError('query cannot be empty')
        if top_k<=0: raise ValueError('top_k must be greater than 0')
        if distance_threshold is not None and distance_threshold<0: raise ValueError('distance_threshold cannot be negative')
        count=self.collection.count()
        if count<=0: return []
        kwargs={'query_embeddings':[self.embedder.embed(query)],'n_results':min(top_k,count),'include':['documents','metadatas','distances']}
        if metadata_filter: kwargs['where']=metadata_filter
        r=self.collection.query(**kwargs)
        if not r.get('documents'): return []
        out=[]
        for text,meta,distance in zip(r['documents'][0],r['metadatas'][0],r['distances'][0]):
            if distance_threshold is not None and distance>distance_threshold: continue
            out.append({'text':text,'source':meta['source'],'chunk_id':meta['chunk_id'],'distance':float(distance),'property_name':meta.get('property_name',''),'property_id':meta.get('property_id',''),'property_ids':meta.get('property_ids',''),'document_type':meta.get('document_type','unknown')})
        return out
    def count(self): return self.collection.count()
    def clear(self):
        r=self.collection.get(include=[]); ids=r.get('ids',[])
        if ids: self.collection.delete(ids=ids)
