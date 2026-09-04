#!/usr/bin/env python3
"""Deterministic, descriptive health statistics for stored commentary."""
from __future__ import annotations
import argparse, json, re, statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bhf_agent import bible
from bhf_agent.chapter_commentary.builder import CommentaryBuilder
from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
from bhf_agent.chapter_commentary.models import COMMENTARY_PROMPT_VERSION, COMMENTARY_SCHEMA_VERSION, CommentaryStatus
from bhf_agent.chapter_commentary.storage import list_commentaries, load_commentary
from bhf_agent.runtime_paths import RUNTIME_DATA_PATHS

VERSION = '1.0'
REF = re.compile(r'^(.+?)\s+(\d+):(\d+)(?:-(\d+))?$')

def _values(xs):
    return {'average': round(statistics.mean(xs), 2) if xs else 0, 'median': statistics.median(xs) if xs else 0, 'minimum': min(xs) if xs else 0, 'maximum': max(xs) if xs else 0}

def report(storage: str | Path, *, check_evidence: bool = False) -> dict:
    storage = Path(storage)
    builder = CommentaryBuilder(storage)
    canonical = builder.discover_canonical_chapters()
    files = {x: load_commentary(storage, *x) for x in list_commentaries(storage)}
    files = {x:c for x,c in files.items() if c is not None}
    counts = Counter()
    sections = Counter(); categories = Counter(); evidence_ids = Counter(); phrases = Counter()
    section_n=[]; block_n=[]; sizes=[]; evidence_n=[]; section_evidence=[]; block_evidence=[]
    total_refs=valid_refs=invalid_refs=out_scope=malformed=0; unknown=[]
    prompts=Counter(); chapter_rows=[]
    for (book,ch), c in files.items():
        current = bool(c.generated_metadata and c.generated_metadata.commentary_prompt_version == COMMENTARY_PROMPT_VERSION and c.generated_metadata.commentary_schema_version == COMMENTARY_SCHEMA_VERSION)
        status=c.status if current else 'stale'; counts[status]+=1
        if not current:
            continue
        if c.generated_metadata: prompts[c.generated_metadata.commentary_prompt_version]+=1
        sn=len(c.sections); bn=sum(len(s.blocks) for s in c.sections); section_n.append(sn); block_n.append(bn)
        text=' '.join(b.text for s in c.sections for b in s.blocks); sizes.append(len(text))
        cited=set(); s_e=0; b_e=0
        for s in c.sections:
            sections[s.kind]+=1
            for b in s.blocks:
                ids=list(b.evidence_ids); cited.update(ids); b_e += len(ids)
                for eid in ids: evidence_ids[eid]+=1
                for ref in b.verse_refs:
                    total_refs += 1; m=REF.match(ref.strip())
                    if not m: malformed+=1; invalid_refs+=1; continue
                    rb, rc, vs, ve=m.group(1),int(m.group(2)),int(m.group(3)),int(m.group(4) or m.group(3))
                    if rb.lower()!=book.lower() or rc!=ch: out_scope+=1; invalid_refs+=1
                    elif vs<1 or ve<vs: invalid_refs+=1
                    else: valid_refs+=1
                b_e += 0
            s_e += sum(len(b.evidence_ids) for b in s.blocks)
        evidence_n.append(len(cited)); section_evidence.append(s_e); block_evidence.append(b_e)
        categories.update([])
        for word in re.findall(r"\b[\w’'-]{4,}\b", text.lower()): phrases[word]+=1
        chapter_rows.append({'chapter':f'{book} {ch}','status':status,'sections':sn,'blocks':bn,'length':len(text),'evidence_count':len(cited)})
        # Bundle comparison is intentionally limited to cited IDs and is read-only.
        if check_evidence:
            try:
                bundle=get_chapter_evidence_bundle(book,ch)
                unknown.extend(f'{book} {ch}: {eid}' for eid in cited if eid not in bundle.evidence_by_id)
                for eid in cited:
                    item=bundle.evidence_by_id.get(eid)
                    if item: categories[item.category]+=1
            except Exception:
                unknown.extend(f'{book} {ch}: bundle-unavailable' for _ in [0])
    for word,n in phrases.items():
        if n>1: pass
    status_counts={s.value:counts[s.value] for s in CommentaryStatus}
    stale=counts['stale']; generated=len(files); total=len(canonical); pending=max(0,total-generated)
    outliers={
      'lowest_evidence': sorted(chapter_rows,key=lambda x:(x['evidence_count'],x['chapter']))[:5],
      'highest_evidence': sorted(chapter_rows,key=lambda x:(-x['evidence_count'],x['chapter']))[:5],
      'shortest': sorted(chapter_rows,key=lambda x:x['length'])[:5],
      'longest': sorted(chapter_rows,key=lambda x:-x['length'])[:5],
    }
    return {'timestamp':datetime.now(timezone.utc).isoformat(),'schema_version':VERSION,'prompt_version_distribution':dict(prompts),'corpus_counts':{'total_chapters':total,'generated':generated,'coverage_percentage':round(generated*100/total,2) if total else 0,**status_counts,'stale':stale,'pending':pending},'structure':{'sections':_values(section_n),'blocks':_values(block_n),'section_kind_distribution':dict(sections)},'evidence_statistics':{'items_per_chapter':_values(evidence_n),'items_per_section':_values(section_evidence),'items_per_block':_values(block_evidence),'category_distribution':dict(categories),'top_20':evidence_ids.most_common(20),'least_used':sorted(evidence_ids.items(),key=lambda x:(x[1],x[0]))[:20]},'citation_statistics':{'total':total_refs,'valid':valid_refs,'invalid':invalid_refs,'unknown_evidence_ids':unknown,'valid_percentage':round(valid_refs*100/total_refs,2) if total_refs else 100},'verse_statistics':{'total':total_refs,'valid':valid_refs,'invalid':invalid_refs,'out_of_chapter':out_scope,'malformed':malformed,'valid_percentage':round(valid_refs*100/total_refs,2) if total_refs else 100},'content_size':_values(sizes),'repetition':{'repeated_word_fingerprints':sorted(((w,n) for w,n in phrases.items() if n>1),key=lambda x:-x[1])[:20]},'outliers':outliers}

def main():
    p=argparse.ArgumentParser(); p.add_argument('--storage-dir',default=str(RUNTIME_DATA_PATHS.bhf_commentary_storage_path)); p.add_argument('--json',dest='json_path'); p.add_argument('--check-evidence',action='store_true'); a=p.parse_args(); data=report(a.storage_dir, check_evidence=a.check_evidence)
    if a.json_path: Path(a.json_path).write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(data,indent=2))
if __name__=='__main__': main()
