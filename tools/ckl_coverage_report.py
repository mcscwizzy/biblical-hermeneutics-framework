#!/usr/bin/env python3
"""Report strict, scripture-anchored CKL coverage by canonical chapter."""
from __future__ import annotations
import argparse, json, statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bhf_agent.ckl import load_canonical_library
from bhf_agent.presentation import build_evidence_bundle
from framework.canonical_library import CKLRepositoryConfig
from framework.canonical_library.scripture import parse_scripture_query
from bhf_agent import bible

REPORT_VERSION = '1.0'

def chapters_for(scope: str | None) -> list[tuple[str,int]]:
    all_chapters=[]
    for b in bible.list_books():
        all_chapters.extend((b['name'], n) for n in range(1, b['chapters']+1))
    if not scope: return all_chapters
    parts=scope.strip().rsplit(' ',1)
    book=scope.strip(); first=last=None
    if len(parts)==2 and parts[1].replace('-','').isdigit():
        book=parts[0]; n=parts[1]
        if '-' in n: first,last=map(int,n.split('-',1))
        else: first=last=int(n)
    resolved=next((b for b,n in all_chapters if b.lower()==book.lower()),None)
    if not resolved: raise ValueError(f'Unknown book scope: {book}')
    return [(resolved,n) for b,n in all_chapters if b==resolved and (first is None or first<=n<=last)]

def scan(scope: str|None=None) -> dict:
    lib=load_canonical_library(config=CKLRepositoryConfig())
    results=[]
    for book,ch in chapters_for(scope):
        ref=bible.verse_range_reference(book,ch)
        query=parse_scripture_query(ref,book_alias_lookup=lib._book_alias_lookup)
        candidates=sorted(lib._scripture_book_index.get(query.book,set())) if query else []
        raw=lib.retrieve_by_scripture_reference(ref,limit=100)
        bundle=build_evidence_bundle(ref,canonical_results=raw)
        counts=Counter(i.category for i in bundle.evidence_items)
        anchored=len(raw)
        status='DATA_GAP' if anchored==0 else 'THIN' if anchored<3 else 'AVAILABLE'
        results.append({'book':book,'chapter':ch,'reference':ref,'status':status,'raw_ckl_candidates':len(candidates),'valid_anchored_evidence':anchored,'bundle_items':len(bundle.evidence_items),'categories':dict(sorted(counts.items())),'evidence_ids':[i.id for i in bundle.evidence_items],'rejected_candidates':len(candidates)-anchored})
    bybook=defaultdict(list)
    for r in results: bybook[r['book']].append(r)
    summaries={}
    for book, rows in bybook.items():
        summaries[book]={'chapters':len(rows),'available':sum(r['status']=='AVAILABLE' for r in rows),'thin':sum(r['status']=='THIN' for r in rows),'data_gaps':sum(r['status']=='DATA_GAP' for r in rows),'coverage_percentage':round(sum(r['status']!='DATA_GAP' for r in rows)*100/len(rows),2) if rows else 0}
    density=Counter()
    for r in results:
        n=r['valid_anchored_evidence']; density['0 items' if n==0 else '1 item' if n==1 else '2-5 items' if n<=5 else '6+ items']+=1
    categories=Counter()
    for r in results:
        for c in r['categories']: categories[c]+=1
    expansion=sorted((r for r in results if r['status']!='AVAILABLE'),key=lambda r:(r['status']!='DATA_GAP',r['valid_anchored_evidence'],r['book'],r['chapter']))
    vals=[r['valid_anchored_evidence'] for r in results]
    return {'timestamp':datetime.now(timezone.utc).isoformat(),'report_version':REPORT_VERSION,'scope':scope or 'entire Bible','coverage_totals':{'chapters_analyzed':len(results),'evidence_available':sum(r['status']=='AVAILABLE' for r in results),'thin':sum(r['status']=='THIN' for r in results),'data_gaps':sum(r['status']=='DATA_GAP' for r in results),'coverage_percentage':round(sum(v>0 for v in vals)*100/len(vals),2) if vals else 0},'book_summaries':summaries,'chapter_results':results,'evidence_density':{'average':round(statistics.mean(vals),2) if vals else 0,'median':statistics.median(vals) if vals else 0,'minimum':min(vals) if vals else 0,'maximum':max(vals) if vals else 0,'distribution':dict(density)},'category_distribution':dict(sorted(categories.items())),'expansion_candidates':expansion[:50]}

def main():
    p=argparse.ArgumentParser(); p.add_argument('scope',nargs='?'); p.add_argument('--json',dest='json_path'); a=p.parse_args(); data=scan(a.scope)
    if a.json_path: Path(a.json_path).write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(data,indent=2))
if __name__=='__main__': main()
