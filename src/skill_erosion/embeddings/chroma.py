import json
import logging
from pathlib import Path
import chromadb
from chromadb.config import Settings
from skill_erosion.config import ROOT
from skill_erosion.contracts.models import Resource
from skill_erosion.embeddings.local import embedding_function, MODEL_VERSION
log=logging.getLogger("skill_erosion")

class ChromaStore:
    model_version=MODEL_VERSION
    def __init__(self,path):
        path=Path(path).resolve()
        marker=path.parent/"chroma-server.json"
        settings=Settings(anonymized_telemetry=False)
        if marker.exists():
            try:
                descriptor=json.loads(marker.read_text(encoding="utf-8"))
                if Path(descriptor["path"]).resolve()!=path:
                    raise ValueError("Shared store path does not match")
                port=int(descriptor["port"])
                if not 0<port<65536:
                    raise ValueError("Invalid shared store port")
                self.client=chromadb.HttpClient(host="127.0.0.1",port=port,settings=settings)
                try:
                    identity=self.client.get_collection("gaptrace-service-identity",embedding_function=None)
                    token=descriptor.get("instance_token")
                    if not token or (identity.metadata or {}).get("instance_token")!=token:
                        raise ValueError("Shared service identity does not match this data directory")
                except Exception:
                    self.client.close()
                    raise
            except Exception as exc:
                raise RuntimeError("The shared Chroma service is unavailable. Restart scripts/run_apps.py; do not open another embedded writer.") from exc
        else:
            self.client=chromadb.PersistentClient(path=str(path),settings=settings)
        ef=embedding_function()
        self.attempts=self.client.get_or_create_collection("skill-erosion-attempts",embedding_function=ef,metadata={"hnsw:space":"cosine"})
        self.resources=self.client.get_or_create_collection("skill-erosion-resources",embedding_function=ef,metadata={"hnsw:space":"cosine"})
    def _upsert(self,collection,ids,documents,metadatas):
        log.info("chroma operation=upsert collection=%s items=%d",collection.name,len(ids))
        if not ids: return
        try:
            # Skip byte-identical rows, preserving actual embeddings and version IDs.
            existing=collection.get(ids=ids,include=["documents","metadatas"])
            known={i:(d,m) for i,d,m in zip(existing["ids"],existing["documents"],existing["metadatas"])}
            changed=[j for j,i in enumerate(ids) if known.get(i)!=(documents[j],metadatas[j])]
            for start in range(0,len(changed),128):
                batch=changed[start:start+128]
                collection.upsert(ids=[ids[i] for i in batch],documents=[documents[i] for i in batch],metadatas=[metadatas[i] for i in batch])
        except Exception as exc:
            log.error("chroma operation=upsert collection=%s error_type=%s; local ONNX model may need a first-use download",collection.name,type(exc).__name__)
            raise
    def upsert_attempts(self,attempts):
        unique={a.evidence_id:a for a in attempts}
        rows=list(unique.values())
        self._upsert(self.attempts,[a.evidence_id for a in rows],[a.response_text or "Empty submitted response" for a in rows],
          [dict(student_id=a.student_id,skill_id=a.skill_id,assistance=a.assistance,correctness=a.correctness,version=a.version) for a in rows])
    def ensure_resources(self):
        catalog=json.loads((ROOT/"resources/remediation/catalog.json").read_text(encoding="utf-8"))
        rows=[Resource.model_validate(r) for r in catalog]
        self._upsert(self.resources,[r.resource_id for r in rows],[r.title+". "+r.description for r in rows],[{"payload":r.model_dump_json()} for r in rows])
        return rows
    def _query(self,collection,text,where=None):
        count=collection.count()
        log.info("chroma operation=query collection=%s items=1 stored_items=%d",collection.name,count)
        if count==0: return []
        try:
            result=collection.query(query_texts=[text],n_results=min(count,1000),where=where,include=["distances","metadatas"])
            return [(i,1-float(d),m) for i,d,m in zip(result["ids"][0],result["distances"][0],result["metadatas"][0])]
        except Exception as exc:
            log.error("chroma operation=query collection=%s error_type=%s",collection.name,type(exc).__name__)
            raise
    def similar_attempts(self,text,student_id,skill_id):
        return self._query(self.attempts,text,{"$and":[{"student_id":student_id},{"skill_id":skill_id},{"assistance":"unassisted"}]})
    def find_resources(self,text,excluded_resource_ids=()):
        return [(Resource.model_validate_json(m["payload"]),score) for i,score,m in self._query(self.resources,text) if i not in excluded_resource_ids]
    def counts(self): return {c.name:c.count() for c in (self.attempts,self.resources)}
