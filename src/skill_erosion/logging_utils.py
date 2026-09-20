"""Structured summaries only: never log attempts, answers or free-text questions."""
import inspect
import logging
import os
import sys
from functools import wraps
from pathlib import Path
from time import perf_counter
from skill_erosion.config import data_dir

def configure_logging(app_name="skill_erosion",root=None):
    root=Path(root or data_dir()); folder=root/"logs";folder.mkdir(parents=True,exist_ok=True)
    shared=Path(os.environ.get("SKILL_EROSION_LOG",folder/"skill_erosion.log"))
    shared.parent.mkdir(parents=True,exist_ok=True)
    paths={shared.resolve(),(folder/f"{app_name}.log").resolve()}
    logger=logging.getLogger("skill_erosion")
    identity=(tuple(sorted(map(str,paths))),id(sys.stdout),os.environ.get("SKILL_EROSION_LOG_LEVEL","INFO"))
    if getattr(logger,"_gaptrace_identity",None)==identity and logger.handlers: return logger
    for handler in logger.handlers[:]: logger.removeHandler(handler);handler.close()
    logger.setLevel(getattr(logging,os.environ.get("SKILL_EROSION_LOG_LEVEL","INFO").upper(),logging.INFO))
    logger.propagate=False
    formatter=logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handlers=[logging.StreamHandler(sys.stdout)]+[logging.FileHandler(p,encoding="utf-8") for p in sorted(paths)]
    for handler in handlers: handler.setFormatter(formatter);logger.addHandler(handler)
    logger._gaptrace_identity=identity
    return logger

def _scope(bound):
    student=bound.get("student_id");skill=bound.get("skill_id")
    for name in ("trend","cluster","journey"):
        value=bound.get(name)
        if value is not None:
            if name=="journey": value=value.trend
            student=student or getattr(value,"student_id",None);skill=skill or getattr(value,"skill_id",None)
    records=bound.get("records",[])
    if records:
        def unique(field):
            values={getattr(a,field,None) if not isinstance(a,dict) else a.get(field) for a in records}
            return next(iter(values)) if len(values)==1 else f"multiple({len(values)})"
        student=student or unique("student_id");skill=skill or unique("skill_id")
    clean=lambda x:str(x or "none").replace("\n","\\n").replace("\r","\\r")
    return clean(student),clean(skill)

def logged_agent(function):
    signature=inspect.signature(function)
    @wraps(function)
    def wrapped(*args,**kwargs):
        student,skill=_scope(signature.bind(*args,**kwargs).arguments)
        logger=logging.getLogger("skill_erosion");start=perf_counter()
        logger.info("agent=%s event=start student_id=%s skill_id=%s",function.__name__,student,skill)
        try:
            result=function(*args,**kwargs)
            summary=[]
            for name in ("status","verdict","confidence","stored_versions"):
                if hasattr(result,name): summary.append(f"{name}={getattr(result,name)}")
            if isinstance(result,list): summary.append(f"count={len(result)}")
            if isinstance(result,str): summary.append("answer=filtered_template")
            logger.info("agent=%s event=complete student_id=%s skill_id=%s %s elapsed_ms=%.2f",function.__name__,student,skill," ".join(summary) or "result=ready",(perf_counter()-start)*1000)
            return result
        except Exception as exc:
            logger.error("agent=%s event=failed student_id=%s skill_id=%s error_type=%s elapsed_ms=%.2f",function.__name__,student,skill,type(exc).__name__,(perf_counter()-start)*1000)
            raise
    return wrapped
