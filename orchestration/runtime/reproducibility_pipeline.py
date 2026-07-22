"""Immutable candidate reproducibility artifacts with sealed evaluator boundary."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any,Mapping
def digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,default=str).encode()).hexdigest()
def persist(root:Path,name:str,record:Mapping[str,Any])->dict[str,Any]:
 root.mkdir(parents=True,exist_ok=True); p=root/name; value={**record,'digest':digest(record)}
 if p.exists() and json.loads(p.read_text())!=value: raise ValueError('immutable_artifact_drift')
 p.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n'); return value
def initialize(root:Path,manifest:Mapping[str,Any],construction:Mapping[str,Any],unseen:Mapping[str,Any],transfer:Mapping[str,Any])->dict[str,Any]:
 """Seal evaluator contracts before any teaching/evidence artifact exists."""
 return {'manifest':persist(root,'manifest.json',manifest),'construction':persist(root,'construction.json',construction),'sealed_unseen':persist(root,'sealed_unseen.json',unseen),'sealed_transfer':persist(root,'sealed_transfer.json',transfer)}
def package(root:Path,artifacts:Mapping[str,Any])->dict[str,Any]:
 required=('manifest','construction','sealed_unseen','sealed_transfer','sources','derivation','unseen_result','transfer_result')
 missing=[x for x in required if x not in artifacts]
 return persist(root,'candidate_package.json',{'artifacts':artifacts,'complete':not missing,'missing':missing,'trusted_admission':False,'capability_promotion':False})
def review(root:Path,candidate:Mapping[str,Any],pkg:Mapping[str,Any])->dict[str,Any]:
 outcome='admission_ready_with_scope_limit' if pkg['complete'] else 'defer_incomplete_provenance'
 return persist(root,'review.json',{'candidate_id':candidate['candidate_id'],'package_digest':pkg['digest'],'outcome':outcome,'scope_limit':candidate['scope'],'capability_promotion':False})
def authority(root:Path,candidate:Mapping[str,Any],pkg:Mapping[str,Any],review_record:Mapping[str,Any])->dict[str,Any]:
 if review_record['outcome'] not in ('admission_ready','admission_ready_with_scope_limit'): raise ValueError('review_not_admission_ready')
 return persist(root,'pending_authority.json',{'authority_id':digest((candidate['candidate_id'],pkg['digest'],review_record['digest']))[:24],'status':'pending','candidate_id':candidate['candidate_id'],'candidate_digest':candidate['digest'],'package_digest':pkg['digest'],'review_digest':review_record['digest'],'permitted_response':'approve_necessary_condition_repro_v2_admission','exact_once':True,'capability_promotion':False})
